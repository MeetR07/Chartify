import React, { useState } from 'react';
import { BarChart3, Download, Maximize2, TrendingUp, Sparkles, MousePointerClick, Image as ImageIcon } from 'lucide-react';
import PlotlyViewer from './PlotlyViewer';

export default function InteractiveCanvas({
  activeChart,
  loading,
  isRestyling,
  handleDownload,
  setZoomModal,
  onQuickPrompt
}) {
  const [viewMode, setViewMode] = useState('interactive');

  const hasInteractive = Boolean(activeChart?.interactive_spec && activeChart.interactive_spec.data);

  return (
    <div className="glass-panel canvas-card">
      {/* Canvas Toolbar */}
      <div className="canvas-toolbar">
        <div className="canvas-toolbar-left">
          <span className="panel-title">
            <BarChart3 className="panel-icon" size={18} aria-hidden="true" />
            <span>Interactive Canvas</span>
          </span>

          {activeChart && (
            <div className="canvas-badges-wrap">
              <span className="chart-badge main-type">
                {activeChart.chart_type}
              </span>
              {activeChart.args?.style && (
                <span className="chart-badge theme-tag">
                  Style: {activeChart.args.style}
                </span>
              )}
              {activeChart.args?.palette && (
                <span className="chart-badge pal-tag">
                  Palette: {activeChart.args.palette}
                </span>
              )}
              {isRestyling && (
                <span className="restyling-dots-badge">
                  <span>Applying</span>
                  <span className="bouncing-dots" aria-hidden="true">
                    <span className="dot dot-1"></span>
                    <span className="dot dot-2"></span>
                    <span className="dot dot-3"></span>
                  </span>
                </span>
              )}
            </div>
          )}
        </div>

        {activeChart && (
          <div className="canvas-actions">
            {/* View Mode Toggle: Interactive WebGL Hover vs High-Res Studio PNG */}
            {hasInteractive && (
              <div className="view-mode-toggle" role="group" aria-label="Chart display mode">
                <button
                  type="button"
                  className={`view-toggle-btn ${viewMode === 'interactive' ? 'active' : ''}`}
                  onClick={() => setViewMode('interactive')}
                  title="Interactive mode: Hover inspection, tooltips, zooming, and pan"
                >
                  <MousePointerClick size={12} />
                  <span>Interactive</span>
                </button>
                <button
                  type="button"
                  className={`view-toggle-btn ${viewMode === 'static' ? 'active' : ''}`}
                  onClick={() => setViewMode('static')}
                  title="Studio PNG mode: Crisp publication-grade static export"
                >
                  <ImageIcon size={12} />
                  <span>Studio PNG</span>
                </button>
              </div>
            )}

            <button
              type="button"
              onClick={handleDownload}
              className="action-btn download-btn"
              title="Download publication-quality chart as PNG"
            >
              <Download size={13} />
              <span>Download PNG</span>
            </button>
            <button
              type="button"
              onClick={() => setZoomModal(true)}
              className="action-btn zoom-btn"
              title="Expand chart fullscreen"
              aria-label="Fullscreen chart view"
            >
              <Maximize2 size={13} />
            </button>
          </div>
        )}
      </div>

      {/* Chart Viewport */}
      <div className="chart-viewport">
        {loading ? (
          <div className="loading-overlay" role="status" aria-live="polite">
            <div className="spinner" aria-hidden="true"></div>
            <p className="loading-title">
              Autonomous AI Engine is computing chart...
            </p>
            <small className="loading-subtitle">
              Synthesizing statistical parameters, aggregations & aesthetic rendering
            </small>
          </div>
        ) : activeChart ? (
          <div className="active-chart-container" style={{ width: '100%', height: '100%', minHeight: '400px' }}>
            {viewMode === 'interactive' && hasInteractive ? (
              <PlotlyViewer
                spec={activeChart.interactive_spec}
                fallbackUrl={activeChart.url}
              />
            ) : (
              <img
                src={activeChart.url}
                alt={activeChart.title || 'Generated AI Chart'}
                className={`chart-image ${isRestyling ? 'chart-blur' : ''}`}
              />
            )}

            {isRestyling && (
              <div className="restyling-overlay" role="status">
                <div className="restyling-dots-box">
                  <div className="bouncing-dots lg" aria-hidden="true">
                    <span className="dot dot-1"></span>
                    <span className="dot dot-2"></span>
                    <span className="dot dot-3"></span>
                  </div>
                  <span className="restyling-label">Applying aesthetic style & colors...</span>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-icon" aria-hidden="true">
              <TrendingUp size={26} />
            </div>
            <h3 className="empty-title">Ready for Visualization</h3>
            <p className="empty-desc">
              Type any query in the command bar above or pick one of the intelligent suggestions from the sidebar.
            </p>
            <div className="empty-quick-actions">
              <button
                type="button"
                className="empty-chip"
                onClick={() => onQuickPrompt && onQuickPrompt('Create a correlation heatmap')}
              >
                <Sparkles size={11} />
                <span>Correlation Heatmap</span>
              </button>
              <button
                type="button"
                className="empty-chip"
                onClick={() => onQuickPrompt && onQuickPrompt('Show distribution of values with violin plot')}
              >
                <Sparkles size={11} />
                <span>Distribution Violin Plot</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
