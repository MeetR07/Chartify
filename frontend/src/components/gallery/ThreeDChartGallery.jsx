import React, { useMemo, useState } from 'react';
import { Sparkles, Box, X } from 'lucide-react';
import ChartCard from './ChartCard';
import Chart3D from './Chart3D';
import Chart2D from './Chart2D';
import { getGalleryData } from './dataAdapter';

export default function ThreeDChartGallery({ dataset }) {
  const [fullscreenChart, setFullscreenChart] = useState(null);

  // Derive gallery data from dataset
  const galleryData = useMemo(() => {
    return getGalleryData(dataset);
  }, [dataset]);

  const chartKeys = [
    'radar',
    'lollipop',
    'waterfall',
    'treemap',
    'violin',
    'area',
    'donut',
    'pie'
  ];

  return (
    <section className="threed-gallery-section" id="3d-gallery">
      {/* Section Header */}
      <div className="threed-gallery-header">
        <div className="threed-header-left">
          <span className="threed-badge">
            <Box size={14} />
            <span>GENUINE THREE.JS STUDIO</span>
          </span>
          <h2 className="threed-title">3D CHART VISUALIZATION STUDIO 🪐</h2>
          <p className="threed-subtitle">
            GPU-accelerated spatial geometry engine with real perspective cameras, lighting, and dual 2D/3D renderers.
          </p>
        </div>

        <div className="threed-header-stats">
          <span className="threed-stat-pill">8 3D FORMS</span>
          <span className="threed-stat-pill">ORBIT CONTROLS</span>
          <span className="threed-stat-pill">ZERO FAKE 3D</span>
        </div>
      </div>

      {/* 3-Column Responsive Grid */}
      <div className="threed-cards-grid">
        {chartKeys.map((key) => {
          const chartInfo = galleryData[key];
          if (!chartInfo) return null;
          return (
            <ChartCard
              key={key}
              chartKey={key}
              chartInfo={chartInfo}
              onFullscreen={setFullscreenChart}
            />
          );
        })}
      </div>

      {/* Fullscreen Expand Modal */}
      {fullscreenChart && (
        <div className="threed-modal-backdrop" onClick={() => setFullscreenChart(null)}>
          <div className="threed-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="threed-modal-header">
              <h3>{fullscreenChart.chartInfo.title}</h3>
              <button
                type="button"
                className="threed-modal-close"
                onClick={() => setFullscreenChart(null)}
                aria-label="Close Fullscreen"
              >
                <X size={18} />
              </button>
            </div>
            <div className="threed-modal-viewport">
              {fullscreenChart.is3D ? (
                <Chart3D
                  chartType={fullscreenChart.chartKey}
                  data={fullscreenChart.chartInfo.data}
                  autoRotate={true}
                />
              ) : (
                <div className="chart-2d-container lg">
                  <Chart2D
                    chartType={fullscreenChart.chartKey}
                    data={fullscreenChart.chartInfo.data}
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
