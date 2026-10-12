import { configureStore } from '@reduxjs/toolkit';
import authReducer from '../features/auth/authSlice';
import chatReducer from '../features/chat/chatSlice';
import pdfReducer from '../features/pdf/pdfSlice';
import modelReducer, { SMART_SWITCH_KEY } from '../features/model/modelSlice';
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

// Save the smart switch choice so it survives a reload. It can be flipped from
// both the sidebar and Settings, so this watches the store instead of either one.
let savedSmartSwitch = store.getState().model.smartSwitchEnabled;
store.subscribe(() => {
  const { smartSwitchEnabled } = store.getState().model;
  if (smartSwitchEnabled === savedSmartSwitch) return;
  savedSmartSwitch = smartSwitchEnabled;
  try {
    localStorage.setItem(SMART_SWITCH_KEY, String(smartSwitchEnabled));
  } catch {
    // Storage unavailable: the choice just lasts until the next reload
  }
});

export default store;
