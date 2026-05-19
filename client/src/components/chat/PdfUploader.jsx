import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useSelector, useDispatch } from 'react-redux';
import { Upload, X, FileText, AlertCircle, Trash2 } from 'lucide-react';
import { addPdf, setUploading, setUploadProgress, setPdfError, removePdf } from '../../features/pdf/pdfSlice';
import { canAddPdf, formatFileSize } from '../../utils/helpers';
import { PDF_LIMITS } from '../../utils/constants';
import axiosInstance from '../../api/axiosInstance';
import { PDFS } from '../../api/endpoints';

export default function PdfUploader({ onClose, compact = false }) {
  const dispatch = useDispatch();
  const { pdfs, isUploading, uploadProgress, error } = useSelector((state) => state.pdf);
  const { activeChatId } = useSelector((state) => state.chat);

  const handleDeletePdf = async (pdfId) => {
    try {
      await axiosInstance.delete(PDFS.DELETE(pdfId));
      dispatch(removePdf(pdfId));
    } catch (err) {
      dispatch(setPdfError(err.response?.data?.detail || 'Failed to delete PDF'));
    }
  };

  const onDrop = useCallback(
    async (acceptedFiles) => {
      const file = acceptedFiles[0];
      if (!file) return;

      // Validate file size
      if (file.size > PDF_LIMITS.MAX_FILE_SIZE_BYTES) {
        dispatch(setPdfError(`File too large. Max size is ${PDF_LIMITS.MAX_FILE_SIZE_MB}MB.`));
        return;
      }

      dispatch(setUploading(true));

      try {
        const formData = new FormData();
        formData.append('file', file);

        const { data } = await axiosInstance.post(PDFS.UPLOAD, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (e) => {
            const percent = Math.round((e.loaded * 100) / e.total);
            dispatch(setUploadProgress(percent));
          },
        });

        // Check smart multi-PDF limit
        if (!canAddPdf(pdfs, data.page_count)) {
          dispatch(
            setPdfError(
              `Can't add this PDF. Based on page counts, the limit has been reached.`
            )
          );
          return;
        }

        // Attach to chat if we're in one
        if (activeChatId) {
          await axiosInstance.post(PDFS.ATTACH(activeChatId), { pdf_id: data.id });
        }

        dispatch(addPdf(data));
        dispatch(setUploading(false));
      } catch (err) {
        dispatch(setPdfError(err.response?.data?.detail || 'Upload failed'));
      }
    },
    [dispatch, pdfs, activeChatId]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    disabled: isUploading,
  });

  return (
    <div className={`space-y-3 ${compact ? '' : 'max-w-3xl mx-auto glass rounded-xl border border-glass-border p-4'}`}>
      {!compact && (
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
            <FileText size={16} className="text-primary-400" />
            Upload PDF
          </h3>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-surface-600 text-text-muted hover:text-text-primary transition-colors"
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl text-center cursor-pointer transition-all duration-200 ${
          compact ? 'p-4' : 'p-6'
        } ${
          isDragActive
            ? 'border-primary-500 bg-primary-500/10'
            : 'border-glass-border hover:border-primary-500/40 hover:bg-surface-700/50'
        } ${isUploading ? 'pointer-events-none opacity-50' : ''}`}
      >
        <input {...getInputProps()} />
        <Upload size={compact ? 20 : 24} className="mx-auto text-text-muted mb-2" />
        {isDragActive ? (
          <p className="text-sm text-primary-400">Drop your PDF here</p>
        ) : (
          <>
            <p className={`text-text-secondary ${compact ? 'text-xs' : 'text-sm'}`}>
              Drag & drop a PDF, or <span className="text-primary-400">browse</span>
            </p>
            <p className="text-xs text-text-muted mt-1">Max {PDF_LIMITS.MAX_FILE_SIZE_MB}MB per file</p>
          </>
        )}
      </div>

      {/* Upload progress */}
      {isUploading && (
        <div className="space-y-1">
          <div className="h-1.5 bg-surface-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-primary-500 rounded-full transition-all duration-300"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
          <p className="text-xs text-text-muted text-right">{uploadProgress}%</p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 text-xs text-danger bg-danger/10 px-3 py-2 rounded-lg">
          <AlertCircle size={14} />
          {error}
        </div>
      )}

      {/* Uploaded PDFs list */}
      {pdfs.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs text-text-muted">
            {pdfs.length} PDF{pdfs.length > 1 ? 's' : ''} attached
          </p>
          {pdfs.map((pdf) => (
            <div
              key={pdf.id}
              className="flex items-center gap-2 bg-surface-700 rounded-lg px-3 py-2"
            >
              <FileText size={14} className="text-primary-400 flex-shrink-0" />
              <span className="text-xs text-text-primary truncate flex-1">
                {pdf.filename}
              </span>
              <span className="text-xs text-text-muted flex-shrink-0 mr-2">
                {pdf.page_count}p · {formatFileSize(pdf.file_size_bytes)}
              </span>
              <button
                onClick={() => handleDeletePdf(pdf.id)}
                className="p-1.5 rounded-md hover:bg-danger/20 text-text-muted hover:text-danger transition-colors flex-shrink-0"
                title="Remove PDF"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
