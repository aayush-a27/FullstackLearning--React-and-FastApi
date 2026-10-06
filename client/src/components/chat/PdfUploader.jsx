import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useSelector, useDispatch } from 'react-redux';
import { Upload, X, FileText, AlertCircle, Trash2, Loader2, CheckCircle2 } from 'lucide-react';
import { addPdf, setUploading, setUploadProgress, setPdfError, removePdf } from '../../features/pdf/pdfSlice';
import { canAddPdf, formatFileSize, getMaxPdfsAllowed, getFriendlyError } from '../../utils/helpers';
import { PDF_LIMITS } from '../../utils/constants';
import axiosInstance from '../../api/axiosInstance';
import { PDFS } from '../../api/endpoints';
import { isPdfIndexing } from '../../hooks/usePdfStatus';

/** Small badge showing where a PDF is in the indexing pipeline. */
function PdfStatus({ pdf }) {
  if (isPdfIndexing(pdf)) {
    return (
      <span className="flex items-center gap-1 text-[10px] text-warning flex-shrink-0" title="Reading and indexing this PDF">
        <Loader2 size={11} className="animate-spin" />
        Indexing
      </span>
    );
  }
  if (pdf.status === 'failed') {
    return (
      <span className="flex items-center gap-1 text-[10px] text-danger flex-shrink-0" title={pdf.status_message || 'This PDF could not be read'}>
        <AlertCircle size={11} />
        Failed
      </span>
    );
  }
  if (pdf.summary_status === 'processing' || pdf.summary_status === 'pending') {
    return (
      <span className="flex items-center gap-1 text-[10px] text-text-muted flex-shrink-0" title="Searchable now; the full-document summary is still being written">
        <CheckCircle2 size={11} className="text-primary-500" />
        Searchable
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1 text-[10px] text-primary-400 flex-shrink-0" title="Indexed and summarized">
      <CheckCircle2 size={11} />
      Ready
    </span>
  );
}

export default function PdfUploader({ onClose, compact = false }) {
  const dispatch = useDispatch();
  const { pdfs, isUploading, uploadProgress, error } = useSelector((state) => state.pdf);
  const { activeChatId } = useSelector((state) => state.chat);

  const handleDeletePdf = async (pdfId) => {
    try {
      await axiosInstance.delete(PDFS.DELETE(pdfId));
      dispatch(removePdf(pdfId));
    } catch (err) {
      dispatch(setPdfError(getFriendlyError(err, "Couldn't remove that PDF. Please try again.")));
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

      // Quick check before uploading: already at the limit for the PDFs in this chat
      if (pdfs.length >= getMaxPdfsAllowed(pdfs)) {
        dispatch(setPdfError('This chat already has the maximum number of PDFs. Start a new chat to add more.'));
        return;
      }

      dispatch(setUploading(true));
      let uploadedId = null;

      try {
        const formData = new FormData();
        formData.append('file', file);

        const { data } = await axiosInstance.post(PDFS.UPLOAD, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          // The default 30s timeout includes upload time — too short for big files on slow connections
          timeout: 5 * 60 * 1000,
          onUploadProgress: (e) => {
            const percent = Math.round((e.loaded * 100) / e.total);
            dispatch(setUploadProgress(percent));
          },
        });

        uploadedId = data.id;

        // Check smart multi-PDF limit (page count is only known after upload)
        if (!canAddPdf(pdfs, data.page_count)) {
          await axiosInstance.delete(PDFS.DELETE(uploadedId)).catch(() => {});
          dispatch(
            setPdfError(
              `This PDF has ${data.page_count} pages, so it can't be added alongside the PDFs already in this chat. Start a new chat for it.`
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
        // Don't leave an orphaned upload behind if attaching it failed
        if (uploadedId) {
          await axiosInstance.delete(PDFS.DELETE(uploadedId)).catch(() => {});
        }
        dispatch(setPdfError(getFriendlyError(err, "Couldn't upload this PDF. Please try again.")));
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
              <span className="text-xs text-text-muted flex-shrink-0">
                {pdf.page_count}p · {formatFileSize(pdf.file_size_bytes)}
              </span>
              <PdfStatus pdf={pdf} />
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
