import React from 'react';
import { Sparkles, Sun, Moon, Flame } from 'lucide-react';

export default function Navbar({ theme, setTheme, sessionTokens }) {
  return (
    <nav className="navbar" role="navigation" aria-label="Main Navigation">
      <div className="brand-section">
        <div className="logo-icon" aria-hidden="true">
          <Sparkles size={18} />
        </div>
        <div className="brand-info">
          <div className="brand-title-row">
            <span className="brand-title">Chartify</span>
          </div>
        </div>
      </div>

      <div className="nav-actions">


        <div className="token-pill" title="Tokens processed in current session">
          <Flame size={13} aria-hidden="true" />
          <span>{sessionTokens.toLocaleString()} Cooked</span>
        </div>

        <button
          onClick={() => setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'))}
          className="theme-toggle-btn"
          title={theme === 'dark' ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
          aria-label={theme === 'dark' ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
          type="button"
        >
          {theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
        </button>
      </div>
    </nav>
  );
}

