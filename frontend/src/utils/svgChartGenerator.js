/**
 * Generates an in-memory 2D SVG data URL for any chart type and dataset.
 * Ensures the 2D PNG view NEVER displays a broken image icon.
 */

const PALETTES = {
  butter_green: ['#013E37', '#FFEFB3', '#08ab9c', '#f47a34', '#fc6eae', '#ffbd29'],
  vibrant: ['#6366F1', '#06B6D4', '#10B981', '#F59E0B', '#EC4899', '#8B5CF6'],
  cyberpunk: ['#00F2FE', '#4FACFE', '#FF007F', '#7928CA', '#FF4B4B', '#00DFD8'],
  emerald: ['#10B981', '#059669', '#047857', '#34D399', '#6EE7B7', '#065F46'],
  sunset: ['#F43F5E', '#FB923C', '#FBBF24', '#F472B6', '#C084FC', '#E11D48'],
  ocean: ['#0EA5E9', '#38BDF8', '#0284C7', '#6366F1', '#7DD3FC', '#0369A1'],
  viridis: ['#440154', '#3b528b', '#21918c', '#5ec962', '#fde725'],
  plasma: ['#0d0887', '#6a00a8', '#b12a90', '#e16462', '#fca636', '#f0f921'],
  magma: ['#000004', '#3b0f70', '#8c2981', '#de4968', '#fe9f6d', '#fcfdbf']
};

