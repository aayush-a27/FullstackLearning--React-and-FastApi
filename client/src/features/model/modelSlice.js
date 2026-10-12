import { createSlice } from '@reduxjs/toolkit';
import { AI_MODELS } from '../../utils/constants';

// Remembered across reloads; app/store.js writes it back when it changes
export const SMART_SWITCH_KEY = 'smartSwitchEnabled';

function loadSmartSwitch() {
  try {
    return localStorage.getItem(SMART_SWITCH_KEY) !== 'false'; // on by default
  } catch {
    return true; // storage blocked (private mode, etc.)
  }
}

const initialState = {
  selectedModel: AI_MODELS[0],          // Default to first model (Nemotron Super)
  smartSwitchEnabled: loadSmartSwitch(),
  availableModels: AI_MODELS,
  modelHealth: {},                       // { 'groq': 'healthy', 'google': 'degraded', ... }
};

const modelSlice = createSlice({
  name: 'model',
  initialState,
  reducers: {
    setSelectedModel(state, action) {
      const model = state.availableModels.find((m) => m.id === action.payload);
      if (model) {
        state.selectedModel = model;
      }
    },
    toggleSmartSwitch(state) {
      state.smartSwitchEnabled = !state.smartSwitchEnabled;
    },
    setSmartSwitch(state, action) {
      state.smartSwitchEnabled = action.payload;
    },
    setModelHealth(state, action) {
      // action.payload = { groq: 'healthy', google: 'degraded', nvidia: 'down' }
      state.modelHealth = action.payload;
    },
  },
});

export const {
  setSelectedModel,
  toggleSmartSwitch,
  setSmartSwitch,
  setModelHealth,
} = modelSlice.actions;

export default modelSlice.reducer;
