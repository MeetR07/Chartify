import React, { useState, useEffect, useRef } from 'react';
import {
  Sparkles,
  BarChart3,
  TrendingUp,
  Table as TableIcon,
  Upload,
  Zap,
  Download,
  Maximize2,
  X,
  Send,
  Database,
  Layers,
  Cpu,
  RefreshCw,
  PieChart,
  Grid,
  Sun,
  Moon,
  Palette,
  ChevronLeft,
  ChevronRight,
  Sliders,
  Check,
  ChevronDown,
  Shuffle
} from 'lucide-react';

const THEME_STYLES = [
  { id: 'whitegrid', label: 'Whitegrid', desc: 'Clean Light Background', icon: '🌟' },
  { id: 'dark_background', label: 'Dark Glow', desc: 'Deep Dark Glow', icon: '🌙' },
  { id: 'darkgrid', label: 'Dark Grid', desc: 'Technical Dark Grid', icon: '📐' },
  { id: 'fivethirtyeight', label: '538 Editorial', desc: 'FiveThirtyEight Journalism', icon: '📰' },
  { id: 'ggplot', label: 'GGPlot', desc: 'Classic R GGPlot2', icon: '📊' },
  { id: 'ticks', label: 'Minimal', desc: 'Clean Minimal Ticks', icon: '⚡' },
];

const PALETTE_GROUPS = [
  {
    group: '🌈 Gradient & Sequential',
    palettes: [
      { id: 'viridis', label: 'Viridis', desc: 'Purple → Teal → Yellow', colors: ['#440154', '#21918c', '#fde725'] },
      { id: 'plasma', label: 'Plasma', desc: 'Purple → Pink → Orange', colors: ['#7e03a8', '#cc4778', '#f89540'] },
      { id: 'inferno', label: 'Inferno', desc: 'Black → Crimson → Flame', colors: ['#57106e', '#bc3754', '#f98e09'] },
      { id: 'magma', label: 'Magma', desc: 'Dark → Magenta → Peach', colors: ['#000004', '#b73779', '#fcfdbf'] },
      { id: 'rocket', label: 'Rocket', desc: 'Navy → Magenta → Gold', colors: ['#03051a', '#ce436e', '#fae1ab'] },
      { id: 'mako', label: 'Mako', desc: 'Deep Navy → Teal → Mint', colors: ['#0b0405', '#357ba2', '#def5e5'] },
    ]
  },
  {
    group: '🌊 Ocean & Cool (Diverging)',
    palettes: [
      { id: 'coolwarm', label: 'Coolwarm', desc: 'Polar Blue → Gray → Red', colors: ['#3b4cc0', '#dddcdb', '#8b0000'] },
      { id: 'crest', label: 'Crest', desc: 'Mint → Teal → Sea Blue', colors: ['#61aa90', '#33858d', '#1e5d86'] },
      { id: 'icefire', label: 'Icefire', desc: 'Blue → Dark → Crimson', colors: ['#4167c7', '#1f1e1e', '#b93540'] },
    ]
  },
  {
    group: '🔥 Sunset & Warm',
    palettes: [
      { id: 'flare', label: 'Flare', desc: 'Peach → Rose → Plum', colors: ['#e5715e', '#c14168', '#863071'] },
      { id: 'Spectral', label: 'Spectral', desc: 'Red → Amber → Green', colors: ['#d53e4f', '#fee08b', '#99d594'] },
      { id: 'copper', label: 'Copper Bronze', desc: 'Bronze → Copper → Amber', colors: ['#4f3220', '#9e6440', '#ed9660'] },
    ]
  },
  {
    group: '🎯 Categorical & Distinct',
    palettes: [
      { id: 'deep', label: 'Deep', desc: 'Classic Blue / Green / Red', colors: ['#4C72B0', '#55A868', '#C44E52'] },
      { id: 'pastel', label: 'Pastel', desc: 'Soft Calming Pastels', colors: ['#a1c9f4', '#8de5a1', '#ff9f9b'] },
      { id: 'Set2', label: 'Set2', desc: 'Muted Professional Tones', colors: ['#66c2a5', '#fc8d62', '#8da0cb'] },
      { id: 'colorblind', label: 'Pro Colorblind', desc: 'High-Contrast Accessible', colors: ['#0173b2', '#de8f05', '#029e73'] },
    ]
  }
];

const PALETTES = PALETTE_GROUPS.flatMap((g) => g.palettes);

const PROMPT_CATEGORIES = [
  { id: 'all', label: 'All', icon: '✨' },
  { id: 'compare', label: 'Compare', icon: '📊' },
  { id: 'dist', label: 'Distribute', icon: '🍩' },
  { id: 'correlate', label: 'Relations', icon: '🔥' },
  { id: 'theme', label: 'Styles', icon: '🎨' },
];

