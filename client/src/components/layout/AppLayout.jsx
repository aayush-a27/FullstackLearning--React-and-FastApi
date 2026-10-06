import { useCallback, useEffect, useRef } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import { X } from 'lucide-react';
import { setPanelWidths } from '../../features/ui/uiSlice';
import { ROUTES, MODAL_ROUTES, chatPath } from '../../utils/constants';
import { usePdfStatus } from '../../hooks/usePdfStatus';
import Navbar from './Navbar';
import PanelWrapper from './PanelWrapper';
import ResizeHandle from './ResizeHandle';
import ChatHistoryPanel from '../sidebar/LeftSidebar';
import PdfViewer from '../chat/PdfViewer';
import ChatArea from '../chat/ChatArea';
import ChatInput from '../chat/ChatInput';

const MIN_PANEL_PCT = 10; // Minimum 10% width per panel

// Map panel IDs to their React content
function PanelContent({ panelId }) {
  switch (panelId) {
    case 'history':
      return <ChatHistoryPanel />;
    case 'pdfViewer':
      return <PdfViewer />;
    case 'chat':
      return (
        <div className="flex flex-col h-full">
          <ChatArea />
          <ChatInput />
        </div>
      );
    default:
      return null;
  }
}

export default function AppLayout() {
  const dispatch = useDispatch();
  const { panelOrder, panelWidths } = useSelector((state) => state.ui);
  const containerRef = useRef(null);

  // Keep PDF indexing status fresh while documents are being processed
  usePdfStatus();

  // Handle resize of panels
  const handleResize = useCallback(
    (handleIndex, _delta, clientX) => {
      if (!containerRef.current) return;
      const containerRect = containerRef.current.getBoundingClientRect();
      const containerWidth = containerRect.width;

      // handleIndex is the index of the resize handle (0 = between panel 0 and 1, 1 = between panel 1 and 2)
      const leftPanelId = panelOrder[handleIndex];
      const rightPanelId = panelOrder[handleIndex + 1];

      // Calculate mouse position as percentage relative to container
      const mouseRelativeX = clientX - containerRect.left;
      const mousePct = (mouseRelativeX / containerWidth) * 100;

      // Calculate the total width before the left panel
      let leftEdgePct = 0;
      for (let i = 0; i < handleIndex; i++) {
        leftEdgePct += panelWidths[panelOrder[i]];
      }

      // New width for the left panel = mouse position minus its left edge
      let newLeftWidth = mousePct - leftEdgePct;
      // New width for right panel = total of both - new left width
      const totalBoth = panelWidths[leftPanelId] + panelWidths[rightPanelId];
      let newRightWidth = totalBoth - newLeftWidth;

      // Enforce minimums
      if (newLeftWidth < MIN_PANEL_PCT) {
        newLeftWidth = MIN_PANEL_PCT;
        newRightWidth = totalBoth - MIN_PANEL_PCT;
      }
      if (newRightWidth < MIN_PANEL_PCT) {
        newRightWidth = MIN_PANEL_PCT;
        newLeftWidth = totalBoth - MIN_PANEL_PCT;
      }

      dispatch(
        setPanelWidths({
          ...panelWidths,
          [leftPanelId]: newLeftWidth,
          [rightPanelId]: newRightWidth,
        })
      );
    },
    [dispatch, panelOrder, panelWidths]
  );

  return (
    <div className="h-screen flex flex-col bg-radial-gradient overflow-hidden">
      {/* Ambient background effects */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-primary-500/8 rounded-full blur-3xl" />
      </div>

      {/* Top Navbar */}
      <Navbar />

      {/* 3-Panel Area */}
      <div
        ref={containerRef}
        className="relative z-10 flex-1 flex min-h-0"
      >
        {panelOrder.map((panelId, index) => (
          <div key={panelId} className="contents">
            {/* Panel */}
            <PanelWrapper
              panelId={panelId}
              style={{ width: `${panelWidths[panelId]}%` }}
            >
              <PanelContent panelId={panelId} />
            </PanelWrapper>

            {/* Resize handle between panels (not after last) */}
            {index < panelOrder.length - 1 && (
              <ResizeHandle
                index={index}
                onResize={handleResize}
              />
            )}
          </div>
        ))}
      </div>

      {/* Outlet for Profile/Settings pages rendered as overlays */}
      <OutletOverlay />
    </div>
  );
}

// Profile/Settings open as a modal on top of the panel layout.
// On /dashboard and /chat/:id the Outlet is Dashboard, which renders nothing
// visible (it only syncs the open chat with the URL), so it's rendered as-is.
function OutletOverlay() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const activeChatId = useSelector((state) => state.chat.activeChatId);
  const isModal = MODAL_ROUTES.includes(pathname);

  // Closing returns to the chat that was open underneath
  const close = useCallback(() => {
    navigate(activeChatId ? chatPath(activeChatId) : ROUTES.DASHBOARD);
  }, [navigate, activeChatId]);

  useEffect(() => {
    if (!isModal) return undefined;
    const onKeyDown = (e) => {
      if (e.key === 'Escape') close();
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [isModal, close]);

  if (!isModal) return <Outlet />;

  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in"
      onMouseDown={close}
    >
      <div
        role="dialog"
        aria-modal="true"
        className="relative w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-2xl bg-surface-800 border border-glass-border shadow-2xl shadow-black/60 animate-slide-up"
        // Clicks inside the panel shouldn't close it
        onMouseDown={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          onClick={close}
          aria-label="Close"
          className="absolute top-4 right-4 z-10 p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-600 transition-colors"
        >
          <X size={18} />
        </button>
        <Outlet />
      </div>
    </div>
  );
}
