import { useState, useCallback } from 'react';

export default function ResizeHandle({ onResize, index }) {
  const [isActive, setIsActive] = useState(false);

  const handleMouseDown = useCallback(
    (e) => {
      e.preventDefault();
      setIsActive(true);
      document.body.classList.add('no-select');
      document.body.style.cursor = 'col-resize';

      const startX = e.clientX;

      const handleMouseMove = (moveEvent) => {
        const delta = moveEvent.clientX - startX;
        onResize(index, delta, moveEvent.clientX);
      };

      const handleMouseUp = () => {
        setIsActive(false);
        document.body.classList.remove('no-select');
        document.body.style.cursor = '';
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };

      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    },
    [onResize, index]
  );

  return (
    <div
      className={`resize-handle ${isActive ? 'active' : ''}`}
      onMouseDown={handleMouseDown}
      title="Drag to resize"
    />
  );
}
