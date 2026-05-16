import { Trash2 } from 'lucide-react';
import { timeAgo, truncate } from '../../utils/helpers';

export default function ChatHistoryItem({ chat, isActive, onSelect, onDelete }) {
  return (
    <div
      className={`group flex items-center gap-2 px-3 py-2.5 rounded-xl cursor-pointer transition-all duration-200 ${
        isActive
          ? 'bg-primary-500/15 border border-primary-500/20'
          : 'hover:bg-surface-600 border border-transparent'
      }`}
      onClick={onSelect}
    >
      <div className="flex-1 min-w-0">
        <p
          className={`text-sm truncate ${
            isActive ? 'text-primary-400 font-medium' : 'text-text-primary'
          }`}
        >
          {truncate(chat.title, 28)}
        </p>
        <p className="text-xs text-text-muted mt-0.5">{timeAgo(chat.created_at)}</p>
      </div>

      {/* Delete button — visible on hover */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        className="opacity-0 group-hover:opacity-100 p-1 rounded-lg hover:bg-danger/15 text-text-muted hover:text-danger transition-all duration-150"
        aria-label="Delete chat"
      >
        <Trash2 size={14} />
      </button>
    </div>
  );
}
