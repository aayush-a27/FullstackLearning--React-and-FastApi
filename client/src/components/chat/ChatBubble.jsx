import { useEffect, useRef, useState } from 'react';
import { Bot, User, AlertCircle, FileText, Copy, Check, Pencil, RotateCcw } from 'lucide-react';
import toast from 'react-hot-toast';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize from 'rehype-sanitize';
import { AI_MODELS } from '../../utils/constants';

// GFM = tables, strikethrough, task lists. rehype-raw lets inline HTML the
// model emits (e.g. <br> inside table cells) render; rehype-sanitize then
// strips anything unsafe (scripts, event handlers) from that HTML.
const remarkPlugins = [remarkGfm];
const rehypePlugins = [rehypeRaw, rehypeSanitize];
const markdownComponents = {
  table: ({ children }) => (
    <div className="table-wrap">
      <table>{children}</table>
    </div>
  ),
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
};

// Older messages saved raw provider errors ("⚠️ Error generating response with ...")
const LEGACY_ERROR_PREFIX = '⚠️ Error';
const LEGACY_ERROR_TEXT = "This response couldn't be generated. Please ask again.";

function getModelName(modelId) {
  return AI_MODELS.find((m) => m.id === modelId)?.name || modelId;
}

function pageLabel(source) {
  if (!source.page_start) return null;
  return source.page_start === source.page_end
    ? `p.${source.page_start}`
    : `p.${source.page_start}-${source.page_end}`;
}

/** Which PDF pages the answer was grounded in. */
function Sources({ sources, mode }) {
  if (!sources?.length) return null;

  const byFile = new Map();
  for (const source of sources) {
    const pages = byFile.get(source.filename) || [];
    const label = pageLabel(source);
    if (label) pages.push(label);
    byFile.set(source.filename, pages);
  }

  return (
    <div className="mt-2 pt-2 border-t border-glass-border flex flex-wrap items-center gap-x-2 gap-y-1">
      <FileText size={11} className="text-text-muted flex-shrink-0" />
      <span className="text-[10px] text-text-muted">
        {mode === 'summary' ? 'From the document summary:' : 'Sources:'}
      </span>
      {[...byFile.entries()].map(([filename, pages]) => (
        <span key={filename} className="text-[10px] text-primary-400/80">
          {filename}
          {pages.length > 0 && ` · ${pages.join(', ')}`}
        </span>
      ))}
    </div>
  );
}

function ActionButton({ icon: Icon, label, onClick, disabled }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={label}
      aria-label={label}
      className="p-1.5 rounded-lg text-text-muted hover:text-primary-400 hover:bg-primary-500/10 transition-colors disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:text-text-muted"
    >
      <Icon size={14} />
    </button>
  );
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return undefined;
    const timer = setTimeout(() => setCopied(false), 2000);
    return () => clearTimeout(timer);
  }, [copied]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
    } catch {
      // Clipboard needs HTTPS (or localhost) and the user's permission
      toast.error("Couldn't copy — your browser blocked clipboard access.");
    }
  };

  return <ActionButton icon={copied ? Check : Copy} label={copied ? 'Copied' : 'Copy'} onClick={copy} />;
}

/** Inline editor that replaces a user bubble while it's being edited. */
function EditBox({ initial, replacesLater, disabled, onCancel, onSubmit }) {
  const [text, setText] = useState(initial);
  const textareaRef = useRef(null);
  const trimmed = text.trim();
  const canSend = Boolean(trimmed) && !disabled;

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.focus();
    el.setSelectionRange(el.value.length, el.value.length);
  }, []);

  const submit = () => {
    if (canSend) onSubmit(trimmed);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    } else if (e.key === 'Escape') {
      onCancel();
    }
  };

  return (
    <div className="w-full rounded-2xl border border-primary-500/40 bg-surface-700 p-3">
      <textarea
        ref={textareaRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        rows={Math.min(8, Math.max(2, text.split('\n').length))}
        aria-label="Edit your message"
        className="w-full bg-transparent text-sm text-text-primary leading-relaxed resize-none focus:outline-none"
      />
      {replacesLater && (
        <p className="text-[11px] text-text-muted mt-1">
          Sending replaces this message and everything after it.
        </p>
      )}
      <div className="flex justify-end gap-2 mt-2">
        <button
          type="button"
          onClick={onCancel}
          className="px-3 py-1.5 rounded-lg text-xs text-text-secondary hover:bg-glass-border/50 transition-colors"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={submit}
          disabled={!canSend}
          className="px-3 py-1.5 rounded-lg text-xs font-medium bg-primary-600 hover:bg-primary-500 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Send
        </button>
      </div>
    </div>
  );
}

