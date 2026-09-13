import React from 'react';
import { Database, Maximize2, RefreshCw, Upload } from 'lucide-react';

export default function DatasetInspector({
  dataset,
  fetchDataset,
  setDatasetModal,
  handleFileUpload,
  uploading,
  onColumnClick
}) {
  return (
    <div className="dataset-inspector-block">
      <div className="panel-header">
        <span className="panel-title">
          <Database className="panel-icon" size={17} />
          <span>Dataset Inspector</span>
        </span>
        <div className="panel-actions">
          <button
            onClick={() => setDatasetModal(true)}
            className="action-btn"
            title="Fullscreen Dataset Inspector"
            aria-label="Fullscreen Dataset Inspector"
            type="button"
          >
            <Maximize2 size={13} />
          </button>
          <button
            onClick={fetchDataset}
            className="action-btn"
            title="Refresh Dataset"
            aria-label="Refresh Dataset"
            type="button"
          >
            <RefreshCw size={13} />
          </button>
        </div>
      </div>

      {dataset ? (
        <>
          {/* Summary Stats Grid */}
          <div className="data-summary-bar">
            <div className="stat-box">
              <div className="stat-value">{dataset.row_count.toLocaleString()}</div>
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
                {(dataset.head_rows || dataset.sample_data || []).slice(0, 5).map((row, idx) => (
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
                      className="table-ellipsis-cell"
                    >
                      ••• {dataset.hidden_count.toLocaleString()} rows hidden •••
                    </td>
                  </tr>
                )}

                {(dataset.tail_rows || []).slice(-3).map((row, idx) => (
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
      ) : (
        <div className="dataset-empty-hint">Loading dataset preview...</div>
      )}

      {/* Upload Custom CSV Dropzone */}
      <label className={`upload-btn ${uploading ? 'uploading' : ''}`}>
        <Upload size={15} className={uploading ? 'spin' : ''} />
        <span>{uploading ? 'Processing Dataset...' : 'Upload Custom CSV Dataset'}</span>
        <input
          type="file"
          accept=".csv"
          style={{ display: 'none' }}
          onChange={handleFileUpload}
          disabled={uploading}
        />
      </label>
    </div>
  );
}
