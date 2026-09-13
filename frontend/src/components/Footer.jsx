import React from 'react';

export default function Footer() {
  return (
    <footer className="page-footer" role="contentinfo">
      <div className="footer-content">
        <div className="footer-left">
          <span className="footer-brand">Chartify AI Studio</span>
          <span className="footer-sep" aria-hidden="true">•</span>
          <span className="footer-desc">Autonomous AI Data Visualization & Analytics Engine</span>
        </div>
        <div className="footer-right">
          <span>Multi-Provider Cascade: Gemini • Mistral • Groq LPU</span>
          <span className="footer-sep" aria-hidden="true">•</span>
          <span className="footer-badge">System Active</span>
        </div>
      </div>
    </footer>
  );
}