export default function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('novachart_theme') || 'dark');
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
  const [errorMsg, setErrorMsg] = useState('');
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
    localStorage.setItem('novachart_theme', theme);
  }, [theme]);

  // Click outside to close dropdowns only if clicked completely outside both
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
    setErrorMsg('');
    try {
      const res = await fetch('/api/upload-csv', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        await fetchDataset();
      } else {
        setErrorMsg(data.detail || 'Upload failed');
      }
    } catch (err) {
      setErrorMsg('Failed to upload file');
    } finally {
      setUploading(false);
    }
  };

  // Handle Chart Generation
  const handleGenerate = async (queryText) => {
    const q = queryText || query;
    if (!q.trim() || loading) return;

    setLoading(true);
    setErrorMsg('');

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
            chart_type: data.chart_type,
            title: data.tool_args?.title || data.chart_type,
            tokens: data.tokens,
            query: q,
            result: data.result,
            args: data.tool_args
          };
          setActiveChart(newChart);
          // Preserve all generated charts without filtering out duplicate chart types
          setChartHistory((prev) => [newChart, ...prev]);
          setSessionTokens((prev) => prev + (data.tokens?.total || 0));
        } else {
          setErrorMsg(data.ai_response || 'AI did not generate a chart. Try asking more specifically.');
        }
      } else {
        setErrorMsg(data.detail || 'Failed to generate chart');
      }
    } catch (err) {
      setErrorMsg('Error connecting to AI backend');
    } finally {
      setLoading(false);
      setQuery('');
    }
  };

  // Unified Dynamic Style & Palette updater that immediately updates active chart
  const applyStyleAndPalette = async (style, palette) => {
    setSelectedStyle(style);
    setSelectedPalette(palette);
    if (activeChart && activeChart.args) {
      if (restyleTimerRef.current) {
        clearTimeout(restyleTimerRef.current);
      }

      let isDone = false;
      // Sirf tabhi 3 dots dikhega jab operation 1 second (> 1000ms) se zyada time le
      restyleTimerRef.current = setTimeout(() => {
        if (!isDone) {
          setIsRestyling(true);
        }
      }, 1000);

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
            args: data.tool_args
          }));
          setChartHistory((prev) =>
            prev.map((c) => (c.id === activeChart.id ? { ...c, url: data.chart_url, args: data.tool_args } : c))
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

  // Explicit Download Handler (Strictly downloads ONLY on user click)
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
    } catch (err) {
      console.error('Download failed:', err);
    }
  };

  // Movable History Carousel Handlers
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

  // Dynamic Smart Prompts based on Active Dataset Columns
  const getDynamicQuickChips = () => {
    if (!dataset || !dataset.columns || dataset.columns.length === 0) return [];

    const numCols = dataset.numeric_columns || [];
    const catCols = dataset.categorical_columns || [];
    const allCols = dataset.columns || [];

    const cat1 = catCols[0] || allCols[0];
    const cat2 = catCols[1] || catCols[0] || allCols[0];
    const num1 = numCols[0] || (allCols.length > 1 ? allCols[1] : allCols[0]);
    const num2 = numCols[1] || numCols[0] || num1;

    const chips = [];

    // --- Compare Category ---
    if (cat1 && num1) {
      chips.push({
        category: 'compare',
        icon: '📊',
        tag: 'Bar',
        title: 'Bar Comparison',
        desc: `${num1} across ${cat1}`,
        query: `Plot a bar chart comparing ${num1} by ${cat1}`,
        accent: '#6366f1'
      });
    }

    const timeCol = allCols.find((c) => /month|year|date|day|time|period/i.test(c)) || cat1;
    if (timeCol && num1) {
      chips.push({
        category: 'compare',
        icon: '📈',
        tag: 'Line',
        title: 'Line Trend',
        desc: `${num1} over ${timeCol}`,
        query: `Show a line chart of ${num1} across ${timeCol}`,
        accent: '#818cf8'
      });
    }

    if (cat1 && num1) {
      chips.push({
        category: 'compare',
        icon: '🍭',
        tag: 'Lollipop',
        title: 'Lollipop Stem',
        desc: `${num1} across ${cat1}`,
        query: `Create a lollipop chart of ${num1} across ${cat1}`,
        accent: '#ec4899'
      });
    }

    if (cat1 && num1) {
      chips.push({
        category: 'compare',
        icon: '🗺️',
        tag: 'Treemap',
        title: 'Treemap Share',
        desc: `${cat1} by ${num1}`,
        query: `Generate a treemap of ${num1} by ${cat1}`,
        accent: '#06b6d4'
      });
    }

    if (cat1 && num1) {
      chips.push({
        category: 'compare',
        icon: '🪜',
        tag: 'Waterfall',
        title: 'Waterfall Flow',
        desc: `${cat1} vs ${num1}`,
        query: `Create a waterfall chart of ${cat1} vs ${num1}`,
        accent: '#38bdf8'
      });
    }

    // --- Distribution Category ---
    if (cat1 && num1) {
      chips.push({
        category: 'dist',
        icon: '🍩',
        tag: 'Donut',
        title: 'Donut Share',
        desc: `${cat1} (${num1})`,
        query: `Generate a donut chart of ${cat1} by ${num1}`,
        accent: '#f59e0b'
      });
    }

    if (cat1 && num1) {
      chips.push({
        category: 'dist',
        icon: '🔻',
        tag: 'Funnel',
        title: 'Funnel Dropoff',
        desc: `${cat1} conversion (${num1})`,
        query: `Show a funnel chart of ${cat1} stages and ${num1}`,
        accent: '#f97316'
      });
    }

    if (num1) {
      chips.push({
        category: 'dist',
        icon: '📦',
        tag: 'Box',
        title: 'Box Outliers',
        desc: `${num1} ${cat1 ? `by ${cat1}` : ''}`,
        query: `Display a box plot for ${num1} ${cat1 ? `by ${cat1}` : ''}`,
        accent: '#10b981'
      });
    }

    if (num1) {
      chips.push({
        category: 'dist',
        icon: '📶',
        tag: 'Hist',
        title: 'Histogram Dist',
        desc: `${num1} distribution`,
        query: `Create a histogram distribution of ${num1}`,
        accent: '#14b8a6'
      });
    }

    // --- Relations Category ---
    if (numCols.length >= 2) {
      chips.push({
        category: 'correlate',
        icon: '🔥',
        tag: 'Heatmap',
        title: 'Corr Heatmap',
        desc: `Matrix (${numCols.slice(0, 2).join(', ')})`,
        query: `Create a correlation heatmap of all numeric columns`,
        accent: '#ef4444'
      });
    }

    if (numCols.length >= 2) {
      chips.push({
        category: 'correlate',
        icon: '🎯',
        tag: 'Scatter',
        title: 'Scatter Points',
        desc: `${num1} vs ${num2}`,
        query: `Generate a scatter plot of ${num1} vs ${num2}`,
        accent: '#a855f7'
      });
    }

    if (numCols.length >= 2) {
      chips.push({
        category: 'correlate',
        icon: '🫧',
        tag: 'Bubble',
        title: 'Bubble Multi-Var',
        desc: `${num1} vs ${num2} (${cat1 || 'size'})`,
        query: `Create a bubble chart of ${num1} vs ${num2} ${cat1 ? `colored by ${cat1}` : ''}`,
        accent: '#c084fc'
      });
    }

    if (numCols.length >= 2) {
      chips.push({
        category: 'correlate',
        icon: '🕸️',
        tag: 'Radar',
        title: 'Radar Spider',
        desc: `Multi-metric spider chart`,
        query: `Generate a radar chart comparing metrics across ${cat1 || 'items'}`,
        accent: '#8b5cf6'
      });
    }

    // --- Theme Styles Category ---
    if (numCols.length >= 2) {
      chips.push({
        category: 'theme',
        icon: '🌙',
        tag: 'Dark Magma',
        title: 'Dark Magma Glow',
        desc: `Dark background & Magma`,
        query: `Generate a correlation heatmap with dark_background style and magma palette`,
        accent: '#f43f5e'
      });
    }

    if (cat1 && num1) {
      chips.push({
        category: 'theme',
        icon: '🎨',
        tag: 'Pastel Bar',
        title: 'Pastel Clean',
        desc: `${num1} by ${cat1} (Whitegrid)`,
        query: `Create a bar chart of ${num1} by ${cat1} with pastel palette and whitegrid style`,
        accent: '#10b981'
      });
      chips.push({
        category: 'theme',
        icon: '📰',
        tag: '538 Waterfall',
        title: '538 Journalism',
        desc: `${cat1} vs ${num1} (Coolwarm)`,
        query: `Show a waterfall chart of ${cat1} vs ${num1} with fivethirtyeight style and coolwarm palette`,
        accent: '#3b82f6'
      });
    }

    return chips;
  };

  const handleChipClick = (chipQuery) => {
    setQuery(chipQuery);
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  return (
    <div className="app-wrapper">
      {/* Top Navigation Bar */}
      <nav className="navbar">
        <div className="brand-section">
          <div className="logo-icon">
            <Sparkles size={22} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="brand-title">Chartify</span>
              <span className="brand-badge">AI STUDIO</span>
            </div>
          </div>
        </div>

        <div className="nav-actions">
          <div className="status-pill">
            <span className="status-dot"></span>
            <span>Gemini 3.6 Flash Active</span>
          </div>

          <div className="token-pill">
            <Zap size={14} />
            <span>{sessionTokens.toLocaleString()} Tokens</span>
          </div>

          <button
            onClick={() => setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'))}
            className="theme-toggle-btn"
            title={theme === 'dark' ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
            aria-label="Toggle Theme"
          >
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </div>
      </nav>

      {/* Main Dashboard Layout */}
      <main className="dashboard-container">
        {/* Left Column: Dataset & Controls */}
        <aside className="glass-panel sidebar-panel">
          <div className="panel-header">
            <span className="panel-title">
              <Database className="panel-icon" size={18} />
              Dataset Inspector
            </span>
            <div style={{ display: 'flex', gap: '6px' }}>
              <button
                onClick={() => setDatasetModal(true)}
                className="action-btn"
                title="Fullscreen Dataset Inspector"
                style={{ padding: '6px 8px' }}
                aria-label="Fullscreen Dataset"
              >
                <Maximize2 size={14} />
              </button>
              <button
                onClick={fetchDataset}
                className="action-btn"
                title="Refresh Dataset"
                style={{ padding: '6px 8px' }}
                aria-label="Refresh Dataset"
              >
                <RefreshCw size={14} />
              </button>
            </div>
          </div>

          {dataset && (
            <>
              {/* Summary Stats */}
              <div className="data-summary-bar">
                <div className="stat-box">
                  <div className="stat-value">{dataset.row_count}</div>
                  <div className="stat-label">Rows</div>
                </div>
                <div className="stat-box">
                  <div className="stat-value">{dataset.column_count}</div>
                  <div className="stat-label">Columns</div>
                </div>
                <div className="stat-box">
                  <div className="stat-value">{dataset.numeric_columns.length}</div>
                  <div className="stat-label">Numeric</div>
                </div>
              </div>

              {/* Column Tags */}
              <div className="columns-tags">
                {dataset.columns.map((col) => {
                  const isNum = dataset.numeric_columns.includes(col);
                  return (
                    <span key={col} className={`col-tag ${isNum ? 'num' : ''}`}>
                      {col}
                      <small style={{ opacity: 0.6 }}>({isNum ? 'num' : 'str'})</small>
                    </span>
                  );
                })}
              </div>

              {/* Data Table Preview */}
              <div className="table-wrapper">
                <table className="preview-table">
                  <thead>
                    <tr>
                      {dataset.columns.map((col) => (
                        <th key={col}>{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(dataset.head_rows || dataset.sample_data || []).map((row, idx) => (
                      <tr key={`head-${idx}`}>
                        {dataset.columns.map((col) => (
                          <td key={col}>{String(row[col])}</td>
                        ))}
                      </tr>
                    ))}

                    {dataset.has_ellipsis && (
                      <tr>
                        <td
                          colSpan={dataset.columns.length}
                          style={{
                            textAlign: 'center',
                            padding: '6px',
                            background: 'rgba(99, 102, 241, 0.1)',
                            color: 'var(--accent-primary-light)',
                            fontFamily: 'var(--font-mono)',
                            fontSize: '0.74rem',
                            fontWeight: 600,
                            letterSpacing: '0.05em'
                          }}
                        >
                          ••• {dataset.hidden_count.toLocaleString()} rows hidden •••
                        </td>
                      </tr>
                    )}

                    {(dataset.tail_rows || []).map((row, idx) => (
                      <tr key={`tail-${idx}`}>
                        {dataset.columns.map((col) => (
                          <td key={col}>{String(row[col])}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {/* Upload Custom CSV Dropzone */}
          <label className="upload-btn">
            <Upload size={16} />
            <span>{uploading ? 'Processing CSV...' : 'Upload Custom CSV Dataset'}</span>
            <input
              type="file"
              accept=".csv"
              style={{ display: 'none' }}
              onChange={handleFileUpload}
              disabled={uploading}
            />
          </label>

          {/* Quick Prompts Section */}
          <div className="quick-prompt-section">
            <div className="prompt-section-header">
              <div className="section-subtitle">
                <Zap size={14} style={{ color: 'var(--accent-amber)' }} />
                <span>Quick Analytics</span>
              </div>
              <span className="prompt-count-pill">
                {(promptCategory === 'all'
                  ? getDynamicQuickChips()
                  : getDynamicQuickChips().filter((c) => c.category === promptCategory)
                ).length}
              </span>
            </div>

            {/* Category Filter Pills */}
            <div className="prompt-category-tabs">
              {PROMPT_CATEGORIES.map((cat) => (
                <button
                  key={cat.id}
                  className={`cat-tab-btn ${promptCategory === cat.id ? 'active' : ''}`}
                  onClick={() => setPromptCategory(cat.id)}
                  type="button"
                >
                  <span className="cat-tab-icon">{cat.icon}</span>
                  <span>{cat.label}</span>
                </button>
              ))}
            </div>

            {/* Prompt Cards Grid */}
            <div className="prompt-cards-container">
              {(promptCategory === 'all'
                ? getDynamicQuickChips()
                : getDynamicQuickChips().filter((c) => c.category === promptCategory)
              ).map((chip, idx) => (
                <button
                  key={idx}
                  className="prompt-card"
                  onClick={() => handleChipClick(chip.query)}
                  disabled={loading}
                  title={chip.query}
                  type="button"
                >
                  <div
                    className="prompt-card-icon-badge"
                    style={{
                      background: `${chip.accent}18`,
                      borderColor: `${chip.accent}35`,
                      color: chip.accent
                    }}
                  >
                    <span>{chip.icon}</span>
                  </div>
                  <div className="prompt-card-info">
                    <div className="prompt-card-top-line">
                      <span className="prompt-card-title">{chip.title}</span>
                      <span
                        className="prompt-card-tag"
                        style={{
                          background: `${chip.accent}16`,
                          color: chip.accent,
                          borderColor: `${chip.accent}30`
                        }}
                      >
                        {chip.tag}
                      </span>
                    </div>
                    <span className="prompt-card-desc">{chip.desc}</span>
                  </div>
                  <div className="prompt-card-arrow">↗</div>
                </button>
              ))}
            </div>
          </div>
        </aside>

        {/* Right Column: AI Studio & Visualization Canvas */}
        <section className="studio-column">
          {/* Natural Language Prompt Command Bar - High Visibility Hero Hub */}
          <div className="prompt-bar-wrapper">
            <form
              className="prompt-bar-container"
              onSubmit={(e) => {
                e.preventDefault();
                handleGenerate();
              }}
            >
              {/* Left AI Orb & Badge */}
              <div className="prompt-left-badge">
                <div className="prompt-orb">
                  <Sparkles className="prompt-icon" size={15} />
                </div>
                <span className="prompt-hub-tag">AI Query</span>
              </div>

              {/* Main Text Input */}
              <input
                ref={inputRef}
                type="text"
                className="prompt-input"
                placeholder="Ask anything... e.g. 'Bar chart of Sales by Month' or 'Correlation Heatmap'..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                disabled={loading}
                autoComplete="off"
                spellCheck="false"
              />

              {/* Clear button if text exists */}
              {query && !loading && (
                <button
                  type="button"
                  className="prompt-clear-btn"
                  onClick={() => {
                    setQuery('');
                    if (inputRef.current) inputRef.current.focus();
                  }}
                  title="Clear prompt"
                >
                  <X size={14} />
                </button>
              )}

              {/* Submit Button */}
              <button
                type="submit"
                className="submit-btn"
                disabled={loading || !query.trim()}
              >
                {loading ? (
                  <>
                    <RefreshCw size={16} className="spin" />
                    <span>Analyzing...</span>
                  </>
                ) : (
                  <>
                    <span>Generate Chart</span>
                    <Send size={15} />
                    <kbd className="prompt-enter-kbd">↵</kbd>
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Style & Palette Studio Controls (HTML Selection Mode) */}
          <div className="style-studio-card">
            {/* Studio Header: Title & Quick Actions */}
            <div className="studio-header">
              <div className="studio-header-title">
                <Sliders size={14} className="studio-header-icon" />
                <span>Chart Aesthetics Studio</span>
              </div>

              <div className="studio-header-right">
                {/* Live Selected Preview Badge */}
                <div className="studio-active-badge">
                  <span className="active-badge-label">Active:</span>
                  <span className="active-badge-val">
                    <span className="active-badge-icon">
                      {THEME_STYLES.find((s) => s.id === selectedStyle)?.icon}
                    </span>
                    <span>{THEME_STYLES.find((s) => s.id === selectedStyle)?.label || selectedStyle}</span>
                  </span>
                  <span className="active-badge-divider">•</span>
                  <span className="active-badge-val">
                    <span className="palette-dots mini">
                      {PALETTES.find((p) => p.id === selectedPalette)?.colors.map((c, i) => (
                        <span key={i} className="preview-dot" style={{ backgroundColor: c }} />
                      ))}
                    </span>
                    <span>{PALETTES.find((p) => p.id === selectedPalette)?.label || selectedPalette}</span>
                  </span>
                  {isRestyling && (
                    <span className="bouncing-dots inline" style={{ marginLeft: '6px' }}>
                      <span className="dot dot-1"></span>
                      <span className="dot dot-2"></span>
                      <span className="dot dot-3"></span>
                    </span>
                  )}
                </div>

                {/* Dual Toggle Button: Open / Close Both Simultaneously */}
                <button
                  type="button"
                  className="studio-tool-btn"
                  onClick={() => {
                    const bothOpen = !(isStyleOpen && isPaletteOpen);
                    setIsStyleOpen(bothOpen);
                    setIsPaletteOpen(bothOpen);
                  }}
                  title="Open or close both Theme and Palette menus together"
                >
                  <Layers size={12} />
                  <span>{isStyleOpen && isPaletteOpen ? 'Close Both' : 'Open Both Menus'}</span>
                </button>

                {/* Surprise / Randomize Button */}
                <button
                  type="button"
                  className="studio-tool-btn"
                  onClick={handleRandomStyle}
                  disabled={isRestyling}
                  title="Surprise me with a random style & palette combo"
                >
                  <Shuffle size={12} className={isRestyling ? 'spin' : ''} />
                  <span>Surprise Me</span>
                  {isRestyling && (
                    <span className="bouncing-dots inline">
                      <span className="dot dot-1"></span>
                      <span className="dot dot-2"></span>
                      <span className="dot dot-3"></span>
                    </span>
                  )}
                </button>
              </div>
            </div>

            {/* Selection Controls Grid: Custom Dual Menus that can both be open simultaneously */}
            <div className="studio-selection-grid">
              {/* Select 1: Theme & Style */}
              <div className="select-control-box" ref={styleBoxRef}>
                <div className="select-control-header">
                  <label className="select-control-label">
                    <Palette size={13} className="studio-icon" />
                    <span>Theme & Base Style</span>
                  </label>
                  <span className="current-select-tag">
                    {THEME_STYLES.find((s) => s.id === selectedStyle)?.icon} {THEME_STYLES.find((s) => s.id === selectedStyle)?.label}
                  </span>
                </div>
                <div className="custom-dropdown-container">
                  <button
                    type="button"
                    className={`custom-dropdown-trigger ${isStyleOpen ? 'active' : ''}`}
                    onClick={() => setIsStyleOpen((prev) => !prev)}
                  >
                    <span className="trigger-label">
                      <span className="trigger-icon">
                        {THEME_STYLES.find((s) => s.id === selectedStyle)?.icon}
                      </span>
                      <span>
                        {THEME_STYLES.find((s) => s.id === selectedStyle)?.label} — {THEME_STYLES.find((s) => s.id === selectedStyle)?.desc}
                      </span>
                    </span>
                    <ChevronDown size={14} className={`select-chevron ${isStyleOpen ? 'rotated' : ''}`} />
                  </button>

                  {/* Dropdown Menu */}
                  {isStyleOpen && (
                    <div className="custom-dropdown-menu">
                      {THEME_STYLES.map((st) => (
                        <button
                          key={st.id}
                          type="button"
                          className={`custom-dropdown-item ${selectedStyle === st.id ? 'selected' : ''}`}
                          onClick={() => handleStyleChange(st.id)}
                        >
                          <div className="item-main">
                            <span className="item-icon">{st.icon}</span>
                            <div className="item-text-group">
                              <span className="item-title">{st.label}</span>
                              <span className="item-desc">{st.desc}</span>
                            </div>
                          </div>
                          {selectedStyle === st.id && (
                            isRestyling ? (
                              <span className="bouncing-dots inline">
                                <span className="dot dot-1"></span>
                                <span className="dot dot-2"></span>
                                <span className="dot dot-3"></span>
                              </span>
                            ) : (
                              <Check size={14} className="item-check" />
                            )
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Select 2: Color Palette */}
              <div className="select-control-box" ref={paletteBoxRef}>
                <div className="select-control-header">
                  <label className="select-control-label">
                    <Sparkles size={13} className="studio-icon" />
                    <span>Color Palette</span>
                  </label>
                  {/* Live Swatch Preview */}
                  <span className="palette-swatch-badge">
                    {PALETTES.find((p) => p.id === selectedPalette)?.colors.map((c, i) => (
                      <span key={i} className="swatch-bar" style={{ backgroundColor: c }} />
                    ))}
                    <span className="palette-swatch-name">
                      {PALETTES.find((p) => p.id === selectedPalette)?.label}
                    </span>
                  </span>
                </div>
                <div className="custom-dropdown-container">
                  <button
                    type="button"
                    className={`custom-dropdown-trigger ${isPaletteOpen ? 'active' : ''}`}
                    onClick={() => setIsPaletteOpen((prev) => !prev)}
                  >
                    <span className="trigger-label">
                      <span className="palette-dots">
                        {PALETTES.find((p) => p.id === selectedPalette)?.colors.map((c, i) => (
                          <span key={i} className="preview-dot" style={{ backgroundColor: c }} />
                        ))}
                      </span>
                      <span>
                        {PALETTES.find((p) => p.id === selectedPalette)?.label} ({PALETTES.find((p) => p.id === selectedPalette)?.desc})
                      </span>
                    </span>
                    <ChevronDown size={14} className={`select-chevron ${isPaletteOpen ? 'rotated' : ''}`} />
                  </button>

                  {/* Dropdown Menu */}
                  {isPaletteOpen && (
                    <div className="custom-dropdown-menu palette-menu">
                      {PALETTE_GROUPS.map((grp) => (
                        <div key={grp.group} className="palette-group-section">
                          <div className="palette-group-header">{grp.group}</div>
                          <div className="palette-group-items">
                            {grp.palettes.map((pal) => (
                              <button
                                key={pal.id}
                                type="button"
                                className={`custom-dropdown-item ${selectedPalette === pal.id ? 'selected' : ''}`}
                                onClick={() => handlePaletteChange(pal.id)}
                              >
                                <div className="item-main">
                                  <div className="palette-dots">
                                    {pal.colors.map((c, i) => (
                                      <span key={i} className="preview-dot" style={{ backgroundColor: c }} />
                                    ))}
                                  </div>
                                  <div className="item-text-group">
                                    <span className="item-title">{pal.label}</span>
                                    <span className="item-desc">{pal.desc}</span>
                                  </div>
                                </div>
                                {selectedPalette === pal.id && (
                                  isRestyling ? (
                                    <span className="bouncing-dots inline">
                                      <span className="dot dot-1"></span>
                                      <span className="dot dot-2"></span>
                                      <span className="dot dot-3"></span>
                                    </span>
                                  ) : (
                                    <Check size={14} className="item-check" />
                                  )
                                )}
                              </button>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Popular Curated Quick Presets */}
            <div className="studio-presets-row">
              <span className="presets-label">Quick Presets:</span>
              <div className="presets-pills">
                {[
                  { label: '🌟 Clean Light', style: 'whitegrid', palette: 'deep' },
                  { label: '🔥 Neon Sunset', style: 'dark_background', palette: 'inferno' },
                  { label: '🌊 Emerald Ocean', style: 'whitegrid', palette: 'crest' },
                  { label: '📰 538 Editorial', style: 'fivethirtyeight', palette: 'coolwarm' },
                  { label: '📊 Dark Viridis', style: 'darkgrid', palette: 'viridis' },
                  { label: '🌸 Soft Pastel', style: 'whitegrid', palette: 'pastel' },
                ].map((preset, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className={`preset-pill ${selectedStyle === preset.style && selectedPalette === preset.palette ? 'active' : ''}`}
                    onClick={() => {
                      handleStyleChange(preset.style);
                      handlePaletteChange(preset.palette);
                    }}
                    title={`Apply ${preset.label}`}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {errorMsg && (
            <div
              style={{
                padding: '12px 18px',
                background: 'rgba(244, 63, 94, 0.1)',
                border: '1px solid rgba(244, 63, 94, 0.3)',
                borderRadius: '12px',
                color: '#fda4af',
                fontSize: '0.88rem'
              }}
            >
              {errorMsg}
            </div>
          )}

          {/* Main Visualization Canvas */}
          <div className="glass-panel canvas-card">
            {/* Toolbar */}
            <div className="canvas-toolbar">
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                <span className="panel-title">
                  <BarChart3 className="panel-icon" size={20} />
                  Interactive Canvas
                </span>
                {activeChart && (
                  <>
                    <span className="chart-badge">
                      {activeChart.chart_type}
                    </span>
                    {activeChart.args?.style && (
                      <span className="chart-badge" style={{ background: 'rgba(99, 102, 241, 0.15)', color: 'var(--accent-primary-light)' }}>
                        Theme: {activeChart.args.style}
                      </span>
                    )}
                    {activeChart.args?.palette && (
                      <span className="chart-badge" style={{ background: 'rgba(236, 72, 153, 0.15)', color: '#f472b6' }}>
                        Palette: {activeChart.args.palette}
                      </span>
                    )}
                    {isRestyling && (
                      <span className="restyling-dots-badge">
                        <span>Applying</span>
                        <span className="bouncing-dots">
                          <span className="dot dot-1"></span>
                          <span className="dot dot-2"></span>
                          <span className="dot dot-3"></span>
                        </span>
                      </span>
                    )}
                  </>
                )}
              </div>

              {activeChart && (
                <div className="canvas-actions">
                  <button
                    type="button"
                    onClick={handleDownloadImage}
                    className="action-btn"
                    title="Download chart as PNG"
                  >
                    <Download size={14} />
                    <span>Download PNG</span>
                  </button>
                  <button
                    onClick={() => setZoomModal(true)}
                    className="action-btn"
                    title="Fullscreen"
                  >
                    <Maximize2 size={14} />
                  </button>
                </div>
              )}
            </div>

            {/* Viewport */}
            <div className="chart-viewport">
              {loading ? (
                <div className="loading-overlay">
                  <div className="spinner"></div>
                  <p style={{ fontWeight: 500, fontSize: '0.95rem' }}>
                    Gemini 3.6 Flash is analyzing data & plotting chart...
                  </p>
                  <small style={{ color: 'var(--text-subtle)' }}>
                    Computing optimal statistical parameters
                  </small>
                </div>
              ) : activeChart ? (
                <div className="active-chart-container">
                  <img
                    src={activeChart.url}
                    alt="Generated AI Chart"
                    className={`chart-image ${isRestyling ? 'chart-blur' : ''}`}
                  />
                  {isRestyling && (
                    <div className="restyling-overlay">
                      <div className="restyling-dots-box">
                        <div className="bouncing-dots lg">
                          <span className="dot dot-1"></span>
                          <span className="dot dot-2"></span>
                          <span className="dot dot-3"></span>
                        </div>
                        <span className="restyling-label">Applying aesthetic style & colors...</span>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="empty-state">
                  <div className="empty-icon">
                    <TrendingUp size={28} />
                  </div>
                  <h3 className="empty-title">Ready for Visualization</h3>
                  <p className="empty-desc">
                    Type a query in the prompt bar above or pick one of the quick suggestions from the left panel.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Movable History Gallery Docked */}
          {chartHistory.length > 0 && (
            <div className="glass-panel history-dock">
              <div className="panel-header" style={{ marginBottom: '6px' }}>
                <span className="panel-title" style={{ fontSize: '0.82rem' }}>
                  <Layers className="panel-icon" size={14} />
                  Session History ({chartHistory.length})
                </span>
                <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                  <button
                    onClick={() => scrollHistory('left')}
                    className="action-btn"
                    title="Scroll Left"
                    style={{ padding: '3px 7px', borderRadius: '6px' }}
                  >
                    <ChevronLeft size={13} />
                  </button>
                  <button
                    onClick={() => scrollHistory('right')}
                    className="action-btn"
                    title="Scroll Right"
                    style={{ padding: '3px 7px', borderRadius: '6px' }}
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
                style={{
                  display: 'flex',
                  gap: '10px',
                  overflowX: 'auto',
                  paddingBottom: '4px',
                  cursor: isDraggingHistory ? 'grabbing' : 'grab',
                  userSelect: 'none'
                }}
              >
                {chartHistory.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => setActiveChart(item)}
                    style={{
                      flexShrink: 0,
                      width: '105px',
                      background: activeChart?.id === item.id ? 'rgba(99, 102, 241, 0.22)' : 'rgba(0,0,0,0.3)',
                      border: activeChart?.id === item.id ? '1.5px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                      borderRadius: '8px',
                      padding: '4px 6px',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                      boxShadow: activeChart?.id === item.id ? '0 0 10px rgba(99, 102, 241, 0.4)' : 'none'
                    }}
                  >
                    <img
                      src={item.url}
                      alt={item.chart_type}
                      style={{ width: '100%', height: '42px', objectFit: 'cover', borderRadius: '5px', pointerEvents: 'none', display: 'block' }}
                    />
                    <div style={{ fontSize: '0.68rem', fontWeight: 600, color: '#fff', marginTop: '3px', textAlign: 'center', textTransform: 'capitalize', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {item.chart_type}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      </main>

      {/* Bottom Dataset Deep-Dive Explorer & Records Preview */}
      {dataset && (
        <section className="bottom-explorer-section">
          <div className="bottom-explorer-card glass-panel">
            <div className="panel-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <TableIcon className="panel-icon" size={20} />
                <div>
                  <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)' }}>
                    Dataset Deep-Dive Explorer & Live Records Preview
                  </h3>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {dataset.row_count.toLocaleString()} total rows • {dataset.column_count} columns ({dataset.numeric_columns.length} numeric, {dataset.columns.length - dataset.numeric_columns.length} categorical)
                  </div>
                </div>
              </div>
              <button
                onClick={() => setDatasetModal(true)}
                className="action-btn"
                style={{ padding: '6px 12px', fontSize: '0.78rem' }}
                aria-label="Fullscreen Table Inspector"
              >
                <Maximize2 size={14} />
                <span>Fullscreen Inspector</span>
              </button>
            </div>

            <div className="bottom-table-container">
              <table className="preview-table">
                <thead>
                  <tr>
                    <th style={{ width: '50px', textAlign: 'center' }}>#</th>
                    {dataset.columns.map((col) => (
                      <th key={col}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span>{col}</span>
                          <span style={{ fontSize: '0.66rem', opacity: 0.6 }}>
                            {dataset.numeric_columns.includes(col) ? '(num)' : '(str)'}
                          </span>
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(dataset.head_rows || dataset.sample_data || []).slice(0, 10).map((row, idx) => (
                    <tr key={`bot-head-${idx}`}>
                      <td style={{ textAlign: 'center', opacity: 0.5, fontFamily: 'var(--font-mono)' }}>{idx + 1}</td>
                      {dataset.columns.map((col) => (
                        <td key={col} style={{ fontFamily: dataset.numeric_columns.includes(col) ? 'var(--font-mono)' : 'inherit' }}>
                          {String(row[col])}
                        </td>
                      ))}
                    </tr>
                  ))}
                  {dataset.has_ellipsis && (
                    <tr>
                      <td
                        colSpan={dataset.columns.length + 1}
                        style={{
                          textAlign: 'center',
                          padding: '10px',
                          background: 'rgba(99, 102, 241, 0.08)',
                          color: 'var(--accent-primary-light)',
                          fontSize: '0.78rem',
                          fontWeight: 600,
                          letterSpacing: '0.05em'
                        }}
                      >
                        •••••• {dataset.hidden_count.toLocaleString()} more rows available in dataset ••••••
                      </td>
                    </tr>
                  )}
                  {(dataset.tail_rows || []).slice(-6).map((row, idx) => (
                    <tr key={`bot-tail-${idx}`}>
                      <td style={{ textAlign: 'center', opacity: 0.5, fontFamily: 'var(--font-mono)' }}>
                        {dataset.row_count - 6 + idx + 1}
                      </td>
                      {dataset.columns.map((col) => (
                        <td key={col} style={{ fontFamily: dataset.numeric_columns.includes(col) ? 'var(--font-mono)' : 'inherit' }}>
                          {String(row[col])}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}

      {/* Page Footer */}
      <footer className="page-footer">
        <div className="footer-content">
          <div className="footer-left">
            <span className="footer-brand">NovaChart AI Studio</span>
            <span className="footer-sep">•</span>
            <span>Natural Language Data Visualization & Analytics Engine</span>
          </div>
          <div className="footer-right">
            <span>Powered by Gemini & Mistral AI</span>
            <span className="footer-sep">•</span>
            <span className="footer-badge">Active & Ready</span>
          </div>
        </div>
      </footer>

      {/* Image Zoom Modal */}
      {zoomModal && activeChart && (
        <div className="modal-backdrop" onClick={() => setZoomModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setZoomModal(false)}>
              <X size={18} />
            </button>
            <img src={activeChart.url} alt="Fullscreen Chart" className="modal-image" />
          </div>
        </div>
      )}

      {/* Dataset Fullscreen Modal */}
      {datasetModal && dataset && (
        <div className="modal-backdrop" onClick={() => setDatasetModal(false)}>
          <div
            className="modal-content"
            onClick={(e) => e.stopPropagation()}
            style={{ width: '92vw', maxWidth: '1300px', height: '88vh', display: 'flex', flexDirection: 'column' }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', paddingBottom: '12px', borderBottom: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Database className="panel-icon" size={20} />
                <div>
                  <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-main)' }}>
                    Dataset Fullscreen Inspector
                  </h3>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    {dataset.row_count} Rows • {dataset.column_count} Columns • {dataset.numeric_columns.length} Numeric Features
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                <input
                  type="text"
                  placeholder="Filter rows..."
                  value={tableSearch}
                  onChange={(e) => setTableSearch(e.target.value)}
                  style={{
                    background: 'rgba(0,0,0,0.25)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '8px',
                    padding: '7px 12px',
                    color: 'var(--text-main)',
                    fontSize: '0.82rem',
                    outline: 'none',
                    width: '220px'
                  }}
                />
                <button className="modal-close" onClick={() => setDatasetModal(false)}>
                  <X size={18} />
                </button>
              </div>
            </div>

            <div style={{ flex: 1, overflow: 'auto', border: '1px solid var(--border-subtle)', borderRadius: '12px', background: 'rgba(0, 0, 0, 0.2)' }}>
              <table className="preview-table" style={{ width: '100%', fontSize: '0.86rem' }}>
                <thead>
                  <tr>
                    <th style={{ width: '45px', textAlign: 'center' }}>#</th>
                    {dataset.columns.map((col) => (
                      <th key={col}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span>{col}</span>
                          <span style={{ fontSize: '0.68rem', opacity: 0.6, fontWeight: 400 }}>
                            {dataset.numeric_columns.includes(col) ? '(num)' : '(str)'}
                          </span>
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {tableSearch ? (
                    dataset.sample_data
                      .filter((row) =>
                        Object.values(row).some((val) =>
                          String(val).toLowerCase().includes(tableSearch.toLowerCase())
                        )
                      )
                      .map((row, idx) => (
                        <tr key={idx}>
                          <td style={{ textAlign: 'center', opacity: 0.5, fontFamily: 'var(--font-mono)' }}>
                            {row._row_idx || idx + 1}
                          </td>
                          {dataset.columns.map((col) => (
                            <td key={col} style={{ fontFamily: dataset.numeric_columns.includes(col) ? 'var(--font-mono)' : 'inherit' }}>
                              {String(row[col])}
                            </td>
                          ))}
                        </tr>
                      ))
                  ) : (
                    <>
                      {(dataset.head_rows || dataset.sample_data || []).map((row, idx) => (
                        <tr key={`f-head-${idx}`}>
                          <td style={{ textAlign: 'center', opacity: 0.6, fontFamily: 'var(--font-mono)' }}>
                            {row._row_idx || idx + 1}
                          </td>
                          {dataset.columns.map((col) => (
                            <td key={col} style={{ fontFamily: dataset.numeric_columns.includes(col) ? 'var(--font-mono)' : 'inherit' }}>
                              {String(row[col])}
                            </td>
                          ))}
                        </tr>
                      ))}

                      {dataset.has_ellipsis && (
                        <tr>
                          <td
                            colSpan={dataset.columns.length + 1}
                            style={{
                              textAlign: 'center',
                              padding: '10px',
                              background: 'rgba(99, 102, 241, 0.12)',
                              color: 'var(--accent-primary-light)',
                              fontFamily: 'var(--font-mono)',
                              fontSize: '0.82rem',
                              fontWeight: 600,
                              letterSpacing: '0.08em'
                            }}
                          >
                            •••••• {dataset.hidden_count.toLocaleString()} rows hidden in between ••••••
                          </td>
                        </tr>
                      )}

                      {(dataset.tail_rows || []).map((row, idx) => (
                        <tr key={`f-tail-${idx}`}>
                          <td style={{ textAlign: 'center', opacity: 0.6, fontFamily: 'var(--font-mono)' }}>
                            {row._row_idx || dataset.row_count - 10 + idx + 1}
                          </td>
                          {dataset.columns.map((col) => (
                            <td key={col} style={{ fontFamily: dataset.numeric_columns.includes(col) ? 'var(--font-mono)' : 'inherit' }}>
                              {String(row[col])}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
