import { useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useSelector } from 'react-redux';
import { useChat } from '../hooks/useChat';
import { ROUTES } from '../utils/constants';

/**
 * Route target for /dashboard and /chat/:chatId.
 *
 * The 3-panel layout itself is rendered by AppLayout; this component only keeps
 * the open chat in sync with the URL, so a copied /chat/<id> link opens that
 * chat and the browser's back/forward buttons move between chats.
 */
export default function Dashboard() {
  const { chatId } = useParams();
  const navigate = useNavigate();
  const { selectChat } = useChat();
  const activeChatId = useSelector((state) => state.chat.activeChatId);

  // Read the latest active chat without re-running the URL effect when it changes:
  // a new chat sets activeChatId first and then updates the URL.
  const activeChatRef = useRef(activeChatId);
  useEffect(() => {
    activeChatRef.current = activeChatId;
  }, [activeChatId]);

  useEffect(() => {
    const target = chatId || null;
    if (target === activeChatRef.current) return;

    selectChat(target).then((found) => {
      // Unknown or someone else's chat — fall back to a fresh chat
      if (!found) navigate(ROUTES.DASHBOARD, { replace: true });
    });
  }, [chatId]); // eslint-disable-line react-hooks/exhaustive-deps

  return null;
}