/**
 * One chat message, with its actions underneath:
 * Copy on every message, Edit on the user's (`onEdit`), Try again where `onRetry` is given.
 * `actionsDisabled` blocks Edit / Try again while an answer is streaming.
 */
export default function ChatBubble({
  message,
  isStreaming,
  onRetry,
  onEdit,
  actionsDisabled = false,
  replacesLater = false,
}) {
  const [editing, setEditing] = useState(false);
  const isUser = message.role === 'user';
  const isError =
    !isUser && (message.isError || message.content?.startsWith(LEGACY_ERROR_PREFIX));

  if (isError) {
    const text = message.isError ? message.content : LEGACY_ERROR_TEXT;
    return (
      <div className="flex gap-3 animate-fade-in justify-start">
        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-danger/10 border border-danger/20 flex items-center justify-center">
          <AlertCircle size={16} className="text-danger/80" />
        </div>
        <div className="flex flex-col items-start max-w-[75%]">
          <div className="rounded-2xl rounded-bl-sm px-4 py-2.5 text-sm bg-danger/5 border border-danger/20 text-text-secondary">
            {text}
          </div>
          {onRetry && (
            <div className="flex items-center gap-0.5 mt-1">
              <ActionButton icon={RotateCcw} label="Try again" onClick={onRetry} disabled={actionsDisabled} />
            </div>
          )}
        </div>
      </div>
    );
  }

  const showActions = !editing && !isStreaming && Boolean(message.content);

  return (
    <div
      className={`flex gap-3 animate-fade-in ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      {/* Avatar */}
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-primary-500/20 border border-primary-500/30 flex items-center justify-center">
          <Bot size={16} className="text-primary-400" />
        </div>
      )}

      <div
        className={`flex flex-col min-w-0 max-w-[75%] ${isUser ? 'items-end' : 'items-start'} ${
          editing ? 'w-full' : ''
        }`}
      >
        {editing ? (
          <EditBox
            initial={message.content}
            replacesLater={replacesLater}
            disabled={actionsDisabled}
            onCancel={() => setEditing(false)}
            onSubmit={(text) => {
              setEditing(false);
              onEdit(text);
            }}
          />
        ) : (
          <div
            className={`max-w-full rounded-2xl px-4 py-3 text-sm leading-relaxed ${
              isUser
                ? 'bg-primary-600 text-white rounded-br-sm'
                : 'bg-surface-700 border border-glass-border text-text-primary rounded-bl-sm'
            }`}
          >
            {isUser ? (
              <p className="whitespace-pre-wrap">{message.content}</p>
            ) : (
              <div className="chat-markdown prose prose-invert prose-sm max-w-none">
                {message.content ? (
                  <ReactMarkdown
                    remarkPlugins={remarkPlugins}
                    rehypePlugins={rehypePlugins}
                    components={markdownComponents}
                  >
                    {isStreaming ? `${message.content}█` : message.content}
                  </ReactMarkdown>
                ) : isStreaming ? (
                  <div className="flex items-center gap-1.5">
                    <div className="w-1.5 h-1.5 bg-primary-400 rounded-full animate-bounce" />
                    <div className="w-1.5 h-1.5 bg-primary-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                    <div className="w-1.5 h-1.5 bg-primary-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                  </div>
                ) : null}
              </div>
            )}

            {/* Which pages the answer came from */}
            {!isUser && (
              <Sources sources={message.metadata?.sources} mode={message.metadata?.mode} />
            )}

            {/* Model tag for AI messages */}
            {!isUser && message.model_used && (
              <p className="text-xs text-text-muted mt-2 pt-1 border-t border-glass-border">
                {getModelName(message.model_used)}
              </p>
            )}
          </div>
        )}

        {/* Actions under the bubble */}
        {showActions && (
          <div className="flex items-center gap-0.5 mt-1">
            <CopyButton text={message.content} />
            {isUser && onEdit && (
              <ActionButton
                icon={Pencil}
                label="Edit"
                onClick={() => setEditing(true)}
                disabled={actionsDisabled}
              />
            )}
            {!isUser && onRetry && (
              <ActionButton icon={RotateCcw} label="Try again" onClick={onRetry} disabled={actionsDisabled} />
            )}
          </div>
        )}
      </div>

      {/* User avatar */}
      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-surface-600 border border-glass-border flex items-center justify-center">
          <User size={16} className="text-text-secondary" />
        </div>
      )}
    </div>
  );
}
