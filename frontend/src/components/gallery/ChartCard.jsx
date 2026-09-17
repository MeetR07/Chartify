import React, { useState, useRef } from 'react';
import Chart2D from './Chart2D';
import Chart3D from './Chart3D';
import ChartToolbar from './ChartToolbar';
import ChartTooltip from './ChartTooltip';

export default function ChartCard({
  chartKey,
  chartInfo,
  onFullscreen
}) {
  const [is3D, setIs3D] = useState(true);
  const [autoRotate, setAutoRotate] = useState(false); // No auto-rotation by default per requirements
  const [hoveredData, setHoveredData] = useState(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const resetRef = useRef(null);

  const handleHover = (data, pos) => {
    setHoveredData(data);
    if (pos) setTooltipPos(pos);
  };

  const handleReset = () => {
    if (resetRef.current) resetRef.current();
  };

  return (
    <div className="gallery-chart-card">
      {/* Card Header */}
      <div className="chart-card-header">
        <div className="chart-title-wrap">
          <h3 className="chart-card-title">{chartInfo.title}</h3>
          <p className="chart-card-desc">{chartInfo.desc}</p>
        </div>

        {/* [2D] [3D] Segmented Toggle */}
        <div className="chart-card-mode-toggle" role="group" aria-label="Toggle 2D / 3D View">
          <button
            type="button"
            className={`mode-toggle-btn ${!is3D ? 'active' : ''}`}
            onClick={() => setIs3D(false)}
            title="Switch to 2D Vector Chart"
          >
            2D
          </button>
          <button
            type="button"
            className={`mode-toggle-btn ${is3D ? 'active' : ''}`}
            onClick={() => setIs3D(true)}
            title="Switch to Genuine 3D WebGL Chart"
          >
            3D
          </button>
        </div>
      </div>

      {/* Live Chart Viewport */}
      <div className="chart-card-viewport">
        {is3D ? (
          <Chart3D
            chartType={chartKey}
            data={chartInfo.data}
            autoRotate={autoRotate}
            onResetRef={resetRef}
            onHover={handleHover}
          />
        ) : (
          <div className="chart-2d-container">
            <Chart2D
              chartType={chartKey}
              data={chartInfo.data}
              onHover={handleHover}
            />
          </div>
        )}

        {/* Floating Tooltip */}
        <ChartTooltip data={hoveredData} position={tooltipPos} />

        {/* Interaction Hint Footer */}
        <div className="chart-card-footer">
          <span className="interaction-hint">
            {is3D ? '🪐 Drag to orbit • Scroll to zoom • Hover data' : '📊 Vector 2D View • Hover data'}
          </span>

          <ChartToolbar
            is3D={is3D}
            autoRotate={autoRotate}
            onToggleRotate={() => setAutoRotate(!autoRotate)}
            onReset={handleReset}
            onFullscreen={() => onFullscreen?.({ chartKey, chartInfo, is3D })}
          />
        </div>
      </div>
    </div>
  );
}
