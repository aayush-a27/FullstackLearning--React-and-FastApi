import { useEffect, useRef, useState } from 'react';
import { AlertCircle } from 'lucide-react';
import Loader from '../common/Loader';

/*
 * Draws a PDF with pdf.js, for browsers that can't show one in an iframe —
 * Android Chrome shows only an "Open" button there, and iOS Safari only the
 * first page. pdf.js is loaded on first use, so desktop never downloads it.
 *
 * Pages are drawn as they scroll near the screen and cleared once far away,
 * so a several-hundred-page book doesn't exhaust a phone's memory.
 */

// Start drawing a page this far before it scrolls into view
const NEAR_SCREEN = '1200px 0px';

let pdfjsPromise = null;
function loadPdfjs() {
  pdfjsPromise ??= Promise.all([
    import('pdfjs-dist'),
    import('pdfjs-dist/build/pdf.worker.min.mjs?url'),
  ]).then(([pdfjs, worker]) => {
    pdfjs.GlobalWorkerOptions.workerSrc = worker.default;
    return pdfjs;
  });
  return pdfjsPromise;
}

function PdfPage({ doc, pageNumber, aspectRatio, width, scrollRoot }) {
  const holderRef = useRef(null);
  const canvasRef = useRef(null);
  const [near, setNear] = useState(false);
  // Until drawn, assume the first page's shape; then use this page's own
  const [ownAspectRatio, setOwnAspectRatio] = useState(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => setNear(entry.isIntersecting),
      // Measured against the scrolling page list, so the margin means
      // "about to scroll into the panel", not into the window
      { root: scrollRoot, rootMargin: NEAR_SCREEN }
    );
    observer.observe(holderRef.current);
    return () => observer.disconnect();
  }, [scrollRoot]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!near || !width || !canvas) return undefined;
    let task = null;
    let cancelled = false;

    doc.getPage(pageNumber).then((page) => {
      if (cancelled) return;
      const natural = page.getViewport({ scale: 1 });
      setOwnAspectRatio(`${natural.width} / ${natural.height}`);
      // Sharp on high-density phone screens, capped to bound memory per page
      const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
      const viewport = page.getViewport({ scale: (width / natural.width) * pixelRatio });
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      task = page.render({ canvas, viewport });
      task.promise.catch(() => {}); // cancelled when scrolled away
    });

    return () => {
      cancelled = true;
      task?.cancel();
      // Free the bitmap once the page is far off screen
      canvas.width = 0;
      canvas.height = 0;
    };
  }, [doc, pageNumber, near, width]);

  return (
    <div
      ref={holderRef}
      className="bg-white rounded shadow-md shadow-black/40 overflow-hidden"
      style={{ width, aspectRatio: ownAspectRatio || aspectRatio }}
    >
      {/* 0×0 until drawn: a default canvas is 300×150, which adds up over hundreds of pages */}
      <canvas ref={canvasRef} width={0} height={0} className="w-full h-full" aria-label={`Page ${pageNumber}`} />
    </div>
  );
}

export default function PdfCanvasViewer({ data, title }) {
  // State, not a ref: pages need the element during render (as their observer root)
  const [scrollEl, setScrollEl] = useState(null);
  const [state, setState] = useState({ doc: null, aspectRatio: null, error: null });
  const [width, setWidth] = useState(0);

  // Load the document
  useEffect(() => {
    let doc = null;
    let cancelled = false;
    loadPdfjs()
      // pdf.js takes over (detaches) the buffer it's given, so hand it a copy;
      // the caller's data must survive for the next time this panel opens
      .then((pdfjs) => pdfjs.getDocument({ data: new Uint8Array(data.slice(0)) }).promise)
      .then(async (loaded) => {
        doc = loaded;
        // Placeholders use the first page's shape until each page is drawn
        const first = (await loaded.getPage(1)).getViewport({ scale: 1 });
        if (!cancelled) setState({ doc: loaded, aspectRatio: `${first.width} / ${first.height}`, error: null });
      })
      .catch(() => {
        if (!cancelled) setState({ doc: null, aspectRatio: null, error: 'Could not display this PDF.' });
      });
    return () => {
      cancelled = true;
      doc?.destroy();
    };
  }, [data]);

  // Pages fill the panel width (minus padding), and follow rotation/resizes
  useEffect(() => {
    if (!scrollEl) return undefined;
    const observer = new ResizeObserver(([entry]) => {
      setWidth(Math.floor(entry.contentRect.width));
    });
    observer.observe(scrollEl);
    return () => observer.disconnect();
  }, [scrollEl]);

  const { doc, aspectRatio, error } = state;

  return (
    <div
      ref={setScrollEl}
      className="h-full overflow-y-auto overscroll-contain px-2 py-2 space-y-3"
      aria-label={title}
    >
      {error ? (
        <div className="h-full flex items-center justify-center gap-2 text-xs text-danger">
          <AlertCircle size={14} />
          {error}
        </div>
      ) : !doc || !width ? (
        <div className="h-full flex items-center justify-center">
          <Loader size="md" text="Loading PDF..." />
        </div>
      ) : (
        Array.from({ length: doc.numPages }, (_, i) => (
          <PdfPage
            key={i + 1}
            doc={doc}
            pageNumber={i + 1}
            aspectRatio={aspectRatio}
            width={width}
            scrollRoot={scrollEl}
          />
        ))
      )}
    </div>
  );
}
