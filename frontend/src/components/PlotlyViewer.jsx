import React, { useEffect, useRef, useState } from 'react';
import { Loader2 } from 'lucide-react';

let plotlyLoadingPromise = null;

function loadPlotlyCDN() {
  if (window.Plotly) {
    return Promise.resolve(window.Plotly);
  }
  if (!plotlyLoadingPromise) {
    plotlyLoadingPromise = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'https://cdn.plot.ly/plotly-2.35.2.min.js';
      script.async = true;
      script.onload = () => resolve(window.Plotly);
      script.onerror = () => {
        plotlyLoadingPromise = null;
        reject(new Error('Failed to load Plotly engine from CDN'));
      };
      document.head.appendChild(script);
    });
  }
  return plotlyLoadingPromise;
}

export default function PlotlyViewer({ spec, theme = 'dark', fallbackUrl }) {
  const containerRef = useRef(null);
  const [loadingPlotly, setLoadingPlotly] = useState(!window.Plotly);
  const [renderError, setRenderError] = useState(false);

  useEffect(() => {
    let isMounted = true;

    if (!spec || !spec.data) {
      return;
    }

    loadPlotlyCDN()
      .then((Plotly) => {
        if (!isMounted || !containerRef.current) return;
        setLoadingPlotly(false);

        const isDark = theme === 'dark' || document.documentElement.getAttribute('data-theme') === 'dark';
        const bg = 'rgba(0,0,0,0)';
        const textCol = isDark ? '#f8fafc' : '#0f172a';
        const gridCol = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)';

        // Deep copy layout to customize for current container
        const customLayout = {
          ...(spec.layout || {}),
          paper_bgcolor: bg,
          plot_bgcolor: bg,
          autosize: true,
          font: {
            family: 'Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif',
            color: textCol,
            size: 11
          },
          margin: { l: 45, r: 25, t: 45, b: 40 },
          legend: {
            orientation: 'h',
            yanchor: 'bottom',
            y: 1.02,
            xanchor: 'right',
            x: 1,
            font: { size: 10, color: textCol }
          }
        };

        if (customLayout.xaxis) {
          customLayout.xaxis.gridcolor = gridCol;
          customLayout.xaxis.color = textCol;
        }
        if (customLayout.yaxis) {
          customLayout.yaxis.gridcolor = gridCol;
          customLayout.yaxis.color = textCol;
        }

        const config = {
          responsive: true,
          displayModeBar: true,
          displaylogo: false,
          modeBarButtonsToRemove: ['lasso2d', 'select2d']
        };

        Plotly.react(containerRef.current, spec.data, customLayout, config)
          .catch((err) => {
            console.error('Plotly render error:', err);
            if (isMounted) setRenderError(true);
          });
      })
      .catch((err) => {
        console.error('Failed to load Plotly:', err);
        if (isMounted) {
          setLoadingPlotly(false);
          setRenderError(true);
        }
      });

    const handleResize = () => {
      if (window.Plotly && containerRef.current) {
        window.Plotly.Plots.resize(containerRef.current);
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      isMounted = false;
      window.removeEventListener('resize', handleResize);
      if (window.Plotly && containerRef.current) {
        try {
          window.Plotly.purge(containerRef.current);
        } catch (e) {
          // ignore purge errors during teardown
        }
      }
    };
  }, [spec, theme]);

  if (renderError && fallbackUrl) {
    return (
      <img
        src={fallbackUrl}
        alt="Chart visualization"
        className="chart-image"
      />
    );
  }

  return (
    <div className="plotly-viewer-wrapper" style={{ width: '100%', height: '100%', minHeight: '380px', position: 'relative' }}>
      {loadingPlotly && (
        <div className="plotly-loader" style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '8px',
          background: 'rgba(0,0,0,0.2)',
          backdropFilter: 'blur(4px)',
          borderRadius: '12px',
          zIndex: 10
        }}>
          <Loader2 className="animate-spin" size={24} style={{ animation: 'spin 1s linear infinite' }} />
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)' }}>
            Loading Interactive WebGL Engine...
          </span>
        </div>
      )}
      <div
        ref={containerRef}
        style={{ width: '100%', height: '100%', minHeight: '380px' }}
      />
    </div>
  );
}
