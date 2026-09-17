import React from 'react';
import { Sliders, Layers, Shuffle, Palette, Sparkles, ChevronDown, Check } from 'lucide-react';
import { THEME_STYLES, PALETTE_GROUPS, PALETTES, QUICK_PRESETS } from '../constants/themeOptions';

export default function AestheticsStudio({
  selectedStyle,
  selectedPalette,
  handleStyleChange,
  handlePaletteChange,
  handleRandomStyle,
  isStyleOpen,
  setIsStyleOpen,
  isPaletteOpen,
  setIsPaletteOpen,
  isRestyling,
  styleBoxRef,
  paletteBoxRef
}) {
  const currentStyleObj = THEME_STYLES.find((s) => s.id === selectedStyle);
  const currentPaletteObj = PALETTES.find((p) => p.id === selectedPalette);

  return (
    <div className="style-studio-card">
      {/* Studio Header */}
      <div className="studio-header">
        <div className="studio-header-title">
          <Sliders size={14} className="studio-header-icon" aria-hidden="true" />
          <span>Aesthetics Lab // Vibe Check 🎨</span>
        </div>

        <div className="studio-header-right">
          {/* Active Preset Preview Badge */}
          <div className="studio-active-badge" title="Currently active theme and color palette">
            <span className="active-badge-label">Active:</span>
            <span className="active-badge-val">
              <span className="active-badge-icon">{currentStyleObj?.icon}</span>
              <span>{currentStyleObj?.label || selectedStyle}</span>
            </span>
            <span className="active-badge-divider">•</span>
            <span className="active-badge-val">
              <span className="palette-dots mini" aria-hidden="true">
                {currentPaletteObj?.colors.map((c, i) => (
                  <span key={i} className="preview-dot" style={{ backgroundColor: c }} />
                ))}
              </span>
              <span>{currentPaletteObj?.label || selectedPalette}</span>
            </span>
            {isRestyling && (
              <span className="bouncing-dots inline">
                <span className="dot dot-1"></span>
                <span className="dot dot-2"></span>
                <span className="dot dot-3"></span>
              </span>
            )}
          </div>

          {/* Dual Toggle Button: Open / Close Both Menus */}
          <button
            type="button"
            className="studio-tool-btn"
            onClick={() => {
              const bothOpen = !(isStyleOpen && isPaletteOpen);
              setIsStyleOpen(bothOpen);
              setIsPaletteOpen(bothOpen);
            }}
            title="Toggle both Theme and Palette menus simultaneously"
          >
            <Layers size={12} />
            <span>{isStyleOpen && isPaletteOpen ? 'Close Menus' : 'Customize Both'}</span>
          </button>

          {/* Surprise Me / Randomize Button */}
          <button
            type="button"
            className="studio-tool-btn surprise-btn"
            onClick={handleRandomStyle}
            disabled={isRestyling}
            title="Roll random aesthetic style and color palette combination"
          >
            <Shuffle size={12} className={isRestyling ? 'spin' : ''} />
            <span>🎲 ROLL VIBE</span>
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

      {/* Selection Controls Grid: Dual Custom Dropdowns */}
      <div className="studio-selection-grid">
        {/* Select 1: Theme & Style */}
        <div className="select-control-box" ref={styleBoxRef}>
          <div className="select-control-header">
            <label className="select-control-label">
              <Palette size={13} className="studio-icon" aria-hidden="true" />
              <span>Theme & Base Style</span>
            </label>
            <span className="current-select-tag">
              {currentStyleObj?.icon} {currentStyleObj?.label}
            </span>
          </div>
          <div className="custom-dropdown-container">
            <button
              type="button"
              className={`custom-dropdown-trigger ${isStyleOpen ? 'active' : ''}`}
              onClick={() => setIsStyleOpen((prev) => !prev)}
              aria-expanded={isStyleOpen}
            >
              <span className="trigger-label">
                <span className="trigger-icon">{currentStyleObj?.icon}</span>
                <span>
                  {currentStyleObj?.label} — {currentStyleObj?.desc}
                </span>
              </span>
              <ChevronDown size={14} className={`select-chevron ${isStyleOpen ? 'rotated' : ''}`} />
            </button>

            {/* Dropdown Menu */}
            {isStyleOpen && (
              <div className="custom-dropdown-menu" role="menu">
                {THEME_STYLES.map((st) => (
                  <button
                    key={st.id}
                    type="button"
                    className={`custom-dropdown-item ${selectedStyle === st.id ? 'selected' : ''}`}
                    onClick={() => {
                      handleStyleChange(st.id);
                      setIsStyleOpen(false);
                    }}
                    role="menuitem"
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
              <Sparkles size={13} className="studio-icon" aria-hidden="true" />
              <span>Color Palette</span>
            </label>
            <span className="palette-swatch-badge">
              {currentPaletteObj?.colors.map((c, i) => (
                <span key={i} className="swatch-bar" style={{ backgroundColor: c }} />
              ))}
              <span className="palette-swatch-name">{currentPaletteObj?.label}</span>
            </span>
          </div>
          <div className="custom-dropdown-container">
            <button
              type="button"
              className={`custom-dropdown-trigger ${isPaletteOpen ? 'active' : ''}`}
              onClick={() => setIsPaletteOpen((prev) => !prev)}
              aria-expanded={isPaletteOpen}
            >
              <span className="trigger-label">
                <span className="palette-dots" aria-hidden="true">
                  {currentPaletteObj?.colors.map((c, i) => (
                    <span key={i} className="preview-dot" style={{ backgroundColor: c }} />
                  ))}
                </span>
                <span>
                  {currentPaletteObj?.label} ({currentPaletteObj?.desc})
                </span>
              </span>
              <ChevronDown size={14} className={`select-chevron ${isPaletteOpen ? 'rotated' : ''}`} />
            </button>

            {/* Dropdown Menu */}
            {isPaletteOpen && (
              <div className="custom-dropdown-menu palette-menu" role="menu">
                {PALETTE_GROUPS.map((grp) => (
                  <div key={grp.group} className="palette-group-section">
                    <div className="palette-group-header">{grp.group}</div>
                    <div className="palette-group-items">
                      {grp.palettes.map((pal) => (
                        <button
                          key={pal.id}
                          type="button"
                          className={`custom-dropdown-item ${selectedPalette === pal.id ? 'selected' : ''}`}
                          onClick={() => {
                            handlePaletteChange(pal.id);
                            setIsPaletteOpen(false);
                          }}
                          role="menuitem"
                        >
                          <div className="item-main">
                            <div className="palette-dots" aria-hidden="true">
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

      {/* Curated Presets Row */}
      <div className="studio-presets-row">
        <span className="presets-label">Quick Presets:</span>
        <div className="presets-pills">
          {QUICK_PRESETS.map((preset, idx) => (
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
  );
}
