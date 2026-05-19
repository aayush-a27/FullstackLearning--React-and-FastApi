import { useSelector } from 'react-redux';
import { FileText, Upload, Eye } from 'lucide-react';
import PdfUploader from './PdfUploader';
import { API_BASE_URL } from '../../utils/constants';

export default function PdfViewer() {
  const { pdfs } = useSelector((state) => state.pdf);

  // Get the first uploaded PDF (primary PDF for viewing)
  const activePdf = pdfs.length > 0 ? pdfs[0] : null;

  // Construct PDF view URL
  const pdfViewUrl = activePdf
    ? `${API_BASE_URL}/pdfs/${activePdf.id}/view`
    : null;

  return (
    <div className="h-full flex flex-col">
      {activePdf ? (
        /* PDF is uploaded — show viewer */
        <>
          {/* PDF info bar */}
          <div className="flex items-center gap-2 px-3 py-2 border-b border-glass-border bg-surface-800/50">
            <Eye size={14} className="text-primary-400" />
            <span className="text-xs text-text-primary truncate flex-1 font-medium">
              {activePdf.filename}
            </span>
            <span className="text-xs text-text-muted flex-shrink-0">
              {activePdf.page_count} pages
            </span>
          </div>

          {/* PDF iframe */}
          <div className="flex-1 p-2">
            <iframe
              src={pdfViewUrl}
              className="pdf-viewer-frame"
              title={`PDF Viewer — ${activePdf.filename}`}
            />
          </div>
        </>
      ) : (
        /* No PDF uploaded — show upload prompt */
        <div className="h-full flex flex-col">
          {/* Empty state */}
          <div className="flex-1 flex flex-col items-center justify-center p-6">
            <div className="w-16 h-16 rounded-2xl bg-primary-500/10 border border-primary-500/20 flex items-center justify-center mb-4 animate-pulse-glow">
              <FileText size={28} className="text-primary-400" />
            </div>
            <h3 className="text-base font-semibold text-text-primary mb-1">
              No PDF Loaded
            </h3>
            <p className="text-xs text-text-muted text-center max-w-xs mb-5">
              Upload a PDF document to view it here. You can ask questions about the content in the chat panel.
            </p>

            {/* Inline uploader */}
            <div className="w-full max-w-sm">
              <PdfUploader onClose={() => {}} compact />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
