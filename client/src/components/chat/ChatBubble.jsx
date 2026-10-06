import { Bot, User, AlertCircle, FileText } from 'lucide-react';
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

export default function ChatBubble({ message, isStreaming }) {
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
        <div className="max-w-[75%] rounded-2xl rounded-bl-sm px-4 py-2.5 text-sm bg-danger/5 border border-danger/20 text-text-secondary">
          {text}
        </div>
      </div>
    );
  }

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

      {/* Bubble */}
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
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

      {/* User avatar */}
      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-surface-600 border border-glass-border flex items-center justify-center">
          <User size={16} className="text-text-secondary" />
        </div>
      )}
    </div>
  );
}
