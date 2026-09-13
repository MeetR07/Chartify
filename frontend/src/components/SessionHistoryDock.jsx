import React from 'react';
import { Layers, ChevronLeft, ChevronRight } from 'lucide-react';

export default function SessionHistoryDock({
  chartHistory,
  activeChart,
  setActiveChart,
  scrollHistory,
  historyScrollRef,
  handleHistoryWheel,
  handleHistoryMouseDown,
  handleHistoryMouseMove,
  handleHistoryMouseUp,
  isDraggingHistory
}) {
  if (!chartHistory || chartHistory.length === 0) return null;

  return (
    <div className="glass-panel history-dock">
      <div className="history-dock-header">
        <span className="panel-title history-title">
          <Layers className="panel-icon" size={14} aria-hidden="true" />
          <span>Session History ({chartHistory.length})</span>
        </span>
        <div className="history-nav-actions">
          <button
            onClick={() => scrollHistory('left')}
            className="action-btn icon-only"
            title="Scroll Left"
            aria-label="Scroll History Left"
            type="button"
          >
            <ChevronLeft size={13} />
          </button>
          <button
            onClick={() => scrollHistory('right')}
            className="action-btn icon-only"
            title="Scroll Right"
            aria-label="Scroll History Right"
            type="button"
          >
            <ChevronRight size={13} />
          </button>
        </div>
      </div>

      <div
        ref={historyScrollRef}
        className="history-scroll-track"
        onWheel={handleHistoryWheel}
        onMouseDown={handleHistoryMouseDown}
        onMouseMove={handleHistoryMouseMove}
        onMouseUp={handleHistoryMouseUp}
        onMouseLeave={handleHistoryMouseUp}
        style={{ cursor: isDraggingHistory ? 'grabbing' : 'grab' }}
      >
        {chartHistory.map((item) => {
          const isActive = activeChart?.id === item.id;
          return (
            <div
              key={item.id}
              onClick={() => setActiveChart(item)}
              className={`history-card-thumb ${isActive ? 'active' : ''}`}
              title={`${item.chart_type}: ${item.title || item.query}`}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') setActiveChart(item);
              }}
            >
              <img
                src={item.url}
                alt={item.chart_type}
                className="history-thumb-img"
              />
              <div className="history-thumb-label">
                {item.chart_type}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
