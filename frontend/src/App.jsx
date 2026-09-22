import React, { useState, useEffect, useRef, useMemo } from 'react';
import Navbar from './components/Navbar';
import DatasetInspector from './components/DatasetInspector';
import PromptHeroBar from './components/PromptHeroBar';
import InteractiveCanvas from './components/InteractiveCanvas';
import SessionHistoryDock from './components/SessionHistoryDock';
import DatasetExplorer from './components/DatasetExplorer';
import ZoomModal from './components/ZoomModal';
import DatasetModal from './components/DatasetModal';
import Toast from './components/Toast';
import Footer from './components/Footer';
import { THEME_STYLES, PALETTES } from './constants/themeOptions';
import { generateAccurateChartQuery, getDynamicQuickChips } from './utils/dynamicPrompts';
import { parseCSVClientSide } from './utils/csvParser';

const API_BASE = (
  import.meta.env.VITE_API_BASE_URL ||
  (typeof window !== 'undefined' && !window.location.hostname.includes('localhost') && !window.location.hostname.includes('127.0.0.1')
    ? 'https://chartify-g0oj.onrender.com'
    : '')
).replace(/\/$/, '');

const DEFAULT_DATASET = {
  columns: ["Month", "Sales", "Profit", "Region"],
  numeric_columns: ["Sales", "Profit"],
  categorical_columns: ["Month", "Region"],
  row_count: 5,
  column_count: 4,
  head_rows: [
    { _row_idx: 1, Month: "Jan", Sales: 15000, Profit: 3000, Region: "North" },
    { _row_idx: 2, Month: "Feb", Sales: 22000, Profit: 4500, Region: "South" },
    { _row_idx: 3, Month: "Mar", Sales: 18000, Profit: -1200, Region: "North" },
    { _row_idx: 4, Month: "Apr", Sales: 27000, Profit: 6000, Region: "West" },
    { _row_idx: 5, Month: "May", Sales: 31000, Profit: 7500, Region: "South" }
  ],
  tail_rows: [],
  has_ellipsis: false,
  hidden_count: 0,
  sample_data: [
    { _row_idx: 1, Month: "Jan", Sales: 15000, Profit: 3000, Region: "North" },
    { _row_idx: 2, Month: "Feb", Sales: 22000, Profit: 4500, Region: "South" },
    { _row_idx: 3, Month: "Mar", Sales: 18000, Profit: -1200, Region: "North" },
    { _row_idx: 4, Month: "Apr", Sales: 27000, Profit: 6000, Region: "West" },
    { _row_idx: 5, Month: "May", Sales: 31000, Profit: 7500, Region: "South" }
  ],
  describe: {
    Sales: { count: 5, mean: 22600, min: 15000, max: 31000 },
    Profit: { count: 5, mean: 3960, min: -1200, max: 7500 }
  }
};