export function generateClient2DChartSvg(activeChart, dataset) {
  const chartType = (activeChart?.chart_type || activeChart?.args?.chart_type || 'bar').toLowerCase();
  const title = activeChart?.title || `${chartType.toUpperCase()} Chart`;
  const paletteKey = activeChart?.args?.palette || 'butter_green';
  const colors = PALETTES[paletteKey] || PALETTES.butter_green;
  const isDark = (activeChart?.args?.style || '').includes('dark');

  const bg = isDark ? '#081720' : '#FFFDF0';
  const textColor = isDark ? '#F1F5F9' : '#013E37';
  const gridColor = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(1,62,55,0.1)';
  const subColor = isDark ? '#94A3B8' : '#3D736C';

  const width = 800;
  const height = 480;
  const margin = { top: 60, right: 40, bottom: 60, left: 70 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;

  // Extract data rows
  const rows = dataset?.sample_data || dataset?.head_rows || [
    { label: 'Jan', value: 15000 },
    { label: 'Feb', value: 22000 },
    { label: 'Mar', value: 18000 },
    { label: 'Apr', value: 27000 },
    { label: 'May', value: 31000 }
  ];

  const xCol = activeChart?.args?.x_col || dataset?.categorical_columns?.[0] || dataset?.columns?.[0] || Object.keys(rows[0] || {})[0];
  const yCol = activeChart?.args?.y_col || dataset?.numeric_columns?.[0] || dataset?.columns?.[1] || Object.keys(rows[0] || {})[1];

  // Aggregate or take top 10 items
  const items = rows.slice(0, 10).map((r, i) => {
    const rawVal = r[yCol] ?? r.value ?? (i + 1) * 10;
    const num = typeof rawVal === 'number' ? rawVal : parseFloat(rawVal) || 0;
    const label = String(r[xCol] ?? r.label ?? `Item ${i + 1}`);
    return { label, value: num };
  });

  const maxVal = Math.max(...items.map((it) => it.value), 10);
  const minVal = Math.min(...items.map((it) => it.value), 0);
  const range = maxVal - minVal || 1;

  let plotContent = '';

  if (chartType === 'pie' || chartType === 'donut') {
    // Render Donut / Pie
    const cx = width / 2;
    const cy = height / 2 + 10;
    const outerRadius = 140;
    const innerRadius = chartType === 'donut' ? 70 : 0;
    const total = items.reduce((acc, it) => acc + Math.max(0, it.value), 0) || 1;

    let startAngle = 0;
    items.forEach((it, idx) => {
      const sliceAngle = (Math.max(0, it.value) / total) * 2 * Math.PI;
      const endAngle = startAngle + sliceAngle;
      const col = colors[idx % colors.length];

      const x1 = cx + outerRadius * Math.cos(startAngle);
      const y1 = cy + outerRadius * Math.sin(startAngle);
      const x2 = cx + outerRadius * Math.cos(endAngle);
      const y2 = cy + outerRadius * Math.sin(endAngle);

      const x3 = cx + innerRadius * Math.cos(endAngle);
      const y3 = cy + innerRadius * Math.sin(endAngle);
      const x4 = cx + innerRadius * Math.cos(startAngle);
      const y4 = cy + innerRadius * Math.sin(startAngle);

      const largeArc = sliceAngle > Math.PI ? 1 : 0;
      const d = innerRadius > 0
        ? `M ${x1} ${y1} A ${outerRadius} ${outerRadius} 0 ${largeArc} 1 ${x2} ${y2} L ${x3} ${y3} A ${innerRadius} ${innerRadius} 0 ${largeArc} 0 ${x4} ${y4} Z`
        : `M ${cx} ${cy} L ${x1} ${y1} A ${outerRadius} ${outerRadius} 0 ${largeArc} 1 ${x2} ${y2} Z`;

      plotContent += `<path d="${d}" fill="${col}" stroke="${bg}" stroke-width="2"><title>${it.label}: ${it.value}</title></path>`;
      startAngle = endAngle;
    });
  } else if (chartType === 'line' || chartType === 'area') {
    // Render Line or Area
    const stepX = plotWidth / (items.length - 1 || 1);
    const points = items.map((it, i) => {
      const x = margin.left + i * stepX;
      const y = margin.top + plotHeight - ((it.value - minVal) / range) * plotHeight;
      return { x, y, ...it };
    });

    const pathD = points.reduce((acc, p, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`, '');
    const col = colors[0];

    if (chartType === 'area') {
      const areaD = `${pathD} L ${points[points.length - 1].x} ${margin.top + plotHeight} L ${points[0].x} ${margin.top + plotHeight} Z`;
      plotContent += `<path d="${areaD}" fill="${col}" fill-opacity="0.25" />`;
    }

    plotContent += `<path d="${pathD}" fill="none" stroke="${col}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />`;

    // Data points & labels
    points.forEach((p, idx) => {
      plotContent += `<circle cx="${p.x}" cy="${p.y}" r="6" fill="${colors[idx % colors.length]}" stroke="${bg}" stroke-width="2" />`;
      plotContent += `<text x="${p.x}" y="${margin.top + plotHeight + 22}" fill="${subColor}" font-size="11" font-weight="600" text-anchor="middle">${p.label}</text>`;
      plotContent += `<text x="${p.x}" y="${p.y - 12}" fill="${textColor}" font-size="11" font-weight="700" text-anchor="middle">${p.value}</text>`;
    });
  } else {
    // Render Default Bar / Histogram / Column
    const barWidth = Math.min(plotWidth / items.length * 0.65, 54);
    const stepX = plotWidth / items.length;

    items.forEach((it, idx) => {
      const barHeight = Math.max(8, ((it.value - minVal) / range) * (plotHeight - 30));
      const x = margin.left + idx * stepX + (stepX - barWidth) / 2;
      const y = margin.top + plotHeight - barHeight;
      const col = colors[idx % colors.length];

      plotContent += `
        <rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" rx="6" fill="${col}" opacity="0.92">
          <title>${it.label}: ${it.value}</title>
        </rect>
        <text x="${x + barWidth / 2}" y="${y - 8}" fill="${textColor}" font-size="11" font-weight="800" text-anchor="middle">${it.value}</text>
        <text x="${x + barWidth / 2}" y="${margin.top + plotHeight + 22}" fill="${subColor}" font-size="11" font-weight="600" text-anchor="middle">${it.label.length > 8 ? it.label.slice(0, 7) + '…' : it.label}</text>
      `;
    });
  }

  // Build gridlines
  let gridLines = '';
  for (let i = 0; i <= 4; i++) {
    const y = margin.top + (plotHeight / 4) * i;
    const val = Math.round(maxVal - (range / 4) * i);
    gridLines += `
      <line x1="${margin.left}" y1="${y}" x2="${width - margin.right}" y2="${y}" stroke="${gridColor}" stroke-dasharray="3,3" />
      <text x="${margin.left - 10}" y="${y + 4}" fill="${subColor}" font-size="10" font-weight="600" text-anchor="end">${val}</text>
    `;
  }

  const svgString = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}" style="background: ${bg}; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
      <!-- Background Rect -->
      <rect width="${width}" height="${height}" fill="${bg}" rx="12" />
      
      <!-- Title -->
      <text x="${margin.left}" y="36" fill="${textColor}" font-size="18" font-weight="800" letter-spacing="-0.02em">${title}</text>
      <text x="${margin.left}" y="52" fill="${subColor}" font-size="11" font-weight="600">${chartType.toUpperCase()} • ${yCol} across ${xCol}</text>
      
      <!-- Grid -->
      ${gridLines}
      
      <!-- Plot -->
      ${plotContent}
    </svg>
  `.trim();

  return `data:image/svg+xml;utf8,${encodeURIComponent(svgString)}`;
}
