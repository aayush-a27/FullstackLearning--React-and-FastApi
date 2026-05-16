import { useSelector, useDispatch } from 'react-redux';
import axiosInstance from '../api/axiosInstance';
import { CHATS, MESSAGES } from '../api/endpoints';
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

  const fetchChats = async () => {
    try {
      dispatch(setLoadingChats(true));
      const { data } = await axiosInstance.get(CHATS.LIST);
      dispatch(setChats(data));
    } catch (err) {
      dispatch(setChatError(err.response?.data?.detail || 'Failed to load chats'));
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
    try {
      dispatch(setLoadingMessages(true));
      const { data } = await axiosInstance.get(MESSAGES.LIST(chatId));
      dispatch(setMessages(data));
    } catch (err) {
      dispatch(setChatError(err.response?.data?.detail || 'Failed to load messages'));
    }
  };

  const sendMessage = async (chatId, content, modelId) => {
    // Add user message immediately
    const userMsg = {
      id: crypto.randomUUID(),
      chat_id: chatId,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };
    dispatch(addMessage(userMsg));

    // Add placeholder for AI response
    const aiPlaceholder = {
      id: crypto.randomUUID(),
      chat_id: chatId,
      role: 'assistant',
      content: '',
      model_used: modelId,
      created_at: new Date().toISOString(),
    };
    dispatch(addMessage(aiPlaceholder));
    dispatch(setStreaming(true));

    try {
      const { data } = await axiosInstance.post(MESSAGES.SEND(chatId), {
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
