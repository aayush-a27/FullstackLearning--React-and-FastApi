import { configureStore } from '@reduxjs/toolkit';
import authReducer from '../features/auth/authSlice';
import chatReducer from '../features/chat/chatSlice';
import pdfReducer from '../features/pdf/pdfSlice';
import modelReducer from '../features/model/modelSlice';
import uiReducer from '../features/ui/uiSlice';

const store = configureStore({
  reducer: {
    auth: authReducer,
    chat: chatReducer,
    pdf: pdfReducer,
    model: modelReducer,
    ui: uiReducer,
  },
  devTools: import.meta.env.DEV,
});

export default store;
