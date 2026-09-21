/**
 * Generates intelligent, dynamic visualization quick prompts based on
 * the dataset's specific column names and data types (numeric vs categorical).
 */
export function getDynamicQuickChips(dataset) {
  if (!dataset || !dataset.columns || dataset.columns.length === 0) {
    return [
      {
        category: 'compare',
        icon: '📊',
        tag: 'Bar',
        title: 'Bar Comparison',
        desc: 'Compare categorical frequencies',
        query: 'Create a bar chart comparing top categories',
        accent: '#38bdf8'
      },
      {
        category: 'dist',
        icon: '🎻',
        tag: 'Violin',
        title: 'Violin Distribution',
        desc: 'Distribution & density shape',
        query: 'Show a violin plot of numeric distribution',
        accent: '#a78bfa'
      }
    ];
  }

  const numCols = dataset.numeric_columns || [];
  const catCols = dataset.columns.filter((c) => !numCols.includes(c));

  const num1 = numCols[0] || dataset.columns[0];
  const num2 = numCols[1] || numCols[0] || dataset.columns[1] || dataset.columns[0];
  const cat1 = catCols[0] || dataset.columns[0];

  const chips = [];

  // --- Compare Category ---
  if (cat1 && num1) {
    chips.push({
      category: 'compare',
      icon: '📊',
      tag: 'Bar',
      title: 'Bar Comparison',
      desc: `${num1} across ${cat1}`,
      query: `Generate a bar chart of ${num1} across ${cat1}`,
      accent: '#38bdf8'
    });
    chips.push({
      category: 'compare',
      icon: '📈',
      tag: 'Line',
      title: 'Line Trend',
      desc: `${num1} over ${cat1}`,
      query: `Plot a line chart of ${num1} over ${cat1}`,
      accent: '#818cf8'
    });
    chips.push({
      category: 'compare',
      icon: '🍭',
      tag: 'Lollipop',
      title: 'Lollipop Stem',
      desc: `${num1} across ${cat1}`,
      query: `Create a lollipop chart of ${num1} across ${cat1}`,
      accent: '#ec4899'
    });
    chips.push({
      category: 'compare',
      icon: '🗺️',
      tag: 'Treemap',
      title: 'Treemap Share',
      desc: `${cat1} by ${num1}`,
      query: `Create a treemap showing ${cat1} sized by ${num1}`,
      accent: '#10b981'
    });
    chips.push({
      category: 'compare',
      icon: '🪜',
      tag: 'Waterfall',
      title: 'Waterfall Flow',
      desc: `${cat1} vs ${num1}`,
      query: `Generate a waterfall chart showing ${cat1} vs ${num1}`,
      accent: '#f59e0b'
    });
  }

  // --- Distribute Category ---
  if (cat1 && num1) {
    chips.push({
      category: 'dist',
      icon: '🍩',
      tag: 'Donut',
      title: 'Donut Share',
      desc: `${cat1} (${num1})`,
      query: `Generate a donut chart of ${cat1} proportions`,
      accent: '#f43f5e'
    });
    chips.push({
      category: 'dist',
      icon: '🥧',
      tag: 'Pie',
      title: 'Pie Breakdown',
      desc: `${cat1} distribution`,
      query: `Create a pie chart showing breakdown of ${cat1}`,
      accent: '#f97316'
    });
  }

  if (num1) {
    chips.push({
      category: 'dist',
      icon: '📶',
      tag: 'Histogram',
      title: 'Hist Frequency',
      desc: `${num1} frequency bins`,
      query: `Plot a histogram of ${num1} with KDE curve`,
      accent: '#06b6d4'
    });
    chips.push({
      category: 'dist',
      icon: '🌊',
      tag: 'KDE Density',
      title: 'KDE Density',
      desc: `${num1} smooth density`,
      query: `Plot a smooth KDE density curve of ${num1}`,
      accent: '#14b8a6'
    });
    chips.push({
      category: 'dist',
      icon: '📦',
      tag: 'Boxplot',
      title: 'Box Quartiles',
      desc: `${num1} ${cat1 ? `by ${cat1}` : 'spread'}`,
      query: `Show a boxplot of ${num1} ${cat1 ? `grouped by ${cat1}` : ''}`,
      accent: '#eab308'
    });
    chips.push({
      category: 'dist',
      icon: '🎻',
      tag: 'Violin',
      title: 'Violin Spread',
      desc: `${num1} density shape`,
      query: `Generate a violin plot of ${num1} ${cat1 ? `by ${cat1}` : ''}`,
      accent: '#a855f7'
    });
  }

  // --- Relations / Correlate Category ---
  if (numCols.length >= 2) {
    chips.push({
      category: 'correlate',
      icon: '🔥',
      tag: 'Heatmap',
      title: 'Correlation Matrix',
      desc: 'All numeric features',
      query: 'Generate a correlation heatmap with annotations',
      accent: '#ef4444'
    });
    chips.push({
      category: 'correlate',
      icon: '✨',
      tag: 'Scatter',
      title: 'Scatter Spread',
      desc: `${num1} vs ${num2}`,
      query: `Create a scatter plot of ${num1} vs ${num2} with regression trendline`,
      accent: '#3b82f6'
    });
    chips.push({
      category: 'correlate',
      icon: '🫧',
      tag: 'Bubble',
      title: 'Bubble Multi-Var',
      desc: `${num1} vs ${num2} (${cat1 || 'size'})`,
      query: `Create a bubble chart of ${num1} vs ${num2} ${cat1 ? `colored by ${cat1}` : ''}`,
      accent: '#c084fc'
    });
    chips.push({
      category: 'correlate',
      icon: '🕸️',
      tag: 'Radar',
      title: 'Radar Spider',
      desc: 'Multi-metric comparison',
      query: `Generate a radar chart comparing metrics across ${cat1 || 'items'}`,
      accent: '#8b5cf6'
    });
  }

  // --- Theme Styles Category ---
  if (numCols.length >= 2) {
    chips.push({
      category: 'theme',
      icon: '🌙',
      tag: 'Dark Magma',
      title: 'Dark Magma Glow',
      desc: 'Dark background & Magma',
      query: 'Generate a correlation heatmap with dark_background style and magma palette',
      accent: '#f43f5e'
    });
  }

  if (cat1 && num1) {
    chips.push({
      category: 'theme',
      icon: '🎨',
      tag: 'Pastel Bar',
      title: 'Pastel Clean',
      desc: `${num1} by ${cat1} (Whitegrid)`,
      query: `Create a bar chart of ${num1} by ${cat1} with pastel palette and whitegrid style`,
      accent: '#10b981'
    });
    chips.push({
      category: 'theme',
      icon: '📰',
      tag: '538 Waterfall',
      title: '538 Journalism',
      desc: `${cat1} vs ${num1} (Coolwarm)`,
      query: `Show a waterfall chart of ${cat1} vs ${num1} with fivethirtyeight style and coolwarm palette`,
      accent: '#3b82f6'
    });
  }

  return chips;
}

/**
 * Returns the concise starter prompt for any selected chart type (e.g. 'Plot a line chart of ')
 * without auto-filling columns, allowing the user to specify their own features.
 */
export function generateAccurateChartQuery(chartType) {
  if (!chartType) return '';

  const prefixMap = {
    bar: 'Plot a bar chart of ',
    line: 'Plot a line chart of ',
    scatter: 'Plot a scatter plot of ',
    histogram: 'Plot a histogram of ',
    box: 'Plot a box plot of ',
    heatmap: 'Plot a heatmap of ',
    pie: 'Plot a pie chart of ',
    donut: 'Plot a donut chart of ',
    area: 'Plot an area chart of ',
    violin: 'Plot a violin plot of ',
    treemap: 'Plot a treemap of ',
    waterfall: 'Plot a waterfall chart of ',
    funnel: 'Plot a funnel chart of ',
    lollipop: 'Plot a lollipop chart of ',
    radar: 'Plot a radar chart of ',
    bubble: 'Plot a bubble chart of ',
    pairplot: 'Plot a pairplot of '
  };

  return prefixMap[chartType.toLowerCase()] || `Plot a ${chartType} chart of `;
}

