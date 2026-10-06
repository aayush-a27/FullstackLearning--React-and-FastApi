import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Trash2, Pencil } from 'lucide-react';
import { timeAgo, truncate } from '../../utils/helpers';
import { chatPath } from '../../utils/constants';

const MAX_TITLE_LENGTH = 255;

// A real link, so the chat's URL can be copied, opened in a new tab, or bookmarked
export default function ChatHistoryItem({ chat, isActive, onRename, onDelete }) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(chat.title);
  const inputRef = useRef(null);

  useEffect(() => {
    if (isEditing) inputRef.current?.select();
  }, [isEditing]);

  const startEditing = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDraft(chat.title);
    setIsEditing(true);
  };

  const commit = async () => {
    setIsEditing(false);
    const title = draft.trim();
    if (!title || title === chat.title) {
      setDraft(chat.title); // nothing to save, or cleared to blank
      return;
    }
    const saved = await onRename(title);
    if (!saved) setDraft(chat.title);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      commit();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      setDraft(chat.title);
      setIsEditing(false);
    }
  };

  if (isEditing) {
    return (
      <div className="px-3 py-2.5 rounded-xl bg-surface-600 border border-primary-500/30">
        <input
          ref={inputRef}
          value={draft}
          maxLength={MAX_TITLE_LENGTH}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={commit}
          aria-label="Chat name"
          className="w-full bg-transparent text-sm text-text-primary focus:outline-none"
        />
        <p className="text-[10px] text-text-muted mt-0.5">Enter to save · Esc to cancel</p>
      </div>
    );
  }

  return (
    <Link
      to={chatPath(chat.id)}
      aria-current={isActive ? 'page' : undefined}
      onDoubleClick={startEditing}
      className={`group flex items-center gap-1 px-3 py-2.5 rounded-xl cursor-pointer transition-all duration-200 ${
        isActive
          ? 'bg-primary-500/15 border border-primary-500/20'
          : 'hover:bg-surface-600 border border-transparent'
      }`}
    >
      <div className="flex-1 min-w-0">
        <p
          className={`text-sm truncate ${
            isActive ? 'text-primary-400 font-medium' : 'text-text-primary'
          }`}
          title={chat.title}
        >
          {truncate(chat.title, 28)}
        </p>
        <p className="text-xs text-text-muted mt-0.5">{timeAgo(chat.created_at)}</p>
      </div>

      {/* Rename / delete — visible on hover */}
      <button
        onClick={startEditing}
        className="opacity-0 group-hover:opacity-100 p-1 rounded-lg hover:bg-primary-500/15 text-text-muted hover:text-primary-400 transition-all duration-150"
        aria-label={`Rename ${chat.title}`}
      >
        <Pencil size={13} />
      </button>
      <button
        onClick={(e) => {
          // Don't let the click also follow the link
          e.preventDefault();
          e.stopPropagation();
          onDelete();
        }}
        className="opacity-0 group-hover:opacity-100 p-1 rounded-lg hover:bg-danger/15 text-text-muted hover:text-danger transition-all duration-150"
        aria-label={`Delete ${chat.title}`}
      >
        <Trash2 size={14} />
      </button>
    </Link>
  );
}