export default function App() {
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem('chartify_theme');
    return saved === 'dark' ? 'light' : (saved || 'light');
  });
  const [dataset, setDataset] = useState(() => {
    try {
      const saved = localStorage.getItem('chartify_dataset');
      return saved ? JSON.parse(saved) : DEFAULT_DATASET;
    } catch {
      return DEFAULT_DATASET;
    }
  });
  const [query, setQuery] = useState('');
  const [selectedChartType, setSelectedChartType] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [activeChart, setActiveChart] = useState(() => {
    try {
      const saved = localStorage.getItem('chartify_active_chart');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [sessionTokens, setSessionTokens] = useState(() => {
    try {
      const saved = localStorage.getItem('chartify_tokens');
      return saved ? parseInt(saved, 10) || 0 : 0;
    } catch {
      return 0;
    }
  });
  const [chartHistory, setChartHistory] = useState(() => {
    try {
      const saved = localStorage.getItem('chartify_chart_history');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [zoomModal, setZoomModal] = useState(false);
  const [viewMode, setViewMode] = useState(() => {
    try {
      return localStorage.getItem('chartify_view_mode') || '2d';
    } catch {
      return '2d';
    }
  });
  const [datasetModal, setDatasetModal] = useState(false);
  const [tableSearch, setTableSearch] = useState('');
  const [toast, setToast] = useState({ message: '', type: 'error' });
  const [selectedStyle, setSelectedStyle] = useState('whitegrid');
  const [selectedPalette, setSelectedPalette] = useState('butter_green');
  const [isStyleOpen, setIsStyleOpen] = useState(false);
  const [isPaletteOpen, setIsPaletteOpen] = useState(false);
  const [isRestyling, setIsRestyling] = useState(false);
  const [isDraggingHistory, setIsDraggingHistory] = useState(false);
  const [dragStartX, setDragStartX] = useState(0);
  const [dragScrollLeft, setDragScrollLeft] = useState(0);

  const inputRef = useRef(null);
  const historyScrollRef = useRef(null);
  const styleBoxRef = useRef(null);
  const paletteBoxRef = useRef(null);
  const restyleTimerRef = useRef(null);

  // Sync theme with document root
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('chartify_theme', theme);
  }, [theme]);

  // Auto-save activeChart across refreshes
  useEffect(() => {
    try {
      if (activeChart) {
        localStorage.setItem('chartify_active_chart', JSON.stringify(activeChart));
      } else {
        localStorage.removeItem('chartify_active_chart');
      }
    } catch (e) {
      console.warn('LocalStorage save failed for activeChart:', e);
    }
  }, [activeChart]);

  // Auto-save chartHistory across refreshes (keeps latest 12)
  useEffect(() => {
    try {
      if (chartHistory && chartHistory.length > 0) {
        const trimmed = chartHistory.slice(0, 12);
        localStorage.setItem('chartify_chart_history', JSON.stringify(trimmed));
      } else {
        localStorage.removeItem('chartify_chart_history');
      }
    } catch (e) {
      console.warn('LocalStorage save failed for chartHistory:', e);
    }
  }, [chartHistory]);

  // Auto-save dataset across refreshes
  useEffect(() => {
    try {
      if (dataset) {
        localStorage.setItem('chartify_dataset', JSON.stringify(dataset));
      }
    } catch (e) {
      console.warn('LocalStorage save failed for dataset:', e);
    }
  }, [dataset]);

  // Auto-save viewMode
  useEffect(() => {
    try {
      localStorage.setItem('chartify_view_mode', viewMode);
    } catch (_) {}
  }, [viewMode]);

  // Auto-save sessionTokens
  useEffect(() => {
    try {
      localStorage.setItem('chartify_tokens', String(sessionTokens));
    } catch (_) {}
  }, [sessionTokens]);

  // Click outside to close dropdowns only when clicked outside both
  useEffect(() => {
    const handleOutsideClick = (e) => {
      if (
        styleBoxRef.current && !styleBoxRef.current.contains(e.target) &&
        paletteBoxRef.current && !paletteBoxRef.current.contains(e.target)
      ) {
        setIsStyleOpen(false);
        setIsPaletteOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  // Fetch current dataset metadata only if not already restored from localStorage
  const fetchDataset = async () => {
    try {
      const saved = localStorage.getItem('chartify_dataset');
      if (saved) {
        return;
      }
      const res = await fetch(`${API_BASE}/api/dataset`);
      if (res.ok) {
        const data = await res.json();
        setDataset(data);
      }
    } catch (err) {
      console.error('Failed to fetch dataset:', err);
    }
  };

  useEffect(() => {
    fetchDataset();
  }, []);

  // Handle CSV Upload (Supports both Python backend and offline client-side parsing)
  const handleFileUpload = async (e) => {
    const inputEl = e.target;
    const file = inputEl?.files?.[0];
    if (!file) return;

    setUploading(true);
    let backendSuccess = false;

    // 1. Try sending to backend if available
    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch(`${API_BASE}/api/upload-csv`, {
        method: 'POST',
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        if (data && Array.isArray(data.columns)) {
          setDataset(data);
          backendSuccess = true;
          setToast({
            message: `Dataset "${file.name}" loaded! (${data.row_count || 'new'} rows, ${data.column_count || data.columns?.length || ''} columns)`,
            type: 'success'
          });
        }
      }
    } catch (_) {
      // Backend not reached or offline, seamlessly fallback to browser parsing
    }

    // 2. Client-side browser fallback (Works directly on phone/Vercel)
    if (!backendSuccess) {
      try {
        const text = await file.text();
        const parsed = parseCSVClientSide(text, file.name);
        if (parsed && parsed.columns.length > 0) {
          setDataset(parsed);
          setToast({
            message: `Dataset "${file.name}" loaded! (${parsed.row_count} rows, ${parsed.column_count} columns)`,
            type: 'success'
          });
        } else {
          throw new Error('Empty CSV');
        }
      } catch (err) {
        console.error('Client CSV upload error:', err);
        setToast({ message: 'Failed to parse CSV dataset. Please check file format.', type: 'error' });
      }
    }

    setUploading(false);
    try {
      if (inputEl) inputEl.value = '';
    } catch (_) {}
  };

  // Handle Chart Generation (Supports full LLM cascade & instant client 3D WebGL fallback)
  const handleGenerate = async (queryText, styleOverride, paletteOverride) => {
    let q = (queryText || query).trim();
    if (!q && selectedChartType) {
      q = `Generate a ${selectedChartType} chart`;
    }
    if (!q || loading) return;

    if (selectedChartType && !q.toLowerCase().includes(selectedChartType)) {
      q = `${selectedChartType} chart: ${q}`;
    }

    const effectiveStyle = styleOverride || selectedStyle;
    const effectivePalette = paletteOverride || selectedPalette;

    setLoading(true);

    // 1. Try connecting to Python LLM backend
    try {
      const res = await fetch(`${API_BASE}/api/generate-chart`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: q,
          style: effectiveStyle,
          palette: effectivePalette
        }),
      });

      if (res.ok) {
        const data = await res.json();
        if (data.clarification_needed) {
          setToast({
            message: `🤔 ${data.message}`,
            type: 'error'
          });
        } else if (data.no_data) {
          setToast({
            message: `ℹ️ ${data.message}`,
            type: 'error'
          });
        } else if (data.success && data.tool_called) {
          const newChart = {
            id: Date.now(),
            url: data.chart_url,
            chart_type: data.chart_type,
            title: data.tool_args?.title || data.chart_type,
            tokens: data.tokens,
            query: q,
            result: data.result,
            chart_data: data.chart_data,
            data_signature: data.data_signature,
            fallback_note: data.fallback_note,
            args: {
              ...data.tool_args,
              style: effectiveStyle,
              palette: effectivePalette
            }
          };
          setActiveChart(newChart);
          setViewMode('2d');
          setChartHistory((prev) => [newChart, ...prev]);
          setSessionTokens((prev) => prev + (data.tokens?.total || 0));

          if (data.fallback_note) {
            setToast({
              message: `💡 ${data.fallback_note}`,
              type: 'success'
            });
          }
        } else {
          setToast({
            message: data.message || data.detail || 'Chart generation tool failed to produce a chart',
            type: 'error'
          });
        }
      } else {
        setToast({
          message: 'Server error while generating chart',
          type: 'error'
        });
      }
    } catch (err) {
      console.error('Chart generation error:', err);
      setToast({
        message: 'Backend chart service is offline or unreachable.',
        type: 'error'
      });
    }

    setLoading(false);
    setQuery('');
  };

  // Dynamic Style & Palette updater with instant visual feedback
  const applyStyleAndPalette = async (style, palette) => {
    setSelectedStyle(style);
    setSelectedPalette(palette);

    if (activeChart && activeChart.args) {
      setIsRestyling(true);

      try {
        const res = await fetch(`${API_BASE}/api/apply-style`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ...activeChart.args,
            style: style,
            palette: palette
          })
        });
        const data = await res.json();
        if (res.ok && data.success) {
          const preservedChartData = (data.chart_data && Object.keys(data.chart_data).length > 0)
            ? data.chart_data
            : activeChart.chart_data;
          const updatedChart = {
            ...activeChart,
            url: data.chart_url,
            chart_data: preservedChartData,
            args: {
              ...activeChart.args,
              ...data.tool_args,
              style: style,
              palette: palette
            }
          };
          setActiveChart(updatedChart);
          setChartHistory((prev) =>
            prev.map((c) => (c.id === activeChart.id ? updatedChart : c))
          );
          setToast({
            message: `🎨 Applied ${palette.replace(/_/g, ' ')} palette with ${style} style!`,
            type: 'success'
          });
        } else {
          setToast({
            message: data.detail || 'Failed to update chart styling',
            type: 'error'
          });
        }
      } catch (err) {
        console.error('Failed to update style and palette:', err);
        setToast({ message: 'Error updating chart style', type: 'error' });
      } finally {
        setIsRestyling(false);
      }
    } else {
      setToast({
        message: `🎨 Selected ${palette.replace(/_/g, ' ')} palette! (Generate a chart to view)`,
        type: 'info'
      });
    }
  };

  const handleStyleChange = (newStyle) => {
    applyStyleAndPalette(newStyle, selectedPalette);
  };

  const handlePaletteChange = (newPalette) => {
    applyStyleAndPalette(selectedStyle, newPalette);
  };

  // Surprise Me / Roll Vibe: Strictly randomizes the color palette and theme of the current chart (NEVER changes chart type or query)
  const handleRandomStyle = () => {
    if (isRestyling) return;

    const otherStyles = THEME_STYLES.filter((s) => s.id !== selectedStyle);
    const randomStyle = otherStyles.length
      ? otherStyles[Math.floor(Math.random() * otherStyles.length)].id
      : THEME_STYLES[0].id;

    const otherPalettes = PALETTES.filter((p) => p.id !== selectedPalette && p.id !== 'custom');
    const randomPalette = otherPalettes.length
      ? otherPalettes[Math.floor(Math.random() * otherPalettes.length)].id
      : PALETTES[0].id;

    applyStyleAndPalette(randomStyle, randomPalette);
  };

  // Surprise Me on canvas toolbar strictly randomizes the color palette & theme of the chart
  const handleSurpriseMe = handleRandomStyle;

  // Download Chart PNG (Dual Bulletproof Export: Direct Python save + Windows Explorer open + Browser download)
  const handleDownload = (e) => {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    if (!activeChart?.url) {
      setToast({ message: 'No chart available to export', type: 'error' });
      return;
    }

    const cleanTitle = (activeChart.title || activeChart.chart_type || 'chart')
      .replace(/[^a-zA-Z0-9_-]/g, '_')
      .toLowerCase();
    const filename = cleanTitle.endsWith('.png') ? cleanTitle : `${cleanTitle}.png`;
    const url = activeChart.url;

    // 1. Direct Python Backend Save -> writes to C:\Users\admin\Downloads & highlights in Windows Explorer
    fetch('/api/export-to-downloads', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_data: url, filename: filename })
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          setToast({ message: `Saved to Downloads: ${filename} 📂✨`, type: 'success' });
        }
      })
      .catch((err) => console.warn('Background Python save:', err));

    // 2. Direct browser download trigger via native anchor
    try {
      const link = document.createElement('a');
      link.download = filename;
      link.href = url.startsWith('data:') ? url : `/api/charts/download/${encodeURIComponent(filename)}`;
      document.body.appendChild(link);
      link.click();
      setTimeout(() => {
        try {
          document.body.removeChild(link);
        } catch (_) {}
      }, 500);
    } catch (err) {
      console.warn('Browser anchor download error:', err);
    }

    setToast({ message: `Exporting ${filename}... 📥`, type: 'success' });
  };

  // History Carousel Handlers
  const scrollHistory = (direction) => {
    if (historyScrollRef.current) {
      const offset = direction === 'left' ? -280 : 280;
      historyScrollRef.current.scrollBy({ left: offset, behavior: 'smooth' });
    }
  };

  const handleHistoryMouseDown = (e) => {
    if (!historyScrollRef.current) return;
    setIsDraggingHistory(true);
    setDragStartX(e.pageX - historyScrollRef.current.offsetLeft);
    setDragScrollLeft(historyScrollRef.current.scrollLeft);
  };

  const handleHistoryMouseMove = (e) => {
    if (!isDraggingHistory || !historyScrollRef.current) return;
    e.preventDefault();
    const x = e.pageX - historyScrollRef.current.offsetLeft;
    const walk = (x - dragStartX) * 1.5;
    historyScrollRef.current.scrollLeft = dragScrollLeft - walk;
  };

  const handleHistoryMouseUp = () => {
    setIsDraggingHistory(false);
  };

  const handleHistoryWheel = (e) => {
    if (historyScrollRef.current && Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
      e.preventDefault();
      historyScrollRef.current.scrollLeft += e.deltaY;
    }
  };

  // Quick Chip click & Column tag insertion
  const handleChipClick = (chipQuery) => {
    setQuery(chipQuery);
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  const handleSelectChartType = (chartType) => {
    setSelectedChartType(chartType);
    if (chartType) {
      const prefix = generateAccurateChartQuery(chartType);
      setQuery(prefix);
    } else {
      setQuery('');
    }
    if (inputRef.current) {
      inputRef.current.focus();
      setTimeout(() => {
        if (inputRef.current) {
          const len = inputRef.current.value.length;
          inputRef.current.setSelectionRange(len, len);
        }
      }, 10);
    }
  };

  const handleColumnClick = (colName) => {
    setQuery((prev) => {
      const trimmed = prev.trim();
      return trimmed ? `${trimmed} by ${colName}` : `Plot of ${colName}`;
    });
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  return (
    <div className="app-wrapper">
      {/* Toast Notification Banner */}
      <Toast
        message={toast.message}
        type={toast.type}
        onClose={() => setToast({ message: '', type: 'error' })}
      />

      {/* Top Navbar */}
      <Navbar
        theme={theme}
        setTheme={setTheme}
        sessionTokens={sessionTokens}
      />

      {/* Main Studio Dashboard */}
      <main className="dashboard-container">
        {/* Left Sidebar: Dataset Inspector */}
        <aside className="glass-panel sidebar-panel">
          <DatasetInspector
            dataset={dataset}
            fetchDataset={fetchDataset}
            setDatasetModal={setDatasetModal}
            handleFileUpload={handleFileUpload}
            uploading={uploading}
          />
        </aside>

        {/* Right Studio Area: Command Bar, Aesthetics Studio, Canvas, History */}
        <section className="studio-column">
          {/* Aurora Prompt Hero Command Bar */}
          <PromptHeroBar
            query={query}
            setQuery={setQuery}
            selectedChartType={selectedChartType}
            onSelectChartType={handleSelectChartType}
            loading={loading}
            handleGenerate={handleGenerate}
            inputRef={inputRef}
            handleFileUpload={handleFileUpload}
            uploading={uploading}
          />

          {/* Interactive Chart Canvas with Surprise Me on far left */}
          <InteractiveCanvas
            activeChart={activeChart}
            dataset={dataset}
            selectedPalette={selectedPalette}
            selectedStyle={selectedStyle}
            loading={loading}
            isRestyling={isRestyling}
            handleDownload={handleDownload}
            setZoomModal={setZoomModal}
            onQuickPrompt={handleChipClick}
            handleRandomStyle={handleRandomStyle}
            handleSurpriseMe={handleSurpriseMe}
            viewMode={viewMode}
            setViewMode={setViewMode}
          />

          {/* Session History Carousel Dock */}
          <SessionHistoryDock
            chartHistory={chartHistory}
            activeChart={activeChart}
            setActiveChart={setActiveChart}
            scrollHistory={scrollHistory}
            historyScrollRef={historyScrollRef}
            handleHistoryWheel={handleHistoryWheel}
            handleHistoryMouseDown={handleHistoryMouseDown}
            handleHistoryMouseMove={handleHistoryMouseMove}
            handleHistoryMouseUp={handleHistoryMouseUp}
            isDraggingHistory={isDraggingHistory}
          />
        </section>
      </main>

      {/* Dataset Deep-Dive Bottom Explorer */}
      <DatasetExplorer
        dataset={dataset}
        setDatasetModal={setDatasetModal}
      />

      {/* Page Footer */}
      <Footer />

      {/* Fullscreen Zoom Modal */}
      <ZoomModal
        activeChart={activeChart}
        dataset={dataset}
        selectedPalette={selectedPalette}
        selectedStyle={selectedStyle}
        viewMode={viewMode}
        isOpen={zoomModal}
        onClose={() => setZoomModal(false)}
        onDownload={handleDownload}
      />

      {/* Fullscreen Dataset Inspector Modal */}
      <DatasetModal
        dataset={dataset}
        isOpen={datasetModal}
        onClose={() => setDatasetModal(false)}
        tableSearch={tableSearch}
        setTableSearch={setTableSearch}
      />
    </div>
  );
}
