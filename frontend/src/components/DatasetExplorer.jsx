import React from 'react';
import { Table as TableIcon, Maximize2 } from 'lucide-react';

export default function DatasetExplorer({
  dataset,
  setDatasetModal
}) {
  if (!dataset) return null;

  return (
    <section className="bottom-explorer-section">
      <div className="bottom-explorer-card glass-panel">
        <div className="panel-header">
          <div className="explorer-header-left">
            <TableIcon className="panel-icon" size={18} aria-hidden="true" />
            <div>
              <h3 className="explorer-title">
                Dataset Deep-Dive Explorer & Live Records Preview
              </h3>
              <div className="explorer-subtitle">
                {dataset.row_count.toLocaleString()} total rows • {dataset.column_count} columns (
                {dataset.numeric_columns.length} numeric,{' '}
                {dataset.columns.length - dataset.numeric_columns.length} categorical)
              </div>
            </div>
          </div>
          <button
            onClick={() => setDatasetModal(true)}
            className="action-btn"
            aria-label="Fullscreen Table Inspector"
            type="button"
          >
            <Maximize2 size={13} />
            <span>Fullscreen Inspector</span>
          </button>
        </div>

        <div className="bottom-table-container">
          <table className="preview-table deep-table">
            <thead>
              <tr>
                <th className="col-idx-header">#</th>
                {dataset.columns.map((col) => (
                  <th key={col}>
                    <div className="col-th-inner">
                      <span>{col}</span>
                      <span className="col-th-badge">
                        {dataset.numeric_columns.includes(col) ? '(num)' : '(str)'}
                      </span>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(dataset.head_rows || dataset.sample_data || []).slice(0, 8).map((row, idx) => (
                <tr key={`bot-head-${idx}`}>
                  <td className="row-num-cell">{idx + 1}</td>
                  {dataset.columns.map((col) => (
                    <td
                      key={col}
                      className={dataset.numeric_columns.includes(col) ? 'mono-cell' : ''}
                    >
                      {String(row[col])}
                    </td>
                  ))}
                </tr>
              ))}
              {dataset.has_ellipsis && (
                <tr>
                  <td
                    colSpan={dataset.columns.length + 1}
                    className="table-ellipsis-cell-deep"
                  >
                    •••••• {dataset.hidden_count.toLocaleString()} more rows available in dataset ••••••
                  </td>
                </tr>
              )}
              {(dataset.tail_rows || []).slice(-4).map((row, idx) => (
                <tr key={`bot-tail-${idx}`}>
                  <td className="row-num-cell">
                    {dataset.row_count - 4 + idx + 1}
                  </td>
                  {dataset.columns.map((col) => (
                    <td
                      key={col}
                      className={dataset.numeric_columns.includes(col) ? 'mono-cell' : ''}
                    >
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
  );
}
