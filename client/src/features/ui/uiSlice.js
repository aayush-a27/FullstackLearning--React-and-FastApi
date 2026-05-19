import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  // Panel order — determines left-to-right arrangement
  panelOrder: ['history', 'pdfViewer', 'chat'],
  // Panel widths as percentages (must sum to 100)
  panelWidths: { history: 20, pdfViewer: 40, chat: 40 },
  // Minimum panel width in pixels
  minPanelWidth: 200,
  // Drag-and-drop state
  draggingPanel: null,       // panel id being dragged
  dropTarget: null,          // panel id being hovered over
  // Legacy (kept for Profile/Settings pages if needed)
  activeModal: null,         // 'profile' | 'settings' | 'upload' | null
  isMobile: false,
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setPanelOrder(state, action) {
      state.panelOrder = action.payload;
    },
    swapPanels(state, action) {
      const { fromIndex, toIndex } = action.payload;
      const newOrder = [...state.panelOrder];
      const temp = newOrder[fromIndex];
      newOrder[fromIndex] = newOrder[toIndex];
      newOrder[toIndex] = temp;
      state.panelOrder = newOrder;
    },
    setPanelWidths(state, action) {
      state.panelWidths = action.payload;
    },
    setDraggingPanel(state, action) {
      state.draggingPanel = action.payload;
    },
    setDropTarget(state, action) {
      state.dropTarget = action.payload;
    },
    openModal(state, action) {
      state.activeModal = action.payload;
    },
    closeModal(state) {
      state.activeModal = null;
    },
    setMobile(state, action) {
      state.isMobile = action.payload;
    },
  },
});

export const {
  setPanelOrder,
  swapPanels,
  setPanelWidths,
  setDraggingPanel,
  setDropTarget,
  openModal,
  closeModal,
  setMobile,
} = uiSlice.actions;

export default uiSlice.reducer;
