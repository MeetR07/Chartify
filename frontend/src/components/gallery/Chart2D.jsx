import React from 'react';

export default function Chart2D({ chartType, data, onHover }) {
  switch (chartType) {
    case 'radar':
      return <Radar2D data={data} onHover={onHover} />;
    case 'lollipop':
      return <Lollipop2D data={data} onHover={onHover} />;
    case 'waterfall':
      return <Waterfall2D data={data} onHover={onHover} />;
    case 'treemap':
      return <Treemap2D data={data} onHover={onHover} />;
    case 'violin':
      return <Violin2D data={data} onHover={onHover} />;
    case 'area':
      return <Area2D data={data} onHover={onHover} />;
    case 'donut':
      return <Donut2D data={data} onHover={onHover} />;
    case 'pie':
      return <Pie2D data={data} onHover={onHover} />;
    default:
      return <div className="chart-2d-fallback">2D Preview Available</div>;
  }
}

/** 2D Radar SVG */
function Radar2D({ data, onHover }) {
  const size = 300;
  const center = size / 2;
  const radius = 105;
  const numAxes = data.length;
  const angleStep = (Math.PI * 2) / numAxes;

  const points = data.map((d, i) => {
    const a = i * angleStep - Math.PI / 2;
    const r = (d.value / d.fullMark) * radius;
    return `${center + Math.cos(a) * r},${center + Math.sin(a) * r}`;
  }).join(' ');

  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="gallery-svg-canvas">
      {/* Background web rings */}
      {[0.25, 0.5, 0.75, 1.0].map((lvl, li) => {
        const ringPts = data.map((_, i) => {
          const a = i * angleStep - Math.PI / 2;
          const r = radius * lvl;
          return `${center + Math.cos(a) * r},${center + Math.sin(a) * r}`;
        }).join(' ');
        return (
          <polygon
            key={li}
            points={ringPts}
            fill="none"
            stroke="#013e37"
            strokeOpacity={lvl === 1.0 ? 0.35 : 0.15}
            strokeWidth="1.2"
          />
        );
      })}

      {/* Axis lines & Labels */}
      {data.map((d, i) => {
        const a = i * angleStep - Math.PI / 2;
        const x2 = center + Math.cos(a) * radius;
        const y2 = center + Math.sin(a) * radius;
        const tx = center + Math.cos(a) * (radius + 18);
        const ty = center + Math.sin(a) * (radius + 18);
        return (
          <g key={i}>
            <line x1={center} y1={center} x2={x2} y2={y2} stroke="#013e37" strokeOpacity="0.25" strokeWidth="1" />
            <text x={tx} y={ty + 4} textAnchor="middle" fontSize="10" fontWeight="700" fill="#013E37">
              {d.axis}
            </text>
          </g>
        );
      })}

      {/* Filled Area */}
      <polygon points={points} fill="#08ab9c" fillOpacity="0.45" stroke="#08ab9c" strokeWidth="2.5" />

      {/* Interactive Vertices */}
      {data.map((d, i) => {
        const a = i * angleStep - Math.PI / 2;
        const r = (d.value / d.fullMark) * radius;
        const cx = center + Math.cos(a) * r;
        const cy = center + Math.sin(a) * r;
        return (
          <circle
            key={i}
            cx={cx}
            cy={cy}
            r="4.5"
            fill="#013E37"
            stroke="#FFEFB3"
            strokeWidth="2"
            onMouseEnter={(e) => onHover?.({ name: d.axis, category: '2D Axis', value: d.value, color: '#08ab9c' }, { x: cx, y: cy })}
            onMouseLeave={() => onHover?.(null)}
          />
        );
      })}
    </svg>
  );
}

