import { useEffect, useState } from 'react';
import { useSelector } from 'react-redux';
import { FileText, Eye, AlertCircle, Loader2, CheckCircle2 } from 'lucide-react';
import PdfUploader from './PdfUploader';
import Loader from '../common/Loader';
import axiosInstance from '../../api/axiosInstance';
import { PDFS } from '../../api/endpoints';
import { isPdfIndexing, isSummaryWriting } from '../../hooks/usePdfStatus';

/** Compact indexing state next to the file name. */
function IndexingBadge({ pdf }) {
  if (isPdfIndexing(pdf)) {
    return (
      <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-warning/10 border border-warning/20 text-warning flex-shrink-0">
        <Loader2 size={10} className="animate-spin" />
        Preparing {pdf.progress ?? 0}%
      </span>
    );
  }
  if (pdf.status === 'failed') {
    return (
      <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-danger/10 border border-danger/20 text-danger flex-shrink-0">
        <AlertCircle size={10} />
        Couldn&apos;t read
      </span>
    );
  }
  if (isSummaryWriting(pdf)) {
    return (
      <span
        className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-primary-500/10 border border-primary-500/20 text-primary-400 flex-shrink-0"
        title="Ready for questions. The full-document summary is still being written."
      >
        <CheckCircle2 size={10} />
        Ready · summary {pdf.summary_progress ?? 0}%
      </span>
    );
  }
  if (pdf.status === 'ready') {
    return (
      <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-primary-500/10 border border-primary-500/20 text-primary-400 flex-shrink-0">
        <CheckCircle2 size={10} />
        Ready
      </span>
    );
  }
  return null;
}

export default function PdfViewer() {
  const { pdfs } = useSelector((state) => state.pdf);

  // Get the first uploaded PDF (primary PDF for viewing)
  const activePdf = pdfs.length > 0 ? pdfs[0] : null;
  const activePdfId = activePdf?.id;

  // An iframe can't send the Bearer token, so fetch the file with axios
  // and show it from a local blob URL instead.
  // Keyed by PDF id so a stale result from a previous PDF is never shown.
  const [viewState, setViewState] = useState({ pdfId: null, url: null, error: null });
  const isCurrent = viewState.pdfId === activePdfId;
  const pdfViewUrl = isCurrent ? viewState.url : null;
  const loadError = isCurrent ? viewState.error : null;

  useEffect(() => {
    if (!activePdfId) return undefined;
    let objectUrl = null;
    let cancelled = false;

    axiosInstance
      .get(PDFS.VIEW(activePdfId), { responseType: 'blob', timeout: 120000 })
      .then(({ data }) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(new Blob([data], { type: 'application/pdf' }));
        setViewState({ pdfId: activePdfId, url: objectUrl, error: null });
      })
      .catch(() => {
        if (!cancelled) {
          setViewState({ pdfId: activePdfId, url: null, error: 'Could not load this PDF.' });
        }
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [activePdfId]);

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
            <IndexingBadge pdf={activePdf} />
            <span className="text-xs text-text-muted flex-shrink-0">
              {activePdf.page_count} pages
            </span>
          </div>

          {/* PDF iframe */}
          <div className="flex-1 p-2">
            {loadError ? (
              <div className="h-full flex items-center justify-center gap-2 text-xs text-danger">
                <AlertCircle size={14} />
                {loadError}
              </div>
            ) : pdfViewUrl ? (
              <iframe
                src={pdfViewUrl}
                className="pdf-viewer-frame"
                title={`PDF Viewer — ${activePdf.filename}`}
              />
            ) : (
              <div className="h-full flex items-center justify-center">
                <Loader size="md" text="Loading PDF..." />
              </div>
            )}
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
