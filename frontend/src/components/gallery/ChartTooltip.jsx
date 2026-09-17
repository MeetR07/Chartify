import React from 'react';

export default function ChartTooltip({ data, position }) {
  if (!data) return null;

  return (
    <div
      className="gallery-chart-tooltip"
      style={{
        left: `${position.x + 12}px`,
        top: `${position.y - 28}px`
      }}
      role="tooltip"
    >
      <div className="tooltip-header">
        <span className="tooltip-dot" style={{ backgroundColor: data.color || '#08ab9c' }} />
        <span className="tooltip-title">{data.name || data.axis || data.group}</span>
      </div>
      <div className="tooltip-body">
        {data.category && <span className="tooltip-cat">{data.category}</span>}
        <span className="tooltip-val">
          {data.value !== undefined ? data.value.toLocaleString() : (data.delta !== undefined ? (data.delta > 0 ? `+${data.delta}` : data.delta) : '')}
        </span>
        {data.percent !== undefined && (
          <span className="tooltip-percent">({data.percent}%)</span>
        )}
      </div>
    </div>
  );
}
