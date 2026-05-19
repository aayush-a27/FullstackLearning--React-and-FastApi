import { useSelector, useDispatch } from 'react-redux';
import axiosInstance from '../api/axiosInstance';
import { CHATS, MESSAGES } from '../api/endpoints';
import { setPdfs, clearPdfs } from '../features/pdf/pdfSlice';
import {
  setChats,
  setLoadingChats,
  addChat,
  removeChat,
  setActiveChat,
  setMessages,
  setLoadingMessages,
  addMessage,
  updateLastMessage,
  setStreaming,
  setChatError,
} from '../features/chat/chatSlice';

export function useChat() {
  const dispatch = useDispatch();
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

  const fetchChats = async () => {
    try {
      dispatch(setLoadingChats(true));
      const { data } = await axiosInstance.get(CHATS.LIST);
      dispatch(setChats(data));
      return data;
    } catch (err) {
      dispatch(setChatError(err.response?.data?.detail || 'Failed to load chats'));
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
      dispatch(setChatError(err.response?.data?.detail || 'Failed to create chat'));
      return null;
    }
  };

  const deleteChat = async (chatId) => {
    try {
      await axiosInstance.delete(CHATS.DELETE(chatId));
      dispatch(removeChat(chatId));
    } catch (err) {
      dispatch(setChatError(err.response?.data?.detail || 'Failed to delete chat'));
    }
  };

  const selectChat = async (chatId) => {
    dispatch(setActiveChat(chatId));
    
    // Sync PDFs for the selected chat
    const chat = chats.find(c => c.id === chatId);
    if (chat && chat.pdf_documents) {
      dispatch(setPdfs(chat.pdf_documents));
    } else {
      dispatch(clearPdfs());
    }

    try {
      if (chatId) {
        dispatch(setLoadingMessages(true));
        const { data } = await axiosInstance.get(MESSAGES.LIST(chatId));
        dispatch(setMessages(data));
      } else {
        dispatch(setMessages([]));
      }
    } catch (err) {
      dispatch(setChatError(err.response?.data?.detail || 'Failed to load messages'));
    }
  };

  const sendMessage = async (chatId, content, modelId) => {
    let targetChatId = chatId;

    // Create chat on the fly if it doesn't exist
    if (!targetChatId) {
      dispatch(setStreaming(true));
      const newChat = await createChat(content.slice(0, 30) + (content.length > 30 ? '...' : ''), pdfs.map(p => p.id));
      if (!newChat) {
        dispatch(setStreaming(false));
        return; // createChat handles error toast
      }
      targetChatId = newChat.id;
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
      model_used: modelId,
      created_at: new Date().toISOString(),
    };
    dispatch(addMessage(aiPlaceholder));
    dispatch(setStreaming(true));

    try {
      const { data } = await axiosInstance.post(MESSAGES.SEND(targetChatId), {
        content,
        model_id: modelId,
      });

      // Replace the placeholder content with real response
      // For now using simple request/response; streaming can be added later
      dispatch(updateLastMessage(data.content));
    } catch (err) {
      dispatch(updateLastMessage('⚠️ Failed to get response. Please try again.'));
      dispatch(setChatError(err.response?.data?.detail || 'Failed to send message'));
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
    deleteChat,
    selectChat,
    sendMessage,
  };
}
