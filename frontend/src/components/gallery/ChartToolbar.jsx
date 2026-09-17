import React from 'react';
import { RotateCcw, Play, Pause, Maximize2 } from 'lucide-react';

export default function ChartToolbar({
  onReset,
  autoRotate,
  onToggleRotate,
  onFullscreen,
  is3D
}) {
  return (
    <div className="chart-card-toolbar">
      {is3D && (
        <>
          <button
            type="button"
            className={`gallery-tool-btn ${autoRotate ? 'active' : ''}`}
            onClick={onToggleRotate}
            title={autoRotate ? 'Pause 3D Orbit' : 'Play 3D Orbit'}
            aria-label={autoRotate ? 'Pause 3D Orbit' : 'Play 3D Orbit'}
          >
            {autoRotate ? <Pause size={12} /> : <Play size={12} />}
            <span>{autoRotate ? 'ORBIT' : 'PAUSED'}</span>
          </button>

          <button
            type="button"
            className="gallery-tool-btn"
            onClick={onReset}
            title="Reset Camera Framing"
            aria-label="Reset Camera Framing"
          >
            <RotateCcw size={12} />
            <span>RESET</span>
          </button>
        </>
      )}

      {onFullscreen && (
        <button
          type="button"
          className="gallery-tool-btn"
          onClick={onFullscreen}
          title="Expand View"
          aria-label="Expand View"
        >
          <Maximize2 size={12} />
        </button>
      )}
    </div>
  );
}
