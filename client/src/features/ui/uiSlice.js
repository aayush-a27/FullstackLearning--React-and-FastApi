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
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
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
  },
});

export const {
  swapPanels,
  setPanelWidths,
  setDraggingPanel,
  setDropTarget,
} = uiSlice.actions;

export default uiSlice.reducer;
