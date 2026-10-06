import { useState } from 'react';
import { useSelector } from 'react-redux';
import { Send, Paperclip, Loader2, Zap } from 'lucide-react';
import { useChat } from '../../hooks/useChat';
import PdfUploader from './PdfUploader';
import { PdfStatusBanner } from './PdfProcessingStatus';
import { isPdfIndexing } from '../../hooks/usePdfStatus';

export default function ChatInput() {
  const [message, setMessage] = useState('');
  const [showUploader, setShowUploader] = useState(false);
  const { activeChatId, isStreaming, sendMessage, messages } = useChat();
  const { selectedModel, smartSwitchEnabled } = useSelector((state) => state.model);
  // Typing is allowed while a PDF is indexed; sending waits until it's searchable
  const preparing = useSelector((state) => state.pdf.pdfs.some(isPdfIndexing));
  const canSend = message.trim() && !isStreaming && !preparing;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!canSend) return;
    sendMessage(activeChatId, message.trim(), selectedModel?.id, smartSwitchEnabled);
    setMessage('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="px-3 pb-3 flex-shrink-0">
      {/* PDF Uploader (toggle) */}
      {showUploader && (
        <div className="mb-3 animate-slide-up">
          <PdfUploader onClose={() => setShowUploader(false)} />
        </div>
      )}

      {/* PDF indexing / summary progress (the empty-chat card covers indexing itself) */}
      <PdfStatusBanner hideIndexing={messages.length === 0} />

      {/* Input bar */}
      <form
        onSubmit={handleSubmit}
        className="flex items-end gap-2 glass rounded-2xl p-2 border border-glass-border focus-within:border-primary-500/30 transition-colors"
      >
        {/* Attach PDF button */}
        <button
          type="button"
          id="attach-pdf-btn"
          onClick={() => setShowUploader(!showUploader)}
          disabled={isStreaming}
          className="p-2 rounded-xl hover:bg-primary-500/10 text-text-muted hover:text-primary-400 transition-colors flex-shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Attach PDF"
        >
          <Paperclip size={18} />
        </button>

        {/* Text input */}
        <textarea
          id="chat-input"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            preparing
              ? "Preparing your PDF — type your question, you can send it once it's ready…"
              : 'Ask anything about your PDF...'
          }
          disabled={isStreaming}
          rows={1}
          className="flex-1 bg-transparent text-sm text-text-primary placeholder:text-text-muted resize-none focus:outline-none py-2 max-h-28 disabled:opacity-50"
          style={{ minHeight: '36px' }}
        />

        {/* Send button */}
        <button
          type="submit"
          id="send-message-btn"
          disabled={!canSend}
          title={preparing ? 'Your PDF is still being prepared' : undefined}
          className={`p-2 rounded-xl transition-all duration-200 flex-shrink-0 ${
            canSend
              ? 'bg-primary-600 hover:bg-primary-500 text-white shadow-md shadow-primary-500/20 active:scale-95'
              : 'bg-glass-border/50 text-text-muted/50 cursor-not-allowed'
          }`}
          aria-label="Send message"
        >
          {isStreaming ? (
            <Loader2 size={18} className="animate-spin" />
          ) : (
            <Send size={18} />
          )}
        </button>
      </form>

      {/* Model indicator */}
      <div className="flex items-center justify-center gap-1.5 mt-1.5">
        {smartSwitchEnabled ? (
          <>
            <Zap size={11} className="text-warning" />
            <span className="text-[10px] text-text-muted">Smart Switch — best model picked per question</span>
          </>
        ) : (
          <>
            <span className="text-sm">{selectedModel?.icon}</span>
            <span className="text-[10px] text-text-muted">{selectedModel?.name}</span>
          </>
        )}
      </div>
    </div>
  );
}
