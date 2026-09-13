import React, { useEffect } from 'react';
import { X, Download } from 'lucide-react';

export default function ZoomModal({ activeChart, isOpen, onClose, onDownload }) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !activeChart) return null;

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true" aria-label="Fullscreen Chart Preview">
      <div className="modal-content zoom-modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-top-bar">
          <span className="modal-title">{activeChart.title || activeChart.chart_type}</span>
          <div className="modal-actions-right">
            {onDownload && (
              <button
                type="button"
                className="action-btn"
                onClick={onDownload}
                title="Download PNG"
              >
                <Download size={13} />
                <span>Download</span>
              </button>
            )}
            <button
              className="modal-close"
              onClick={onClose}
              aria-label="Close Fullscreen View"
              type="button"
            >
              <X size={16} />
            </button>
          </div>
        </div>
        <div className="modal-image-wrap">
          <img src={activeChart.url} alt={activeChart.title || 'Fullscreen Chart'} className="modal-image" />
        </div>
      </div>
    </div>
  );
}
