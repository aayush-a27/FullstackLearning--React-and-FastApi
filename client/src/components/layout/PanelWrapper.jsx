import { useDispatch, useSelector } from 'react-redux';
import { setDraggingPanel, setDropTarget, swapPanels } from '../../features/ui/uiSlice';
import { GripVertical } from 'lucide-react';

const PANEL_TITLES = {
  history: 'Chat History',
  pdfViewer: 'PDF Viewer',
  chat: 'Chat',
};

const PANEL_ICONS = {
  history: '💬',
  pdfViewer: '📄',
  chat: '✨',
};

export default function PanelWrapper({ panelId, children, style }) {
  const dispatch = useDispatch();
  const { draggingPanel, dropTarget, panelOrder } = useSelector((state) => state.ui);

  const isDragging = draggingPanel === panelId;
  const isDropTarget = dropTarget === panelId && draggingPanel !== panelId;

  const handleDragStart = (e) => {
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', panelId);
    // Delay so the drag image captures current state
    requestAnimationFrame(() => {
      dispatch(setDraggingPanel(panelId));
    });
  };

  const handleDragEnd = () => {
    dispatch(setDraggingPanel(null));
    dispatch(setDropTarget(null));
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (draggingPanel && draggingPanel !== panelId) {
      dispatch(setDropTarget(panelId));
    }
  };

  const handleDragLeave = () => {
    if (dropTarget === panelId) {
      dispatch(setDropTarget(null));
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const fromPanelId = e.dataTransfer.getData('text/plain');
    if (fromPanelId && fromPanelId !== panelId) {
      const fromIndex = panelOrder.indexOf(fromPanelId);
      const toIndex = panelOrder.indexOf(panelId);
      if (fromIndex !== -1 && toIndex !== -1) {
        dispatch(swapPanels({ fromIndex, toIndex }));
      }
    }
    dispatch(setDraggingPanel(null));
    dispatch(setDropTarget(null));
  };

  return (
    <div
      className={`flex flex-col h-full overflow-hidden glass ${
        isDragging ? 'panel-dragging' : ''
      } ${isDropTarget ? 'panel-drop-target' : ''}`}
      style={style}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Drag header */}
      <div className="panel-header">
        <div
          className="panel-drag-handle"
          draggable
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
          title="Drag to reorder"
        >
          <GripVertical size={16} />
        </div>
        <span className="text-sm" aria-hidden="true">
          {PANEL_ICONS[panelId]}
        </span>
        <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
          {PANEL_TITLES[panelId]}
        </span>
      </div>

      {/* Panel content */}
      <div className="flex-1 overflow-hidden">
        {children}
      </div>
    </div>
  );
}
