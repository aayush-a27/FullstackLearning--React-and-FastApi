import { createSlice } from '@reduxjs/toolkit';
import { AI_MODELS } from '../../utils/constants';

const initialState = {
  selectedModel: AI_MODELS[0],          // Default to first model (GPT-4o)
  smartSwitchEnabled: true,             // Smart switch on by default
  availableModels: AI_MODELS,
  modelHealth: {},                       // { 'openai': 'healthy', 'google': 'degraded', ... }
  fallbackChain: ['gpt-4o', 'gemini-pro', 'claude-sonnet', 'gpt-4o-mini', 'llama-local'],
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
  updateModelHealth,
  setFallbackChain,
} = modelSlice.actions;

export default modelSlice.reducer;
