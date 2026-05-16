import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  pdfs: [],                // Array of uploaded PDFs for the active chat
  uploadProgress: 0,       // 0-100
  isUploading: false,
  error: null,
};

const pdfSlice = createSlice({
  name: 'pdf',
  initialState,
  reducers: {
    setPdfs(state, action) {
      state.pdfs = action.payload;
    },
    addPdf(state, action) {
      state.pdfs.push(action.payload);
    },
    removePdf(state, action) {
      state.pdfs = state.pdfs.filter((p) => p.id !== action.payload);
    },
    setUploadProgress(state, action) {
      state.uploadProgress = action.payload;
    },
    setUploading(state, action) {
      state.isUploading = action.payload;
      if (!action.payload) {
        state.uploadProgress = 0;
      }
    },
    setPdfError(state, action) {
      state.error = action.payload;
      state.isUploading = false;
      state.uploadProgress = 0;
    },
    clearPdfs(state) {
      state.pdfs = [];
      state.uploadProgress = 0;
      state.isUploading = false;
      state.error = null;
    },
  },
});

export const {
  setPdfs,
  addPdf,
  removePdf,
  setUploadProgress,
  setUploading,
  setPdfError,
  clearPdfs,
} = pdfSlice.actions;

export default pdfSlice.reducer;
