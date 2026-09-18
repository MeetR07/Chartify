import React, { useState } from 'react';
import { BarChart3, Download, Maximize2, TrendingUp, Sparkles, Shuffle } from 'lucide-react';
import ThreeCanvas from './ThreeCanvas';
import { generateClient2DChartSvg } from '../utils/svgChartGenerator';

export default function InteractiveCanvas({
  activeChart,
  dataset,
  selectedPalette,
  selectedStyle,
  loading,
  isRestyling,
  handleDownload,
  setZoomModal,
  onQuickPrompt,
  handleRandomStyle,
  handleSurpriseMe,
  viewMode = '3d',
  setViewMode
}) {
  const [internalViewMode, setInternalViewMode] = useState('3d');
  const currentViewMode = setViewMode ? viewMode : internalViewMode;
  const changeViewMode = setViewMode || setInternalViewMode;

  const onSurpriseClick = handleSurpriseMe || handleRandomStyle;

  return (
    <div className="glass-panel canvas-card">
      {/* Canvas Toolbar */}
      <div className="canvas-toolbar">
        <div className="canvas-toolbar-left">
          {onSurpriseClick && (
            <button
              type="button"
              className="action-btn surprise-btn canvas-surprise-btn"
              onClick={onSurpriseClick}
              disabled={loading || isRestyling}
              title="Surprise me with a new intelligent visualization and aesthetic theme from this dataset"
            >
              <Shuffle size={13} className={loading || isRestyling ? 'spin' : ''} />
              <span>🎲 SURPRISE ME</span>
            </button>
          )}



          {isRestyling && (
            <span className="restyle-pill" role="status" aria-live="polite">
              <span className="restyle-pill-label">Polishing chart</span>
              <span className="bouncing-dots" aria-hidden="true">
                <span className="dot dot-1"></span>
                <span className="dot dot-2"></span>
                <span className="dot dot-3"></span>
              </span>
            </span>
          )}
        </div>

        <div className="canvas-actions">
          {/* 3D / 2D View Switcher */}
          <div className="canvas-view-toggle" title="Switch between 3D WebGL and 2D Studio Image">
            <button
              type="button"
              className={`view-toggle-btn ${currentViewMode === '3d' ? 'active' : ''}`}
              onClick={() => changeViewMode('3d')}
            >
              🪐 3D VIEW
            </button>
            <button
              type="button"
              className={`view-toggle-btn ${currentViewMode === '2d' ? 'active' : ''}`}
              onClick={() => changeViewMode('2d')}
            >
              🖼️ 2D PNG
            </button>
          </div>

          {activeChart && (
            <>
              <button
                type="button"
                onClick={handleDownload}
                className="action-btn download-btn"
                title="Download publication-quality chart as PNG"
              >
                <Download size={13} />
                <span>EXPORT PNG ✦</span>
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
            </>
          )}
        </div>
      </div>

      {/* Chart Viewport */}
      <div className="chart-viewport">
        {loading ? (
          <div className="loading-overlay" role="status" aria-live="polite">
            <div className="spinner" aria-hidden="true"></div>
            <p className="loading-title">
              Cooking your visual masterpiece... ⚡
            </p>
            <small className="loading-subtitle">
              Crunching aggregations, aesthetic tokens & high-res vector rendering
            </small>
          </div>
        ) : activeChart ? (
          currentViewMode === '3d' ? (
            <ThreeCanvas
              activeChart={activeChart}
              dataset={dataset}
              selectedPalette={selectedPalette || activeChart?.args?.palette}
              selectedStyle={selectedStyle || activeChart?.args?.style}
            />
          ) : (
            <div className="active-chart-container">
              <img
                src={activeChart.url || generateClient2DChartSvg(activeChart, dataset)}
                alt={activeChart.title || 'Generated AI Chart'}
                className={`chart-image ${isRestyling ? 'chart-blur' : ''}`}
                onError={(e) => {
                  e.currentTarget.onerror = null;
                  e.currentTarget.src = generateClient2DChartSvg(activeChart, dataset);
                }}
              />

              {isRestyling && (
                <div className="restyling-overlay" role="status">
                  <div className="restyling-dots-box">
                    <div className="bouncing-dots lg" aria-hidden="true">
                      <span className="dot dot-1"></span>
                      <span className="dot dot-2"></span>
                      <span className="dot dot-3"></span>
                    </div>
                    <span className="restyling-label">Recoloring aesthetic style...</span>
                  </div>
                </div>
              )}
            </div>
          )
        ) : (
          <div className="empty-state">
            <div className="empty-icon" aria-hidden="true">
              <TrendingUp size={26} />
            </div>
            <h3 className="empty-title">Ready To Cook Visuals 🚀</h3>
            <p className="empty-desc">
              Drop any query in the command bar above or pick one of these trending visual recipes.
            </p>
            <div className="empty-quick-actions">
              <button
                type="button"
                className="empty-chip"
                onClick={() => onQuickPrompt && onQuickPrompt('Create a correlation heatmap')}
              >
                <Sparkles size={11} />
                <span>🔥 Correlation Heatmap</span>
              </button>
              <button
                type="button"
                className="empty-chip"
                onClick={() => onQuickPrompt && onQuickPrompt('Show distribution of values with violin plot')}
              >
                <Sparkles size={11} />
                <span>✨ Distribution Violin Plot</span>
              </button>
              <button
                type="button"
                className="empty-chip"
                onClick={() => onQuickPrompt && onQuickPrompt('Scatter plot with regression trendline')}
              >
                <Sparkles size={11} />
                <span>⚡ Trendline Scatter</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
