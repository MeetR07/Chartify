import React, { useState, useEffect, useRef, useMemo } from 'react';
import Navbar from './components/Navbar';
import DatasetInspector from './components/DatasetInspector';
import QuickAnalytics from './components/QuickAnalytics';
import PromptHeroBar from './components/PromptHeroBar';
import AestheticsStudio from './components/AestheticsStudio';
import InteractiveCanvas from './components/InteractiveCanvas';
import SessionHistoryDock from './components/SessionHistoryDock';
import DatasetExplorer from './components/DatasetExplorer';
import ZoomModal from './components/ZoomModal';
import DatasetModal from './components/DatasetModal';
import Toast from './components/Toast';
import Footer from './components/Footer';
import { getDynamicQuickChips } from './utils/dynamicPrompts';
import { THEME_STYLES, PALETTES } from './constants/themeOptions';

export default function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('chartify_theme') || 'dark');
  const [dataset, setDataset] = useState(null);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [activeChart, setActiveChart] = useState(null);
  const [sessionTokens, setSessionTokens] = useState(0);
  const [chartHistory, setChartHistory] = useState([]);
  const [zoomModal, setZoomModal] = useState(false);
  const [datasetModal, setDatasetModal] = useState(false);
  const [tableSearch, setTableSearch] = useState('');
  const [toast, setToast] = useState({ message: '', type: 'error' });
  const [selectedStyle, setSelectedStyle] = useState('whitegrid');
  const [selectedPalette, setSelectedPalette] = useState('deep');
  const [isStyleOpen, setIsStyleOpen] = useState(false);
  const [isPaletteOpen, setIsPaletteOpen] = useState(false);
  const [isRestyling, setIsRestyling] = useState(false);
  const [isDraggingHistory, setIsDraggingHistory] = useState(false);
  const [dragStartX, setDragStartX] = useState(0);
  const [dragScrollLeft, setDragScrollLeft] = useState(0);
  const [promptCategory, setPromptCategory] = useState('all');

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
      const res = await fetch('/api/dataset');
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
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    setUploading(true);
    try {
      const res = await fetch('/api/upload-csv', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        await fetchDataset();
        setToast({
          message: `Dataset "${file.name}" loaded successfully (${data.row_count || 'new'} rows)!`,
          type: 'success'
        });
      } else {
        setToast({ message: data.detail || 'Upload failed', type: 'error' });
      }
    } catch (err) {
      setToast({ message: 'Failed to upload CSV dataset', type: 'error' });
    } finally {
      setUploading(false);
    }
  };

  // Handle Chart Generation
  const handleGenerate = async (queryText) => {
    const q = queryText || query;
    if (!q.trim() || loading) return;

    setLoading(true);

    try {
      const res = await fetch('/api/generate-chart', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: q,
          style: selectedStyle,
          palette: selectedPalette
        }),
      });

      const data = await res.json();

      if (res.ok && data.success) {
        if (data.tool_called) {
          const newChart = {
            id: Date.now(),
            url: data.chart_url,
            interactive_spec: data.interactive_spec,
            has_interactive: data.has_interactive,
            chart_type: data.chart_type,
            title: data.tool_args?.title || data.chart_type,
            tokens: data.tokens,
            query: q,
            result: data.result,
            args: data.tool_args
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

  // Dynamic Style & Palette updater with visual feedback
  const applyStyleAndPalette = async (style, palette) => {
    setSelectedStyle(style);
    setSelectedPalette(palette);
    if (activeChart && activeChart.args) {
      if (restyleTimerRef.current) {
        clearTimeout(restyleTimerRef.current);
      }

      let isDone = false;
      restyleTimerRef.current = setTimeout(() => {
        if (!isDone) {
          setIsRestyling(true);
        }
      }, 700);

      try {
        const res = await fetch('/api/apply-style', {
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
          setActiveChart((prev) => ({
            ...prev,
            url: data.chart_url,
            interactive_spec: data.interactive_spec,
            has_interactive: data.has_interactive,
            args: data.tool_args
          }));
          setChartHistory((prev) =>
            prev.map((c) => (c.id === activeChart.id ? {
              ...c,
              url: data.chart_url,
              interactive_spec: data.interactive_spec,
              has_interactive: data.has_interactive,
              args: data.tool_args
            } : c))
          );
        }
      } catch (err) {
        console.error('Failed to update style and palette:', err);
      } finally {
        isDone = true;
        if (restyleTimerRef.current) {
          clearTimeout(restyleTimerRef.current);
          restyleTimerRef.current = null;
        }
        setIsRestyling(false);
      }
    }
  };

  const handleStyleChange = (newStyle) => {
    applyStyleAndPalette(newStyle, selectedPalette);
  };

  const handlePaletteChange = (newPalette) => {
    applyStyleAndPalette(selectedStyle, newPalette);
  };

  const handleRandomStyle = () => {
    const randomStyle = THEME_STYLES[Math.floor(Math.random() * THEME_STYLES.length)].id;
    const randomPalette = PALETTES[Math.floor(Math.random() * PALETTES.length)].id;
    applyStyleAndPalette(randomStyle, randomPalette);
  };

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

  const handleColumnClick = (colName) => {
    setQuery((prev) => {
      const trimmed = prev.trim();
      return trimmed ? `${trimmed} by ${colName}` : `Plot of ${colName}`;
    });
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  // Memoized dynamic chips
  const dynamicChips = useMemo(() => getDynamicQuickChips(dataset), [dataset]);

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
        {/* Left Sidebar: Dataset & Quick Analytics */}
        <aside className="glass-panel sidebar-panel">
          <DatasetInspector
            dataset={dataset}
            fetchDataset={fetchDataset}
            setDatasetModal={setDatasetModal}
            handleFileUpload={handleFileUpload}
            uploading={uploading}
            onColumnClick={handleColumnClick}
          />

          <QuickAnalytics
            chips={dynamicChips}
            promptCategory={promptCategory}
            setPromptCategory={setPromptCategory}
            onChipClick={handleChipClick}
            loading={loading}
          />
        </aside>

        {/* Right Studio Area: Command Bar, Aesthetics Studio, Canvas, History */}
        <section className="studio-column">
          {/* Aurora Prompt Hero Command Bar */}
          <PromptHeroBar
            query={query}
            setQuery={setQuery}
            loading={loading}
            handleGenerate={handleGenerate}
            inputRef={inputRef}
          />

          {/* Chart Aesthetics Studio */}
          <AestheticsStudio
            selectedStyle={selectedStyle}
            selectedPalette={selectedPalette}
            handleStyleChange={handleStyleChange}
            handlePaletteChange={handlePaletteChange}
            handleRandomStyle={handleRandomStyle}
            isStyleOpen={isStyleOpen}
            setIsStyleOpen={setIsStyleOpen}
            isPaletteOpen={isPaletteOpen}
            setIsPaletteOpen={setIsPaletteOpen}
            isRestyling={isRestyling}
            styleBoxRef={styleBoxRef}
            paletteBoxRef={paletteBoxRef}
          />

          {/* Interactive Chart Canvas */}
          <InteractiveCanvas
            activeChart={activeChart}
            loading={loading}
            isRestyling={isRestyling}
            handleDownload={handleDownload}
            setZoomModal={setZoomModal}
            onQuickPrompt={handleChipClick}
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
