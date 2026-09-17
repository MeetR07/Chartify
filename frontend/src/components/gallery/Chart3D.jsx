import React from 'react';
import Radar3D from './charts3d/Radar3D';
import Lollipop3D from './charts3d/Lollipop3D';
import Waterfall3D from './charts3d/Waterfall3D';
import Treemap3D from './charts3d/Treemap3D';
import Violin3D from './charts3d/Violin3D';
import Area3D from './charts3d/Area3D';
import Donut3D from './charts3d/Donut3D';
import Pie3D from './charts3d/Pie3D';

export default function Chart3D({ chartType, data, autoRotate, onResetRef, onHover }) {
  switch (chartType) {
    case 'radar':
      return <Radar3D data={data} autoRotate={autoRotate} onResetRef={onResetRef} onHover={onHover} />;
    case 'lollipop':
      return <Lollipop3D data={data} autoRotate={autoRotate} onResetRef={onResetRef} onHover={onHover} />;
    case 'waterfall':
      return <Waterfall3D data={data} autoRotate={autoRotate} onResetRef={onResetRef} onHover={onHover} />;
    case 'treemap':
      return <Treemap3D data={data} autoRotate={autoRotate} onResetRef={onResetRef} onHover={onHover} />;
    case 'violin':
      return <Violin3D data={data} autoRotate={autoRotate} onResetRef={onResetRef} onHover={onHover} />;
    case 'area':
      return <Area3D data={data} autoRotate={autoRotate} onResetRef={onResetRef} onHover={onHover} />;
    case 'donut':
      return <Donut3D data={data} autoRotate={autoRotate} onResetRef={onResetRef} onHover={onHover} />;
    case 'pie':
      return <Pie3D data={data} autoRotate={autoRotate} onResetRef={onResetRef} onHover={onHover} />;
    default:
      return <div className="chart-3d-fallback">3D Renderer Initializing...</div>;
  }
}
