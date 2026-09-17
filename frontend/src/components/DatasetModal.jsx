import React, { useEffect, useMemo } from 'react';
import { Database, X, Search } from 'lucide-react';

export default function DatasetModal({
  dataset,
  isOpen,
  onClose,
  tableSearch,
  setTableSearch
}) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  const searchLower = (tableSearch || '').trim().toLowerCase();
  const rowsToDisplay = useMemo(() => {
    if (!searchLower) return dataset?.sample_data || [];
    return (dataset?.sample_data || []).filter((row) =>
      Object.values(row).some((val) =>
        String(val ?? '').toLowerCase().includes(searchLower)
      )
    );
  }, [dataset?.sample_data, searchLower]);

  if (!isOpen || !dataset) return null;

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true" aria-label="Fullscreen Dataset Inspector">
      <div className="modal-content dataset-modal-box" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="dataset-modal-header">
          <div className="dataset-modal-title-group">
            <Database className="panel-icon" size={18} aria-hidden="true" />
            <div>
              <h3 className="modal-heading">Dataset Fullscreen Inspector</h3>
              <div className="modal-subheading">
                {dataset.row_count != null ? dataset.row_count.toLocaleString() : 0} Total Rows • {dataset.column_count ?? dataset.columns?.length ?? 0} Columns •{' '}
                {dataset.numeric_columns?.length ?? 0} Numeric Features
              </div>
            </div>
          </div>

          <div className="dataset-modal-controls">
            <div className="table-search-input-wrap">
              <Search size={13} className="search-icon" aria-hidden="true" />
              <input
                type="text"
                placeholder="Filter records..."
                value={tableSearch}
                onChange={(e) => setTableSearch(e.target.value)}
                className="table-search-input"
                aria-label="Filter dataset records"
              />
              {tableSearch && (
                <button
                  type="button"
                  className="search-clear-btn"
                  onClick={() => setTableSearch('')}
                  title="Clear filter"
                >
                  <X size={11} />
                </button>
              )}
            </div>

            <button
              className="modal-close"
              onClick={onClose}
              aria-label="Close Inspector"
              type="button"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Scrollable Full Table */}
        <div className="dataset-modal-table-wrap">
          <table className="preview-table full-modal-table">
            <thead>
              <tr>
                <th style={{ width: '50px', textAlign: 'center' }}>#</th>
                {(dataset.columns || []).map((col) => (
                  <th key={col}>
                    <div className="col-th-inner">
                      <span>{col}</span>
                      <span className="col-th-badge">
                        {dataset.numeric_columns?.includes(col) ? '(num)' : '(str)'}
                      </span>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rowsToDisplay.length === 0 ? (
                <tr>
                  <td colSpan={(dataset.columns?.length || 0) + 1} style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)' }}>
                    No rows match query "{tableSearch}"
                  </td>
                </tr>
              ) : (
                rowsToDisplay.map((row, idx) => (
                  <tr key={idx}>
                    <td style={{ textAlign: 'center', opacity: 0.5, fontFamily: 'var(--font-mono)' }}>
                      {row._row_idx || idx + 1}
                    </td>
                    {(dataset.columns || []).map((col) => (
                      <td
                        key={col}
                        className={dataset.numeric_columns?.includes(col) ? 'mono-cell' : ''}
                      >
                        {String(row[col] ?? '')}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