/** 2D Lollipop SVG */
function Lollipop2D({ data, onHover }) {
  const w = 340;
  const h = 220;
  const padL = 40;
  const padB = 40;
  const chartW = w - padL - 20;
  const chartH = h - padB - 20;
  const maxVal = Math.max(...data.map((d) => d.value), 1);
  const step = chartW / data.length;

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="gallery-svg-canvas">
      {/* Ground baseline */}
      <line x1={padL - 10} y1={h - padB} x2={w - 10} y2={h - padB} stroke="#013e37" strokeWidth="1.5" />

      {data.map((d, i) => {
        const cx = padL + i * step + step / 2;
        const cy = (h - padB) - (d.value / maxVal) * chartH;
        const color = ['#013E37', '#08ab9c', '#f47a34', '#fc6eae', '#ffbd29', '#146665', '#38bdf8'][i % 7];

        return (
          <g
            key={i}
            onMouseEnter={() => onHover?.({ name: d.name, category: 'Lollipop', value: d.value, color }, { x: cx, y: cy })}
            onMouseLeave={() => onHover?.(null)}
          >
            <line x1={cx} y1={h - padB} x2={cx} y2={cy} stroke="#013e37" strokeWidth="2.5" />
            <circle cx={cx} cy={cy} r="6.5" fill={color} stroke="#013e37" strokeWidth="1.5" />
            <text x={cx} y={h - padB + 16} textAnchor="middle" fontSize="9" fontWeight="700" fill="#013E37">
              {d.name.slice(0, 5)}
            </text>
            <text x={cx} y={cy - 10} textAnchor="middle" fontSize="9" fontWeight="800" fill="#013E37">
              {d.value}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/** 2D Waterfall SVG */
function Waterfall2D({ data, onHover }) {
  const w = 340;
  const h = 220;
  const maxBal = 150;
  const padL = 30;
  const padB = 45;
  const chartW = w - padL - 15;
  const chartH = h - padB - 20;
  const step = chartW / data.length;
  const barW = step * 0.7;

  let current = 0;

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="gallery-svg-canvas">
      <line x1={padL - 10} y1={h - padB} x2={w - 10} y2={h - padB} stroke="#013e37" strokeWidth="1.5" />

      {data.map((d, i) => {
        let topY, bottomY, color;
        if (d.type === 'start' || d.type === 'total') {
          bottomY = h - padB;
          topY = (h - padB) - (d.balance / maxBal) * chartH;
          color = '#013E37';
          current = d.balance;
        } else if (d.type === 'positive') {
          bottomY = (h - padB) - (current / maxBal) * chartH;
          topY = (h - padB) - ((current + d.delta) / maxBal) * chartH;
          color = '#10b981';
          current += d.delta;
        } else {
          topY = (h - padB) - (current / maxBal) * chartH;
          bottomY = (h - padB) - ((current + d.delta) / maxBal) * chartH;
          color = '#f43f5e';
          current += d.delta;
        }

        const rectY = Math.min(topY, bottomY);
        const rectH = Math.max(Math.abs(topY - bottomY), 3);
        const cx = padL + i * step + (step - barW) / 2;

        return (
          <g
            key={i}
            onMouseEnter={() => onHover?.({ name: d.name, category: d.type.toUpperCase(), delta: d.delta, value: d.balance, color }, { x: cx + barW / 2, y: rectY })}
            onMouseLeave={() => onHover?.(null)}
          >
            <rect x={cx} y={rectY} width={barW} height={rectH} rx="3" fill={color} stroke="#013E37" strokeWidth="1" />
            <text x={cx + barW / 2} y={h - padB + 14} textAnchor="middle" fontSize="8" fontWeight="700" fill="#013E37">
              {d.name.split(' ')[0]}
            </text>
            <text x={cx + barW / 2} y={rectY - 5} textAnchor="middle" fontSize="8" fontWeight="800" fill={color}>
              {d.delta > 0 ? `+${d.delta}` : d.delta}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/** 2D Treemap SVG */
function Treemap2D({ data, onHover }) {
  const w = 320;
  const h = 200;

  const rects = [
    { x: 10,  y: 10,  w: 160, h: 100 },
    { x: 175, y: 10,  w: 135, h: 58 },
    { x: 175, y: 72,  w: 135, h: 38 },
    { x: 10,  y: 115, w: 95,  h: 75 },
    { x: 110, y: 115, w: 90,  h: 75 },
    { x: 205, y: 115, w: 105, h: 35 },
    { x: 205, y: 154, w: 105, h: 36 }
  ];

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="gallery-svg-canvas">
      {data.slice(0, rects.length).map((d, i) => {
        const r = rects[i];
        return (
          <g
            key={i}
            onMouseEnter={() => onHover?.({ name: d.name, category: 'Treemap 2D', value: d.value, color: d.color }, { x: r.x + r.w / 2, y: r.y + r.h / 2 })}
            onMouseLeave={() => onHover?.(null)}
          >
            <rect x={r.x} y={r.y} width={r.w} height={r.h} rx="4" fill={d.color} stroke="#013e37" strokeWidth="1.5" />
            <text x={r.x + 8} y={r.y + 18} fontSize="10" fontWeight="800" fill="#FFEFB3">
              {d.name.slice(0, 12)}
            </text>
            <text x={r.x + 8} y={r.y + 32} fontSize="9" fontWeight="700" fill="#FFEFB3" opacity="0.85">
              {d.value}M
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/** 2D Violin SVG */
function Violin2D({ data, onHover }) {
  const w = 320;
  const h = 200;
  const step = w / data.length;

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="gallery-svg-canvas">
      {data.map((cohort, i) => {
        const cx = i * step + step / 2;
        const color = ['#013E37', '#08ab9c', '#f47a34'][i % 3];

        return (
          <g
            key={i}
            onMouseEnter={() => onHover?.({ name: cohort.group, category: 'Median', value: `${cohort.median}%`, color }, { x: cx, y: 100 })}
            onMouseLeave={() => onHover?.(null)}
          >
            {/* Center spine */}
            <line x1={cx} y1={25} x2={cx} y2={175} stroke="#013E37" strokeWidth="1.5" />
            {/* Bilateral curves */}
            <path
              d={`M ${cx} 25 Q ${cx - 28} 80 ${cx - 10} 120 Q ${cx - 24} 150 ${cx} 175 Q ${cx + 24} 150 ${cx + 10} 120 Q ${cx + 28} 80 ${cx} 25 Z`}
              fill={color}
              fillOpacity="0.75"
              stroke="#013E37"
              strokeWidth="1.5"
            />
            {/* Median line */}
            <circle cx={cx} cy={100} r="4" fill="#FFEFB3" stroke="#013E37" strokeWidth="1.5" />
            <text x={cx} y={192} textAnchor="middle" fontSize="11" fontWeight="800" fill="#013E37">
              {cohort.group}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/** 2D Area SVG */
function Area2D({ data, onHover }) {
  const w = 320;
  const h = 200;
  const padL = 30;
  const padB = 30;
  const chartW = w - padL - 15;
  const chartH = h - padB - 20;
  const stepX = chartW / (data.labels.length - 1);

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="gallery-svg-canvas">
      <line x1={padL} y1={h - padB} x2={w - 10} y2={h - padB} stroke="#013E37" strokeWidth="1.2" />

      {data.series.map((s) => {
        const pts = s.values.map((v, i) => {
          const x = padL + i * stepX;
          const y = (h - padB) - (v / 100) * chartH;
          return `${x},${y}`;
        });
        const areaPath = `M ${padL},${h - padB} L ${pts.join(' L ')} L ${padL + chartW},${h - padB} Z`;

        return (
          <g key={s.name}>
            <path d={areaPath} fill={s.color} fillOpacity="0.35" stroke={s.color} strokeWidth="2.5" />
            {s.values.map((v, i) => (
              <circle
                key={i}
                cx={padL + i * stepX}
                cy={(h - padB) - (v / 100) * chartH}
                r="3"
                fill={s.color}
                onMouseEnter={() => onHover?.({ name: `${s.name} (${data.labels[i]})`, category: 'Area Trend', value: v, color: s.color }, { x: padL + i * stepX, y: (h - padB) - (v / 100) * chartH })}
                onMouseLeave={() => onHover?.(null)}
              />
            ))}
          </g>
        );
      })}
    </svg>
  );
}

/** 2D Donut SVG */
function Donut2D({ data, onHover }) {
  const size = 260;
  const center = size / 2;
  const r = 85;
  const innerR = 45;
  const total = data.reduce((sum, d) => sum + d.value, 0);

  let startAngle = 0;

  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="gallery-svg-canvas">
      {data.map((d, i) => {
        const angle = (d.value / total) * Math.PI * 2;
        const endAngle = startAngle + angle;

        const x1 = center + r * Math.cos(startAngle);
        const y1 = center + r * Math.sin(startAngle);
        const x2 = center + r * Math.cos(endAngle);
        const y2 = center + r * Math.sin(endAngle);

        const x3 = center + innerR * Math.cos(endAngle);
        const y3 = center + innerR * Math.sin(endAngle);
        const x4 = center + innerR * Math.cos(startAngle);
        const y4 = center + innerR * Math.sin(startAngle);

        const largeArc = angle > Math.PI ? 1 : 0;
        const dStr = `M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} L ${x3} ${y3} A ${innerR} ${innerR} 0 ${largeArc} 0 ${x4} ${y4} Z`;

        const mid = startAngle + angle / 2;
        const tooltipX = center + (r + innerR) / 2 * Math.cos(mid);
        const tooltipY = center + (r + innerR) / 2 * Math.sin(mid);

        startAngle = endAngle;

        return (
          <path
            key={i}
            d={dStr}
            fill={d.color}
            stroke="#FFFDF0"
            strokeWidth="2"
            onMouseEnter={() => onHover?.({ name: d.name, category: 'Donut Slice', value: d.value, percent: Math.round((d.value / total) * 100), color: d.color }, { x: tooltipX, y: tooltipY })}
            onMouseLeave={() => onHover?.(null)}
          />
        );
      })}
    </svg>
  );
}

/** 2D Pie SVG */
function Pie2D({ data, onHover }) {
  const size = 260;
  const center = size / 2;
  const r = 90;
  const total = data.reduce((sum, d) => sum + d.value, 0);

  let startAngle = 0;

  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="gallery-svg-canvas">
      {data.map((d, i) => {
        const angle = (d.value / total) * Math.PI * 2;
        const endAngle = startAngle + angle;

        const x1 = center + r * Math.cos(startAngle);
        const y1 = center + r * Math.sin(startAngle);
        const x2 = center + r * Math.cos(endAngle);
        const y2 = center + r * Math.sin(endAngle);

        const largeArc = angle > Math.PI ? 1 : 0;
        const dStr = `M ${center} ${center} L ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} Z`;

        const mid = startAngle + angle / 2;
        const tooltipX = center + (r * 0.6) * Math.cos(mid);
        const tooltipY = center + (r * 0.6) * Math.sin(mid);

        startAngle = endAngle;

        return (
          <path
            key={i}
            d={dStr}
            fill={d.color}
            stroke="#FFFDF0"
            strokeWidth="2"
            onMouseEnter={() => onHover?.({ name: d.name, category: 'Pie Wedge', value: d.value, percent: Math.round((d.value / total) * 100), color: d.color }, { x: tooltipX, y: tooltipY })}
            onMouseLeave={() => onHover?.(null)}
          />
        );
      })}
    </svg>
  );
}
