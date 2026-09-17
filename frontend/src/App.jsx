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

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

export default function App() {
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem('chartify_theme');
    return saved === 'dark' ? 'light' : (saved || 'light');
  });
  const [dataset, setDataset] = useState(null);
  const [query, setQuery] = useState('');
  const [selectedChartType, setSelectedChartType] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [activeChart, setActiveChart] = useState(null);
  const [sessionTokens, setSessionTokens] = useState(0);
  const [chartHistory, setChartHistory] = useState([]);
  const [zoomModal, setZoomModal] = useState(false);
  const [viewMode, setViewMode] = useState('3d');
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

  // Fetch current dataset metadata
  const fetchDataset = async () => {
    try {
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

  // Handle CSV Upload
  const handleFileUpload = async (e) => {
    const inputEl = e.target;
    const file = inputEl?.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    setUploading(true);
    try {
      const res = await fetch(`${API_BASE}/api/upload-csv`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        // If upload response includes complete dataset metadata, use it directly;
        // otherwise always call fetchDataset() to ensure the UI has full data
        if (data && Array.isArray(data.numeric_columns) && Array.isArray(data.columns)) {
          setDataset(data);
        } else {
          await fetchDataset();
        }
        setToast({
          message: `Dataset "${file.name}" loaded! (${data.row_count || 'new'} rows, ${data.column_count || data.columns?.length || ''} columns)`,
          type: 'success'
        });
      } else {
        setToast({ message: data.detail || 'Upload failed', type: 'error' });
      }
    } catch (err) {
      console.error('Upload error:', err);
      // Fallback: try fetching dataset in case upload completed on backend
      try {
        await fetchDataset();
      } catch (_) {}
      setToast({ message: 'Failed to upload CSV dataset', type: 'error' });
    } finally {
      setUploading(false);
      // Reset input so same file can be re-uploaded
      try {
        if (inputEl) inputEl.value = '';
      } catch (_) {}
    }
  };

  // Handle Chart Generation
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

      const data = await res.json();

      if (res.ok && data.success) {
        if (data.tool_called) {
          const newChart = {
            id: Date.now(),
            url: data.chart_url,
            chart_type: data.chart_type,
            title: data.tool_args?.title || data.chart_type,
            tokens: data.tokens,
            query: q,
            result: data.result,
            args: {
              ...data.tool_args,
              style: effectiveStyle,
              palette: effectivePalette
            }
          };
          setActiveChart(newChart);
          setChartHistory((prev) => [newChart, ...prev]);
          setSessionTokens((prev) => prev + (data.tokens?.total || 0));
        } else {
          setToast({
            message: data.ai_response || 'AI did not generate a chart. Try a more specific query.',
            type: 'error'
          });
        }
      } else {
        setToast({ message: data.detail || 'Failed to generate chart', type: 'error' });
      }
    } catch (err) {
      setToast({ message: 'Error connecting to AI visualization engine', type: 'error' });
    } finally {
      setLoading(false);
      setQuery('');
    }
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
          const updatedChart = {
            ...activeChart,
            url: data.chart_url,
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

  // Download Chart PNG
  const handleDownload = (e) => {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    if (!activeChart || !activeChart.url) return;
    try {
      const tempLink = document.createElement('a');
      tempLink.href = activeChart.url;
      tempLink.download = `${activeChart.chart_type || 'chart'}.png`;
      document.body.appendChild(tempLink);
      tempLink.click();
      document.body.removeChild(tempLink);
      setToast({ message: 'High-res PNG downloaded successfully!', type: 'success' });
    } catch (err) {
      console.error('Download failed:', err);
      setToast({ message: 'Chart download failed', type: 'error' });
    }
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
      const accurateQuery = generateAccurateChartQuery(chartType, dataset);
      if (accurateQuery) {
        setQuery(accurateQuery);
      }
    } else {
      setQuery('');
    }
    if (inputRef.current) {
      inputRef.current.focus();
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
