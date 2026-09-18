import React, { useEffect, useState } from 'react';
import { X, Download, Columns, Box, Image } from 'lucide-react';
import ThreeCanvas from './ThreeCanvas';
import { generateClient2DChartSvg } from '../utils/svgChartGenerator';

export default function ZoomModal({
  activeChart,
  dataset,
  selectedPalette,
  selectedStyle,
  viewMode = 'both',
  isOpen,
  onClose,
  onDownload
}) {
  const [modalViewMode, setModalViewMode] = useState('both');

  // When modal opens, default to 'both' so both 3D and 2D are shown together!
  useEffect(() => {
    if (isOpen) {
      setModalViewMode('both');
    }
  }, [isOpen]);

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

  const paletteKey = activeChart?.args?.palette || selectedPalette;
  const styleKey = activeChart?.args?.style || selectedStyle;

  return (
    <div
      className="modal-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Fullscreen Chart Preview"
    >
      <div className="modal-content zoom-modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-top-bar">
          <div className="modal-title-group">
            <span className="modal-title">{activeChart.title || activeChart.chart_type}</span>
            <span className="modal-badge-type">{(activeChart.chart_type || 'chart').toUpperCase()}</span>
          </div>

          {/* View Mode Switcher: Dual Both, 3D Only, 2D Only */}
          <div className="view-mode-tabs zoom-view-tabs" role="tablist">
            <button
              type="button"
              className={`view-toggle-btn ${modalViewMode === 'both' ? 'active' : ''}`}
              onClick={() => setModalViewMode('both')}
              role="tab"
              aria-selected={modalViewMode === 'both'}
              title="Show 3D WebGL and 2D Image side-by-side"
            >
              <Columns size={12} style={{ display: 'inline', marginRight: 4, verticalAlign: '-1px' }} />
              <span>⚡ BOTH (DUAL)</span>
            </button>
            <button
              type="button"
              className={`view-toggle-btn ${modalViewMode === '3d' ? 'active' : ''}`}
              onClick={() => setModalViewMode('3d')}
              role="tab"
              aria-selected={modalViewMode === '3d'}
              title="Fullscreen 3D Interactive WebGL"
            >
              <Box size={12} style={{ display: 'inline', marginRight: 4, verticalAlign: '-1px' }} />
              <span>🪐 3D VIEW</span>
            </button>
            <button
              type="button"
              className={`view-toggle-btn ${modalViewMode === '2d' ? 'active' : ''}`}
              onClick={() => setModalViewMode('2d')}
              role="tab"
              aria-selected={modalViewMode === '2d'}
              title="Fullscreen 2D High-Res PNG"
            >
              <Image size={12} style={{ display: 'inline', marginRight: 4, verticalAlign: '-1px' }} />
              <span>🖼️ 2D PNG</span>
            </button>
          </div>

          <div className="modal-actions-right">
            {onDownload && (
              <button
                type="button"
                className="action-btn download-btn"
                onClick={onDownload}
                title="Download Publication PNG"
              >
                <Download size={13} />
                <span>EXPORT PNG</span>
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

        {/* Modal Body Content */}
        <div className="zoom-modal-body">
          {modalViewMode === 'both' ? (
            <div className="zoom-modal-dual-grid">
              {/* Left Pane: 3D WebGL */}
              <div className="zoom-modal-pane">
                <div className="zoom-modal-pane-header">
                  <div className="pane-header-title">
                    <Box size={13} />
                    <span>🪐 3D WEBGL INTERACTIVE</span>
                  </div>
                  <span className="zoom-modal-pane-tag">360° ORBIT & ZOOM</span>
                </div>
                <div className="zoom-modal-pane-content">
                  <ThreeCanvas
                    activeChart={activeChart}
                    dataset={dataset}
                    selectedPalette={paletteKey}
                    selectedStyle={styleKey}
                  />
                </div>
              </div>

              {/* Right Pane: 2D PNG */}
              <div className="zoom-modal-pane">
                <div className="zoom-modal-pane-header">
                  <div className="pane-header-title">
                    <Image size={13} />
                    <span>🖼️ 2D HIGH-RES PNG</span>
                  </div>
                  <span className="zoom-modal-pane-tag">PUBLICATION READY</span>
                </div>
                <div className="zoom-modal-pane-content modal-image-wrap">
                  <img
                    src={activeChart.url || generateClient2DChartSvg(activeChart, dataset)}
                    alt={activeChart.title || 'Fullscreen Chart'}
                    className="modal-image"
                    onError={(e) => {
                      e.currentTarget.onerror = null;
                      e.currentTarget.src = generateClient2DChartSvg(activeChart, dataset);
                    }}
                  />
                </div>
              </div>
            </div>
          ) : modalViewMode === '3d' ? (
            <div className="zoom-modal-single-pane">
              <ThreeCanvas
                activeChart={activeChart}
                dataset={dataset}
                selectedPalette={paletteKey}
                selectedStyle={styleKey}
              />
            </div>
          ) : (
            <div className="zoom-modal-single-pane modal-image-wrap">
              <img
                src={activeChart.url || generateClient2DChartSvg(activeChart, dataset)}
                alt={activeChart.title || 'Fullscreen Chart'}
                className="modal-image"
                onError={(e) => {
                  e.currentTarget.onerror = null;
                  e.currentTarget.src = generateClient2DChartSvg(activeChart, dataset);
                }}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
