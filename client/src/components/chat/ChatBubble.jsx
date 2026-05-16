import { Bot, User } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

export default function ChatBubble({ message, isStreaming }) {
  const isUser = message.role === 'user';

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
          <div className="prose prose-invert prose-sm max-w-none prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-li:my-0.5">
            {message.content ? (
              <ReactMarkdown>{message.content}</ReactMarkdown>
            ) : isStreaming ? (
              <div className="flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 bg-primary-400 rounded-full animate-bounce" />
                <div className="w-1.5 h-1.5 bg-primary-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                <div className="w-1.5 h-1.5 bg-primary-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
              </div>
            ) : null}
          </div>
        )}

        {/* Model tag for AI messages */}
        {!isUser && message.model_used && (
          <p className="text-xs text-text-muted mt-2 pt-1 border-t border-glass-border">
            {message.model_used}
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
