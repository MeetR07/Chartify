import React from 'react';
import { Sparkles, X, RefreshCw, Send } from 'lucide-react';

export default function PromptHeroBar({
  query,
  setQuery,
  loading,
  handleGenerate,
  inputRef
}) {
  return (
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
          <div className="prompt-orb" aria-hidden="true">
            <Sparkles className="prompt-icon" size={14} />
          </div>
          <span className="prompt-hub-tag">AI Query</span>
        </div>

        {/* Input */}
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
          aria-label="Natural language query for chart generation"
        />

        {/* Clear Button */}
        {query && !loading && (
          <button
            type="button"
            className="prompt-clear-btn"
            onClick={() => {
              setQuery('');
              if (inputRef.current) inputRef.current.focus();
            }}
            title="Clear prompt"
            aria-label="Clear prompt"
          >
            <X size={13} />
          </button>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          className="submit-btn"
          disabled={loading || !query.trim()}
          aria-label="Generate Chart"
        >
          {loading ? (
            <>
              <RefreshCw size={15} className="spin" />
              <span>Analyzing...</span>
            </>
          ) : (
            <>
              <span>Generate Chart</span>
              <Send size={14} />
              <kbd className="prompt-enter-kbd" title="Press Enter to generate">↵</kbd>
            </>
          )}
        </button>
      </form>
    </div>
  );
}
