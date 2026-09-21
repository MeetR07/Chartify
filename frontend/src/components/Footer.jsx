import React from 'react';

export default function Footer() {
  return (
    <footer className="page-footer" role="contentinfo">
      <div className="footer-content">
        <div className="footer-left">
          <span className="footer-brand">Chartify AI Studio // Gen-Z Edition ✦</span>
          <span className="footer-sep" aria-hidden="true">•</span>
          <span className="footer-desc">Autonomous AI Data Visualization & Analytics Engine</span>
        </div>
        <div className="footer-right">
          <span className="footer-providers">Multi-Provider Cascade: Gemini • Mistral • Groq LPU</span>
          <span className="footer-sep" aria-hidden="true">•</span>
          <span className="footer-badge">⚡ ALL SYSTEMS GO</span>
        </div>
      </div>
    </footer>
  );
}

