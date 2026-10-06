import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, MessageSquare } from 'lucide-react';
import { ROUTES } from '../../utils/constants';
import { useChat } from '../../hooks/useChat';
import ChatHistoryItem from './ChatHistoryItem';
import Button from '../common/Button';
import Loader from '../common/Loader';

export default function ChatHistoryPanel() {
  const {
    chats,
    activeChatId,
    isLoadingChats,
    fetchChats,
    renameChat,
    deleteChat,
    selectChat,
  } = useChat();

  const navigate = useNavigate();

  useEffect(() => {
    fetchChats();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleNewChat = () => {
    // /dashboard is "new chat"; clear directly too in case we're already there
    navigate(ROUTES.DASHBOARD);
    selectChat(null);
  };

  return (
    <div className="h-full flex flex-col">
      {/* New Chat button */}
      <div className="p-3 border-b border-glass-border">
        <Button
          id="new-chat-btn"
          onClick={handleNewChat}
          variant="secondary"
          size="sm"
          fullWidth
        >
          <Plus size={16} />
          New Chat
        </Button>
      </div>

      {/* Chat List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
        {isLoadingChats ? (
          <div className="flex items-center justify-center py-8">
            <Loader size="sm" text="Loading..." />
          </div>
        ) : chats.length === 0 ? (
          <div className="text-center py-8">
            <MessageSquare size={28} className="mx-auto text-text-muted/40 mb-2" />
            <p className="text-xs text-text-muted">No chats yet</p>
            <p className="text-xs text-text-muted">Start a new conversation!</p>
          </div>
        ) : (
          chats.map((chat) => (
            <ChatHistoryItem
              key={chat.id}
              chat={chat}
              isActive={chat.id === activeChatId}
              onRename={(title) => renameChat(chat.id, title)}
              onDelete={() => deleteChat(chat.id)}
            />
          ))
        )}
      </div>
    </div>
  );
}
