import { useEffect, useRef } from 'react';
import { useSelector } from 'react-redux';
import { FileText, Sparkles } from 'lucide-react';
import ChatBubble from './ChatBubble';
import { useChat } from '../../hooks/useChat';
import Loader from '../common/Loader';
import { PdfPreparingCard } from './PdfProcessingStatus';
import { isPdfIndexing } from '../../hooks/usePdfStatus';
import { PDF_LIMITS } from '../../utils/constants';

export default function ChatArea() {
  const { messages, isStreaming, isLoadingMessages, activeChatId } = useSelector(
    (state) => state.chat
  );
  const preparing = useSelector((state) => state.pdf.pdfs.some(isPdfIndexing));
  const { resendFrom, retryAnswer } = useChat();
  const bottomRef = useRef(null);
  // Same rule as the input box: no new answers while one streams or a PDF is indexing
  const actionsDisabled = isStreaming || preparing;
  const lastIndex = messages.length - 1;

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6">
      {preparing && messages.length === 0 && !isLoadingMessages ? (
        /* PDF still being indexed — explain the wait instead of a blank chat */
        <PdfPreparingCard />
      ) : !activeChatId ? (
        /* Empty state — no chat selected */
        <div className="h-full flex flex-col items-center justify-center animate-fade-in">
          <div className="w-16 h-16 rounded-2xl bg-primary-500/10 border border-primary-500/20 flex items-center justify-center mb-4 animate-pulse-glow">
            <Sparkles size={28} className="text-primary-400" />
          </div>
          <h2 className="text-lg font-bold text-text-primary mb-2">Green Book AI</h2>
          <p className="text-text-muted text-center max-w-xs text-sm">
            Upload a PDF and start chatting. Ask questions, get insights, and receive
            suggestions to improve your documents.
          </p>
          <div className="flex items-center gap-2 mt-4 text-xs text-text-muted">
            <FileText size={14} />
            <span>Supports PDF files up to {PDF_LIMITS.MAX_FILE_SIZE_MB}MB</span>
          </div>
        </div>
      ) : isLoadingMessages ? (
        <div className="h-full flex items-center justify-center">
          <Loader size="md" text="Loading messages..." />
        </div>
      ) : messages.length === 0 ? (
        /* Empty chat — no messages yet */
        <div className="h-full flex flex-col items-center justify-center animate-fade-in">
          <div className="w-14 h-14 rounded-2xl bg-primary-500/10 border border-primary-500/20 flex items-center justify-center mb-3">
            <FileText size={24} className="text-primary-400" />
          </div>
          <h3 className="text-base font-semibold text-text-primary mb-1">Start a conversation</h3>
          <p className="text-xs text-text-muted text-center max-w-xs">
            Upload a PDF or type a question to get started.
          </p>
        </div>
      ) : (
        /* Messages list */
        <div className="space-y-4">
          {messages.map((msg, index) => (
            <ChatBubble
              key={msg.id}
              message={msg}
              isStreaming={isStreaming && index === lastIndex && msg.role === 'assistant'}
              actionsDisabled={actionsDisabled}
              // Try again only on the latest answer, so it never wipes later turns
              onRetry={
                msg.role === 'assistant' && index === lastIndex ? () => retryAnswer(index) : undefined
              }
              onEdit={msg.role === 'user' ? (text) => resendFrom(index, text) : undefined}
              // More than this message's own answer would be replaced
              replacesLater={index < lastIndex - 1}
            />
          ))}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}
