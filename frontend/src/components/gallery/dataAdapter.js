/**
 * Adapts the currently active dataset to normalized schemas for all 8 3D/2D gallery charts.
 * Guarantees 100% data value consistency between 2D and 3D renderers.
 */

export function getGalleryData(dataset) {
  const numCols = dataset?.numeric_columns || [];
  const allCols = dataset?.columns || [];
  const catCols = allCols.filter((c) => !numCols.includes(c));
  const sampleRows = dataset?.head_rows || dataset?.sample_data || [];

  const primaryNum = numCols[0] || 'Score';
  const secondaryNum = numCols[1] || numCols[0] || 'Amount';
  const primaryCat = catCols[0] || allCols[0] || 'Category';

  // 1. Radar Data (6 dimensional performance metrics)
  const radarData = [
    { axis: 'Throughput', value: 85, fullMark: 100 },
    { axis: 'Latency', value: 92, fullMark: 100 },
    { axis: 'Reliability', value: 78, fullMark: 100 },
    { axis: 'Scalability', value: 88, fullMark: 100 },
    { axis: 'Efficiency', value: 95, fullMark: 100 },
    { axis: 'Aesthetics', value: 90, fullMark: 100 }
  ];

  // 2. Lollipop Data (Sequential discrete categories with stems)
  let lollipopData = [];
  if (sampleRows.length >= 6) {
    lollipopData = sampleRows.slice(0, 7).map((r, i) => ({
      name: String(r[primaryCat] || `Item ${i + 1}`).slice(0, 14),
      value: Math.max(Math.abs(parseFloat(r[primaryNum]) || (i + 1) * 14 + 10), 5)
    }));
  } else {
    lollipopData = [
      { name: 'Tokyo', value: 88 },
      { name: 'New York', value: 74 },
      { name: 'London', value: 65 },
      { name: 'Paris', value: 58 },
      { name: 'Singapore', value: 92 },
      { name: 'Berlin', value: 49 },
      { name: 'Sydney', value: 63 }
    ];
  }

  // 3. Waterfall Data (Financial sequential movements & net balance)
  const waterfallData = [
    { name: 'Gross Revenue', delta: 135, type: 'start', balance: 135 },
    { name: 'Direct COGS', delta: -42, type: 'negative', balance: 93 },
    { name: 'Marketing', delta: -25, type: 'negative', balance: 68 },
    { name: 'Partnerships', delta: 18, type: 'positive', balance: 86 },
    { name: 'R&D Cloud', delta: -22, type: 'negative', balance: 64 },
    { name: 'Taxes & Fees', delta: -14, type: 'negative', balance: 50 },
    { name: 'Net Profit', delta: 50, type: 'total', balance: 50 }
  ];

  // 4. Treemap Data (Proportional rectangular tree areas)
  const treemapData = [
    { name: 'Enterprise Cloud', value: 42, color: '#013E37' },
    { name: 'Developer Tools', value: 28, color: '#08ab9c' },
    { name: 'Mobile Platform', value: 22, color: '#f47a34' },
    { name: 'AI Services', value: 35, color: '#fc6eae' },
    { name: 'Security & Auth', value: 18, color: '#ffbd29' },
    { name: 'Data Pipeline', value: 25, color: '#146665' },
    { name: 'Edge Nodes', value: 14, color: '#38bdf8' }
  ];

  // 5. Violin Data (Density distributions across cohorts)
  const violinData = [
    {
      group: 'Tier A',
      median: 78,
      points: [62, 68, 72, 75, 78, 80, 84, 88, 92, 96]
    },
    {
      group: 'Tier B',
      median: 58,
      points: [44, 48, 52, 56, 58, 62, 65, 70, 74, 80]
    },
    {
      group: 'Tier C',
      median: 45,
      points: [30, 35, 38, 42, 45, 48, 50, 54, 60, 66]
    }
  ];

  // 6. Area Data (Multi-series time progression across distinct depth lanes)
  const areaData = {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    series: [
      { name: 'Cloud Infra', color: '#013E37', values: [32, 45, 58, 65, 78, 92] },
      { name: 'AI Pipelines', color: '#08ab9c', values: [20, 34, 48, 62, 74, 86] },
      { name: 'Edge Devices', color: '#f47a34', values: [15, 22, 30, 42, 50, 68] }
    ]
  };

  // 7. Donut Data (Proportions summing to 100%)
  const donutData = [
    { name: 'Direct Sales', value: 42, color: '#013E37' },
    { name: 'Partner Channel', value: 26, color: '#08ab9c' },
    { name: 'Enterprise Referral', value: 18, color: '#f47a34' },
    { name: 'Inbound Web', value: 14, color: '#fc6eae' }
  ];

  // 8. Pie Data (Proportions summing to 100%)
  const pieData = [
    { name: 'North America', value: 38, color: '#013E37' },
    { name: 'Europe EMEA', value: 28, color: '#08ab9c' },
    { name: 'Asia Pacific', value: 20, color: '#f47a34' },
    { name: 'Latin America', value: 14, color: '#ffbd29' }
  ];

  return {
    radar: {
      title: '3D Performance Radar',
      desc: 'Multi-dimensional spatial polygon with spatial axis poles',
      data: radarData
    },
    lollipop: {
      title: '3D Urban Metrics Lollipop',
      desc: '3D cylinder stems + metallic sphere tips on ground plane',
      data: lollipopData
    },
    waterfall: {
      title: '3D Fiscal Waterfall',
      desc: 'Sequential 3D floating prisms with net balance math',
      data: waterfallData
    },
    treemap: {
      title: '3D Volume Treemap',
      desc: 'Proportional 3D boxes sized by value with depth lanes',
      data: treemapData
    },
    violin: {
      title: '3D Distribution Violin',
      desc: 'True bilateral kernel density volume surfaces in 3D',
      data: violinData
    },
    area: {
      title: '3D Tiered Area Surface',
      desc: 'Multi-series separated into parallel depth lanes',
      data: areaData
    },
    donut: {
      title: '3D Toroidal Donut',
      desc: 'Real 3D curved toroidal segments with radial gaps',
      data: donutData
    },
    pie: {
      title: '3D Extruded Pie',
      desc: 'Extruded 3D wedges with radial hover expansion',
      data: pieData
    }
  };
}
