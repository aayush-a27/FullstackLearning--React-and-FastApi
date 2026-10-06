import { createSlice } from '@reduxjs/toolkit';
import { AI_MODELS } from '../../utils/constants';

const initialState = {
  selectedModel: AI_MODELS[0],          // Default to first model (Nemotron Super)
  smartSwitchEnabled: true,             // Smart switch on by default
  availableModels: AI_MODELS,
  modelHealth: {},                       // { 'groq': 'healthy', 'google': 'degraded', ... }
  fallbackChain: ['nemotron-super', 'gemini-flash', 'groq-fast'],
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
    updateModelHealth(state, action) {
      // action.payload = { provider: 'openai', status: 'healthy' | 'degraded' | 'down' }
      state.modelHealth[action.payload.provider] = action.payload.status;
    },
    setFallbackChain(state, action) {
      state.fallbackChain = action.payload;
    },
  },
});

export const {
  setSelectedModel,
  toggleSmartSwitch,
  setSmartSwitch,
  setModelHealth,
  updateModelHealth,
  setFallbackChain,
} = modelSlice.actions;

export default modelSlice.reducer;
