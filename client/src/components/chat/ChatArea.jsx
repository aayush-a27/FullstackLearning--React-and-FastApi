import { useEffect, useRef } from 'react';
import { useSelector } from 'react-redux';
import { FileText, Sparkles } from 'lucide-react';
import ChatBubble from './ChatBubble';
import Loader from '../common/Loader';
import Navbar from '../layout/Navbar';

export default function ChatArea() {
  const { messages, isStreaming, isLoadingMessages, activeChatId } = useSelector(
    (state) => state.chat
  );
  const bottomRef = useRef(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Navbar */}
      <Navbar />

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {!activeChatId ? (
          /* Empty state — no chat selected */
          <div className="h-full flex flex-col items-center justify-center animate-fade-in">
            <div className="w-20 h-20 rounded-2xl bg-primary-500/10 border border-primary-500/20 flex items-center justify-center mb-6 animate-pulse-glow">
              <Sparkles size={36} className="text-primary-400" />
            </div>
            <h2 className="text-2xl font-bold text-text-primary mb-2">PDF Chat AI</h2>
            <p className="text-text-muted text-center max-w-sm">
              Upload a PDF and start chatting. Ask questions, get insights, and receive
              suggestions to improve your documents.
            </p>
            <div className="flex items-center gap-2 mt-6 text-xs text-text-muted">
              <FileText size={14} />
              <span>Supports PDF files up to 50MB</span>
            </div>
          </div>
        ) : isLoadingMessages ? (
          <div className="h-full flex items-center justify-center">
            <Loader size="md" text="Loading messages..." />
          </div>
        ) : messages.length === 0 ? (
          /* Empty chat — no messages yet */
          <div className="h-full flex flex-col items-center justify-center animate-fade-in">
            <div className="w-16 h-16 rounded-2xl bg-primary-500/10 border border-primary-500/20 flex items-center justify-center mb-4">
              <FileText size={28} className="text-primary-400" />
            </div>
            <h3 className="text-lg font-semibold text-text-primary mb-1">Start a conversation</h3>
            <p className="text-sm text-text-muted text-center max-w-xs">
              Upload a PDF or type a question to get started.
            </p>
          </div>
        ) : (
          /* Messages list */
          <div className="max-w-3xl mx-auto space-y-4">
            {messages.map((msg) => (
              <ChatBubble key={msg.id} message={msg} isStreaming={isStreaming && msg === messages[messages.length - 1] && msg.role === 'assistant'} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>
    </div>
  );
}
