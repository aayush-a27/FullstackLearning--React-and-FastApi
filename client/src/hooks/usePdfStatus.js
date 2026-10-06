import { useEffect, useRef } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import toast from 'react-hot-toast';
import axiosInstance from '../api/axiosInstance';
import { PDFS } from '../api/endpoints';
import { updatePdf } from '../features/pdf/pdfSlice';

const POLL_INTERVAL_MS = 2000;

/** True while a PDF is still being read, chunked or embedded. */
export function isPdfIndexing(pdf) {
  return pdf?.status === 'pending' || pdf?.status === 'processing';
}

/** True once the text is searchable, even if the summary is still being written. */
export function isPdfReady(pdf) {
  return pdf?.status === 'ready';
}

/** Searchable, but the whole-document summary isn't finished yet. */
export function isSummaryWriting(pdf) {
  return (
    pdf?.status === 'ready' &&
    (pdf.summary_status === 'pending' || pdf.summary_status === 'processing')
  );
}

function needsPolling(pdf) {
  return isPdfIndexing(pdf) || isSummaryWriting(pdf) || (pdf?.status === 'ready' && !pdf.summary_status);
}

/**
 * Poll the server while any attached PDF is still being indexed or summarized,
 * so the UI can show real progress. Mount this once, high in the tree.
 */
export function usePdfStatus() {
  const dispatch = useDispatch();
  const { pdfs } = useSelector((state) => state.pdf);

  // The interval below reads the latest list without restarting on every change
  const pdfsRef = useRef(pdfs);
  useEffect(() => {
    pdfsRef.current = pdfs;
  }, [pdfs]);

  const active = pdfs.some(needsPolling);

  useEffect(() => {
    if (!active) return undefined;

    let cancelled = false;
    let inFlight = false;
    const poll = async () => {
      // Skip a tick rather than overlap requests (and double-fire the toasts)
      if (inFlight) return;
      inFlight = true;
      const unfinished = pdfsRef.current.filter(needsPolling);
      await Promise.all(
        unfinished.map(async (pdf) => {
          try {
            const { data } = await axiosInstance.get(PDFS.GET(pdf.id));
            if (cancelled) return;
            if (isPdfIndexing(pdf) && data.status === 'ready') {
              toast.success(`${data.filename} is ready — ask away!`);
            } else if (isPdfIndexing(pdf) && data.status === 'failed') {
              toast.error(data.status_message || `${data.filename} couldn't be read.`);
            }
            dispatch(updatePdf(data));
          } catch {
            // Keep polling; a transient failure shouldn't stop status updates
          }
        })
      );
      inFlight = false;
    };

    poll();
    const timer = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [active, dispatch]);
}
