/**
 * Fast, robust client-side CSV parser that extracts headers, data rows,
 * numeric/categorical type detection, and summary statistics.
 * Works 100% offline in browser without needing an external Python backend.
 */
export function parseCSVClientSide(csvText, filename = 'dataset.csv') {
  if (!csvText || typeof csvText !== 'string') {
    throw new Error('CSV content is empty.');
  }

  const lines = csvText.split(/\r\n|\n|\r/).filter((l) => l.trim().length > 0);
  if (lines.length < 2) {
    throw new Error('CSV file must have a header row and at least one data row.');
  }

  // Parse a CSV line taking quotes, double quotes, and commas into account
  const parseLine = (lineStr) => {
    const cells = [];
    let current = '';
    let inQuotes = false;
    for (let i = 0; i < lineStr.length; i++) {
      const char = lineStr[i];
      if (char === '"' || char === "'") {
        inQuotes = !inQuotes;
      } else if (char === ',' && !inQuotes) {
        cells.push(current.trim().replace(/^["']|["']$/g, ''));
        current = '';
      } else {
        current += char;
      }
    }
    cells.push(current.trim().replace(/^["']|["']$/g, ''));
    return cells;
  };

  const rawHeaders = parseLine(lines[0]);
  const headers = rawHeaders.map((h, idx) => (h && h.length > 0 ? h : `Feature_${idx + 1}`));

  const rows = [];
  for (let i = 1; i < lines.length; i++) {
    const values = parseLine(lines[i]);
    if (values.length === 0 || (values.length === 1 && values[0] === '')) continue;
    const rowObj = { _row_idx: i };
    headers.forEach((h, colIdx) => {
      const val = values[colIdx] !== undefined ? values[colIdx] : '';
      const num = Number(val);
      if (val !== '' && !isNaN(num)) {
        rowObj[h] = num;
      } else {
        rowObj[h] = val;
      }
    });
    rows.push(rowObj);
  }

  if (rows.length === 0) {
    throw new Error('No valid data records found in CSV.');
  }

  // Detect numeric vs categorical columns
  const numericCols = headers.filter((h) => rows.some((r) => typeof r[h] === 'number'));
  const catCols = headers.filter((h) => !numericCols.includes(h));

  const totalRows = rows.length;

  // Build describe stats for numeric columns
  const describeData = {};
  numericCols.forEach((col) => {
    const nums = rows.map((r) => r[col]).filter((v) => typeof v === 'number');
    if (nums.length > 0) {
      const sum = nums.reduce((a, b) => a + b, 0);
      const mean = +(sum / nums.length).toFixed(2);
      const min = Math.min(...nums);
      const max = Math.max(...nums);
      describeData[col] = { count: nums.length, mean, min, max };
    }
  });

  return {
    columns: headers,
    numeric_columns: numericCols,
    categorical_columns: catCols,
    row_count: totalRows,
    column_count: headers.length,
    head_rows: rows.slice(0, 10),
    tail_rows: totalRows > 20 ? rows.slice(-10) : [],
    has_ellipsis: totalRows > 20,
    hidden_count: Math.max(0, totalRows - 20),
    sample_data: rows.slice(0, 200),
    describe: describeData,
    filename: filename,
    success: true,
    message: `'${filename}' loaded — ${totalRows} rows, ${headers.length} columns.`
  };
}
