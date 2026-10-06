import { useSelector, useDispatch, useStore } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import axiosInstance from '../api/axiosInstance';
import { CHATS, MESSAGES } from '../api/endpoints';
import { streamMessage } from '../api/streamMessage';
import { setPdfs, clearPdfs } from '../features/pdf/pdfSlice';
import { getFriendlyError } from '../utils/helpers';
import { ROUTES, chatPath } from '../utils/constants';
import {
  setChats,
  setLoadingChats,
  addChat,
  updateChat,
  removeChat,
  setActiveChat,
  setMessages,
  setLoadingMessages,
  addMessage,
  replaceLastMessage,
  patchLastMessage,
  updateLastMessage,
  setStreaming,
  setChatError,
} from '../features/chat/chatSlice';

export function useChat() {
  const dispatch = useDispatch();
  const store = useStore();
  const navigate = useNavigate();
  const {
    chats,
    activeChatId,
    messages,
    isStreaming,
    isLoadingChats,
    isLoadingMessages,
    error,
  } = useSelector((state) => state.chat);
  const { pdfs } = useSelector((state) => state.pdf);

  // Show a short, user-friendly toast and keep the message in state
  const reportError = (err, fallback) => {
    const message = getFriendlyError(err, fallback);
    dispatch(setChatError(message));
    toast.error(message);
    return message;
  };

  const fetchChats = async () => {
    try {
      dispatch(setLoadingChats(true));
      const { data } = await axiosInstance.get(CHATS.LIST);
      dispatch(setChats(data));
      return data;
    } catch (err) {
      dispatch(setLoadingChats(false));
      reportError(err, "Couldn't load your chats. Please refresh the page.");
      return null;
    }
  };

  const createChat = async (title, pdfIds = []) => {
    try {
      const { data } = await axiosInstance.post(CHATS.CREATE, {
        title,
        pdf_ids: pdfIds,
      });
      dispatch(addChat(data));
      dispatch(setActiveChat(data.id));
      dispatch(setMessages([]));
      return data;
    } catch (err) {
      reportError(err, "Couldn't start a new chat. Please try again.");
      return null;
    }
  };

  /** Rename a chat. Returns true on success. */
  const renameChat = async (chatId, title) => {
    const trimmed = title.trim();
    if (!trimmed) return false;
    try {
      const { data } = await axiosInstance.patch(CHATS.RENAME(chatId), { title: trimmed });
      dispatch(updateChat(data));
      return true;
    } catch (err) {
      reportError(err, "Couldn't rename that chat. Please try again.");
      return false;
    }
  };

  const deleteChat = async (chatId) => {
    try {
      await axiosInstance.delete(CHATS.DELETE(chatId));
      const wasOpen = chatId === activeChatId;
      dispatch(removeChat(chatId));
      if (wasOpen) {
        // The deleted chat was open — leave its URL and start fresh
        dispatch(clearPdfs());
        navigate(ROUTES.DASHBOARD, { replace: true });
      }
    } catch (err) {
      reportError(err, "Couldn't delete that chat. Please try again.");
    }
  };

  /**
   * Open a chat (or start a fresh one with `null`).
   * Loads the chat from the server rather than the sidebar list, so it also
   * works for a pasted /chat/<id> link before the list has loaded.
   * Resolves to false if the chat doesn't exist or isn't the user's.
   */
  const selectChat = async (chatId) => {
    dispatch(setActiveChat(chatId));

    if (!chatId) {
      dispatch(clearPdfs());
      dispatch(setMessages([]));
      return true;
    }

    // Show the PDFs we already know about straight away
    const listed = chats.find((c) => c.id === chatId);
    dispatch(listed ? setPdfs(listed.pdf_documents || []) : clearPdfs());
    dispatch(setLoadingMessages(true));

    // Ignore late responses if the user has already switched to another chat
    const stillActive = () => store.getState().chat.activeChatId === chatId;

    try {
      const [{ data: chat }, { data: chatMessages }] = await Promise.all([
        axiosInstance.get(CHATS.GET(chatId)),
        axiosInstance.get(MESSAGES.LIST(chatId)),
      ]);
      if (!stillActive()) return true;
      dispatch(setPdfs(chat.pdf_documents || []));
      dispatch(setMessages(chatMessages));
      return true;
    } catch (err) {
      if (!stillActive()) return true;
      dispatch(setLoadingMessages(false));
      const status = err.response?.status;
      if (status === 404 || status === 422) {
        dispatch(setActiveChat(null));
        dispatch(clearPdfs());
        dispatch(setMessages([]));
        toast.error("That chat doesn't exist or you don't have access to it.");
        return false;
      }
      reportError(err, "Couldn't load this conversation. Please try again.");
      return true;
    }
  };

  const sendMessage = async (chatId, content, modelId, smartSwitch) => {
    let targetChatId = chatId;

    // Create chat on the fly if it doesn't exist
    if (!targetChatId) {
      dispatch(setStreaming(true));
      const newChat = await createChat(content.slice(0, 30) + (content.length > 30 ? '...' : ''), pdfs.map(p => p.id));
      if (!newChat) {
        dispatch(setStreaming(false));
        return; // createChat already showed an error toast
      }
      targetChatId = newChat.id;
      // Give the new chat its own shareable URL (activeChatId is already set,
      // so Dashboard's URL sync won't reload it mid-stream)
      navigate(chatPath(targetChatId));
    }

    // Add user message immediately
    const userMsg = {
      id: crypto.randomUUID(),
      chat_id: targetChatId,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };
    dispatch(addMessage(userMsg));

    // Add placeholder for AI response
    const aiPlaceholder = {
      id: crypto.randomUUID(),
      chat_id: targetChatId,
      role: 'assistant',
      content: '',
      model_used: null, // set from the server's reply (smart switch / fallback may change it)
      created_at: new Date().toISOString(),
    };
    dispatch(addMessage(aiPlaceholder));
    dispatch(setStreaming(true));

    const payload = { content, model_id: modelId, smart_switch: smartSwitch };
    let received = false;

    try {
      await streamMessage({
        chatId: targetChatId,
        body: payload,
        onEvent: (name, data) => {
          if (name === 'start') {
            // Which PDF pages the answer is grounded in
            dispatch(patchLastMessage({ metadata: { mode: data.mode, sources: data.sources } }));
          } else if (name === 'model') {
            dispatch(patchLastMessage({ model_used: data.model_used }));
          } else if (name === 'delta') {
            received = true;
            dispatch(updateLastMessage(data.text));
          } else if (name === 'done') {
            dispatch(replaceLastMessage(data));
          } else if (name === 'error') {
            throw new Error(data.detail);
          }
        },
      });
    } catch (err) {
      if (received) {
        // Keep the partial answer the user already saw, and say it was cut off
        dispatch(setChatError(err.message));
        toast.error('The answer was cut off.');
      } else {
        const message = err.message || "Couldn't get a response. Please try again.";
        dispatch(replaceLastMessage({ ...aiPlaceholder, content: message, isError: true }));
        dispatch(setChatError(message));
      }
    } finally {
      dispatch(setStreaming(false));
    }
  };

  return {
    chats,
    activeChatId,
    messages,
    isStreaming,
    isLoadingChats,
    isLoadingMessages,
    error,
    fetchChats,
    createChat,
    renameChat,
    deleteChat,
    selectChat,
    sendMessage,
  };
}
