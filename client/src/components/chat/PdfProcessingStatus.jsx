import { useSelector } from 'react-redux';
import { Loader2, CheckCircle2, AlertCircle, FileSearch } from 'lucide-react';
import { isPdfIndexing, isSummaryWriting } from '../../hooks/usePdfStatus';

/** Human-readable stage for a PDF that is still being indexed. */
function indexingStage(pdf) {
  if (pdf.status === 'pending') return 'Waiting to start…';
  const progress = pdf.progress ?? 0;
  if (progress < 10) return `Reading ${pdf.page_count} pages…`;
  if (progress < 95) return 'Indexing for search…';
  return 'Finishing up…';
}

function ProgressBar({ value, slim = false }) {
  return (
    <div className={`w-full bg-surface-600 rounded-full overflow-hidden ${slim ? 'h-1' : 'h-1.5'}`}>
      <div
        className="h-full bg-primary-500 rounded-full transition-all duration-700 ease-out"
        style={{ width: `${Math.max(3, value ?? 0)}%` }}
      />
    </div>
  );
}

/**
 * Large centered card, shown in an empty chat while its PDFs are indexed,
 * so the user knows why they should wait before asking anything.
 */
export function PdfPreparingCard() {
  const { pdfs } = useSelector((state) => state.pdf);
  const indexing = pdfs.filter(isPdfIndexing);
  if (!indexing.length) return null;

  return (
    <div className="h-full flex flex-col items-center justify-center animate-fade-in px-6">
      <div className="w-16 h-16 rounded-2xl bg-primary-500/10 border border-primary-500/20 flex items-center justify-center mb-4 animate-pulse-glow">
        <FileSearch size={28} className="text-primary-400" />
      </div>
      <h3 className="text-base font-semibold text-text-primary mb-1">
        Preparing your {indexing.length > 1 ? 'PDFs' : 'PDF'}
      </h3>
      <p className="text-xs text-text-muted text-center max-w-xs mb-5">
        We&apos;re reading and indexing it so answers can point to the right pages.
        Long documents can take a minute or two.
      </p>

      <div className="w-full max-w-sm space-y-4">
        {indexing.map((pdf) => (
          <div key={pdf.id} className="space-y-1.5">
            <div className="flex items-center justify-between gap-3 text-xs">
              <span className="text-text-primary truncate font-medium">{pdf.filename}</span>
              <span className="text-primary-400 tabular-nums flex-shrink-0">{pdf.progress ?? 0}%</span>
            </div>
            <ProgressBar value={pdf.progress} />
            <p className="text-[11px] text-text-muted flex items-center gap-1.5">
              <Loader2 size={11} className="animate-spin" />
              {indexingStage(pdf)}
            </p>
          </div>
        ))}
      </div>

      <p className="text-[11px] text-text-muted mt-6">
        You can ask questions as soon as it&apos;s ready.
      </p>
    </div>
  );
}

/**
 * Slim status strip above the chat input. Covers PDFs still being indexed
 * (input is disabled) and PDFs that are searchable but still being summarized.
 */
export function PdfStatusBanner({ hideIndexing = false }) {
  const { pdfs } = useSelector((state) => state.pdf);
  const indexing = hideIndexing ? [] : pdfs.filter(isPdfIndexing);
  const summarizing = pdfs.filter(isSummaryWriting);
  const failed = pdfs.filter((pdf) => pdf.status === 'failed');

  if (!indexing.length && !summarizing.length && !failed.length) return null;

  return (
    <div className="mb-2 space-y-1.5 animate-fade-in">
      {indexing.map((pdf) => (
        <div
          key={pdf.id}
          className="rounded-xl border border-warning/20 bg-warning/5 px-3 py-2 space-y-1.5"
        >
          <div className="flex items-center gap-2 text-xs">
            <Loader2 size={13} className="animate-spin text-warning flex-shrink-0" />
            <span className="text-text-primary truncate">
              Preparing <span className="font-medium">{pdf.filename}</span>
            </span>
            <span className="text-text-muted truncate hidden sm:inline">· {indexingStage(pdf)}</span>
            <span className="ml-auto text-warning tabular-nums flex-shrink-0">{pdf.progress ?? 0}%</span>
          </div>
          <ProgressBar value={pdf.progress} slim />
        </div>
      ))}

      {summarizing.map((pdf) => (
        <div
          key={pdf.id}
          className="flex items-center gap-2 rounded-xl border border-glass-border bg-surface-800/60 px-3 py-1.5 text-[11px]"
          title="Specific questions work now; summary questions will work once this finishes"
        >
          <CheckCircle2 size={12} className="text-primary-500 flex-shrink-0" />
          <span className="text-text-secondary truncate">
            <span className="text-text-primary">{pdf.filename}</span> is ready for questions
          </span>
          <span className="ml-auto flex items-center gap-1.5 text-text-muted flex-shrink-0">
            <Loader2 size={11} className="animate-spin" />
            Writing full summary {pdf.summary_progress ?? 0}%
          </span>
        </div>
      ))}

      {failed.map((pdf) => (
        <div
          key={pdf.id}
          className="flex items-center gap-2 rounded-xl border border-danger/20 bg-danger/5 px-3 py-1.5 text-[11px]"
        >
          <AlertCircle size={12} className="text-danger flex-shrink-0" />
          <span className="text-text-secondary truncate">
            <span className="text-text-primary">{pdf.filename}</span>:{' '}
            {pdf.status_message || "this PDF couldn't be read."}
          </span>
        </div>
      ))}
    </div>
  );
}
