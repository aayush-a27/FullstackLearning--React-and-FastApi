import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  leftSidebarOpen: true,
  rightSidebarOpen: true,
  activeModal: null,       // 'profile' | 'settings' | 'upload' | null
  isMobile: false,
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    toggleLeftSidebar(state) {
      state.leftSidebarOpen = !state.leftSidebarOpen;
    },
    toggleRightSidebar(state) {
      state.rightSidebarOpen = !state.rightSidebarOpen;
    },
    setLeftSidebar(state, action) {
      state.leftSidebarOpen = action.payload;
    },
    setRightSidebar(state, action) {
      state.rightSidebarOpen = action.payload;
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
  toggleLeftSidebar,
  toggleRightSidebar,
  setLeftSidebar,
  setRightSidebar,
  openModal,
  closeModal,
  setMobile,
} = uiSlice.actions;

export default uiSlice.reducer;
