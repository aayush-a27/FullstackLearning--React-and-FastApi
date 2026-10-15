import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  chats: [],              // Array of chat session objects
  activeChatId: null,     // Currently selected chat
  messages: [],           // Messages for the active chat
  isStreaming: false,      // Whether AI is currently responding
  isLoadingChats: false,
  isLoadingMessages: false,
  error: null,
};

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    setChats(state, action) {
      state.chats = action.payload;
      state.isLoadingChats = false;
    },
    setLoadingChats(state, action) {
      state.isLoadingChats = action.payload;
    },
    addChat(state, action) {
      state.chats.unshift(action.payload);
    },
    updateChat(state, action) {
      const index = state.chats.findIndex((c) => c.id === action.payload.id);
      if (index !== -1) state.chats[index] = { ...state.chats[index], ...action.payload };
    },
    removeChat(state, action) {
      state.chats = state.chats.filter((c) => c.id !== action.payload);
      if (state.activeChatId === action.payload) {
        state.activeChatId = null;
        state.messages = [];
      }
    },
    setActiveChat(state, action) {
      state.activeChatId = action.payload;
    },
    setMessages(state, action) {
      state.messages = action.payload;
      state.isLoadingMessages = false;
    },
    setLoadingMessages(state, action) {
      state.isLoadingMessages = action.payload;
    },
    addMessage(state, action) {
      state.messages.push(action.payload);
    },
    /** Swap one message (found by id) for another, e.g. a temporary one for the saved one. */
    replaceMessage(state, action) {
      const { id, message } = action.payload;
      const index = state.messages.findIndex((m) => m.id === id);
      if (index !== -1) state.messages[index] = message;
    },
    /** Drop the message at `index` and everything after it (edit / try again). */
    truncateMessages(state, action) {
      state.messages = state.messages.slice(0, action.payload);
    },
    replaceLastMessage(state, action) {
      if (state.messages.length > 0) {
        state.messages[state.messages.length - 1] = action.payload;
      }
    },
    patchLastMessage(state, action) {
      const lastMsg = state.messages[state.messages.length - 1];
      if (lastMsg) Object.assign(lastMsg, action.payload);
    },
    updateLastMessage(state, action) {
      const lastMsg = state.messages[state.messages.length - 1];
      if (lastMsg) {
        lastMsg.content += action.payload;
      }
    },
    setStreaming(state, action) {
      state.isStreaming = action.payload;
    },
    setChatError(state, action) {
      state.error = action.payload;
    },
  },
});

export const {
  setChats,
  setLoadingChats,
  addChat,
  updateChat,
  removeChat,
  setActiveChat,
  setMessages,
  setLoadingMessages,
  addMessage,
  replaceMessage,
  truncateMessages,
  replaceLastMessage,
  patchLastMessage,
  updateLastMessage,
  setStreaming,
  setChatError,
} = chatSlice.actions;

export default chatSlice.reducer;
