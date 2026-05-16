import { useState } from 'react';
import { useSelector } from 'react-redux';
import { Send, Paperclip, Loader2 } from 'lucide-react';
import { useChat } from '../../hooks/useChat';
import PdfUploader from './PdfUploader';

export default function ChatInput() {
  const [message, setMessage] = useState('');
  const [showUploader, setShowUploader] = useState(false);
  const { activeChatId, isStreaming, sendMessage } = useChat();
  const { selectedModel } = useSelector((state) => state.model);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!message.trim() || !activeChatId || isStreaming) return;
    sendMessage(activeChatId, message.trim(), selectedModel?.id);
    setMessage('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="px-4 pb-4">
      {/* PDF Uploader (toggle) */}
      {showUploader && (
        <div className="mb-3 animate-slide-up">
          <PdfUploader onClose={() => setShowUploader(false)} />
        </div>
      )}

      {/* Input bar */}
      <form
        onSubmit={handleSubmit}
        className="max-w-3xl mx-auto flex items-end gap-2 glass rounded-2xl p-2 border border-glass-border focus-within:border-primary-500/30 transition-colors"
      >
        {/* Attach PDF button */}
        <button
          type="button"
          id="attach-pdf-btn"
          onClick={() => setShowUploader(!showUploader)}
          className="p-2.5 rounded-xl hover:bg-primary-500/10 text-text-muted hover:text-primary-400 transition-colors flex-shrink-0"
          aria-label="Attach PDF"
        >
          <Paperclip size={20} />
        </button>

        {/* Text input */}
        <textarea
          id="chat-input"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={activeChatId ? 'Ask about your PDF...' : 'Select or create a chat first'}
          disabled={!activeChatId || isStreaming}
          rows={1}
          className="flex-1 bg-transparent text-sm text-text-primary placeholder:text-text-muted resize-none focus:outline-none py-2.5 max-h-32 disabled:opacity-50"
          style={{ minHeight: '40px' }}
        />

        {/* Send button */}
        <button
          type="submit"
          id="send-message-btn"
          disabled={!message.trim() || !activeChatId || isStreaming}
          className="p-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-200 active:scale-95 flex-shrink-0"
          aria-label="Send message"
        >
          {isStreaming ? (
            <Loader2 size={20} className="animate-spin" />
          ) : (
            <Send size={20} />
          )}
        </button>
      </form>

      {/* Model indicator */}
      <div className="max-w-3xl mx-auto flex items-center justify-center gap-1.5 mt-2">
        <span className="text-lg">{selectedModel?.icon}</span>
        <span className="text-xs text-text-muted">{selectedModel?.name}</span>
      </div>
    </div>
  );
}
