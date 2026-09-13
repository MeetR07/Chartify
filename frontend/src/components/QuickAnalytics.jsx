import React from 'react';
import { Zap, ArrowUpRight } from 'lucide-react';
import { PROMPT_CATEGORIES } from '../constants/themeOptions';

export default function QuickAnalytics({
  chips,
  promptCategory,
  setPromptCategory,
  onChipClick,
  loading
}) {
  const filteredChips =
    promptCategory === 'all'
      ? chips
      : chips.filter((c) => c.category === promptCategory);

  return (
    <div className="quick-prompt-section">
      <div className="prompt-section-header">
        <div className="section-subtitle">
          <Zap size={14} className="zap-icon" />
          <span>Quick Analytics</span>
        </div>
        <span className="prompt-count-pill" title={`${filteredChips.length} smart prompts available`}>
          {filteredChips.length}
        </span>
      </div>

      {/* Category Filter Tabs */}
      <div className="prompt-category-tabs" role="tablist">
        {PROMPT_CATEGORIES.map((cat) => (
          <button
            key={cat.id}
            className={`cat-tab-btn ${promptCategory === cat.id ? 'active' : ''}`}
            onClick={() => setPromptCategory(cat.id)}
            type="button"
            role="tab"
            aria-selected={promptCategory === cat.id}
          >
            <span className="cat-tab-icon" aria-hidden="true">{cat.icon}</span>
            <span>{cat.label}</span>
          </button>
        ))}
      </div>

      {/* Dynamic Prompt Cards */}
      <div className="prompt-cards-container">
        {filteredChips.map((chip, idx) => (
          <button
            key={idx}
            className="prompt-card"
            onClick={() => onChipClick(chip.query)}
            disabled={loading}
            title={chip.query}
            type="button"
          >
            <div
              className="prompt-card-icon-badge"
              style={{
                background: `${chip.accent}16`,
                borderColor: `${chip.accent}35`,
                color: chip.accent
              }}
              aria-hidden="true"
            >
              <span>{chip.icon}</span>
            </div>
            <div className="prompt-card-info">
              <div className="prompt-card-top-line">
                <span className="prompt-card-title">{chip.title}</span>
                <span
                  className="prompt-card-tag"
                  style={{
                    background: `${chip.accent}14`,
                    color: chip.accent,
                    borderColor: `${chip.accent}28`
                  }}
                >
                  {chip.tag}
                </span>
              </div>
              <span className="prompt-card-desc">{chip.desc}</span>
            </div>
            <div className="prompt-card-arrow" aria-hidden="true">
              <ArrowUpRight size={13} />
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
