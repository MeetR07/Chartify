import React, { useRef, useEffect } from 'react';
import { Sparkles, X, RefreshCw, Flame, ChevronDown, Search, Paperclip, ArrowRight } from 'lucide-react';

const CHART_TYPES = [
  { value: '', label: 'All Charts (Auto)' },
  { value: 'column', label: 'Vertical Bar (Column)' },
  { value: 'bar', label: 'Horizontal Bar' },
  { value: 'line', label: 'Line Chart' },
  { value: 'scatter', label: 'Scatter Plot' },
  { value: 'histogram', label: 'Histogram' },
  { value: 'box', label: 'Box Plot' },
  { value: 'heatmap', label: 'Heatmap' },
  { value: 'pie', label: 'Pie Chart' },
  { value: 'donut', label: 'Donut Chart' },
  { value: 'area', label: 'Area Chart' },
  { value: 'violin', label: 'Violin Plot' },
  { value: 'treemap', label: 'Treemap' },
  { value: 'waterfall', label: 'Waterfall' },
  { value: 'funnel', label: 'Funnel Chart' },
  { value: 'lollipop', label: 'Lollipop' },
  { value: 'radar', label: 'Radar Chart' },
  { value: 'bubble', label: 'Bubble Chart' },
  { value: 'pairplot', label: 'Pairplot' }
];

export default function PromptHeroBar({
  query,
  setQuery,
  selectedChartType = '',
  onSelectChartType = () => {},
  loading,
  handleGenerate,
  inputRef,
  handleFileUpload,
  uploading = false
}) {
  const fileInputRef = useRef(null);

  const activeLabel = selectedChartType
    ? `${selectedChartType.toUpperCase()} CHART`
    : (
        <>
          ALL CHARTS <span className="hide-on-mobile">(AUTO)</span>
        </>
      );

  return (
    <div className="prompt-bar-wrapper">
      {/* Hidden File Input for Paperclip Upload */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv"
        onChange={(e) => {
          if (handleFileUpload) handleFileUpload(e);
          e.target.value = '';
        }}
        style={{ display: 'none' }}
      />

      <form
        className="prompt-bar-container stacked-layout"
        onSubmit={(e) => {
          e.preventDefault();
          handleGenerate();
        }}
      >
        {/* Input */}
        <textarea
          ref={inputRef}
          className="prompt-input prompt-textarea"
          placeholder="Ask anything, @ to mention, / for actions"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              if (query.trim() || selectedChartType) {
                handleGenerate();
              }
            }
          }}
          disabled={loading}
          autoComplete="off"
          spellCheck="false"
          aria-label="Natural language query for chart generation"
          rows={1}
        />

        {/* Action Row */}
        <div className="prompt-action-row">
          <div className="prompt-actions-left">
            {/* Attachment Paperclip Button (now + icon) */}
            <button
              type="button"
              className="prompt-attach-btn"
              onClick={() => fileInputRef.current?.click()}
              title="Attach / Upload CSV dataset"
              aria-label="Upload CSV dataset"
              disabled={uploading || loading}
            >
              {uploading ? <RefreshCw size={16} className="spin" /> : <span style={{ fontSize: '18px', fontWeight: '300' }}>+</span>}
            </button>

            {/* Left Chart Type Select Pill */}
            <div className="prompt-left-badge" title="Select Chart Type">
              <Sparkles size={14} className="prompt-badge-sparkle" aria-hidden="true" />
              <span className="prompt-badge-text">{activeLabel}</span>
              <ChevronDown size={13} className="select-chevron" aria-hidden="true" />
              <select
                className="chart-type-select"
                value={selectedChartType}
                onChange={(e) => onSelectChartType(e.target.value)}
                disabled={loading}
                aria-label="Select Chart Type"
              >
                {CHART_TYPES.map((ct) => (
                  <option key={ct.value} value={ct.value}>
                    {ct.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="prompt-actions-right">
            {/* Cook Chart Submit Button */}
            <button
              type="submit"
              className="submit-btn"
              disabled={loading || (!query.trim() && !selectedChartType)}
              aria-label="Cook Chart"
            >
              {loading ? (
                <>
                  <RefreshCw size={14} className="spin" />
                  <span className="submit-btn-text">COOKING...</span>
                </>
              ) : (
                <>
                  <Flame size={15} className="submit-btn-flame" />
                  <span className="submit-btn-text">COOK CHART</span>
                  <ArrowRight size={15} className="submit-btn-arrow" />
                </>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
