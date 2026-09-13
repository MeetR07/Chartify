export const THEME_STYLES = [
  { id: 'whitegrid', label: 'Whitegrid', desc: 'Clean Light Background', icon: '🌟' },
  { id: 'dark_background', label: 'Dark Glow', desc: 'Deep Dark Glow', icon: '🌙' },
  { id: 'darkgrid', label: 'Dark Grid', desc: 'Technical Dark Grid', icon: '📐' },
  { id: 'fivethirtyeight', label: '538 Editorial', desc: 'FiveThirtyEight Journalism', icon: '📰' },
  { id: 'ggplot', label: 'GGPlot', desc: 'Classic R GGPlot2', icon: '📊' },
  { id: 'ticks', label: 'Minimal', desc: 'Clean Minimal Ticks', icon: '⚡' },
];

export const PALETTE_GROUPS = [
  {
    group: '🌈 Gradient & Sequential',
    palettes: [
      { id: 'viridis', label: 'Viridis', desc: 'Purple → Teal → Yellow', colors: ['#440154', '#21918c', '#fde725'] },
      { id: 'plasma', label: 'Plasma', desc: 'Purple → Pink → Orange', colors: ['#7e03a8', '#cc4778', '#f89540'] },
      { id: 'inferno', label: 'Inferno', desc: 'Black → Crimson → Flame', colors: ['#57106e', '#bc3754', '#f98e09'] },
      { id: 'magma', label: 'Magma', desc: 'Dark → Magenta → Peach', colors: ['#000004', '#b73779', '#fcfdbf'] },
      { id: 'rocket', label: 'Rocket', desc: 'Navy → Magenta → Gold', colors: ['#03051a', '#ce436e', '#fae1ab'] },
      { id: 'mako', label: 'Mako', desc: 'Deep Navy → Teal → Mint', colors: ['#0b0405', '#357ba2', '#def5e5'] },
    ]
  },
  {
    group: '🌊 Ocean & Cool (Diverging)',
    palettes: [
      { id: 'coolwarm', label: 'Coolwarm', desc: 'Polar Blue → Gray → Red', colors: ['#3b4cc0', '#dddcdb', '#8b0000'] },
      { id: 'crest', label: 'Crest', desc: 'Mint → Teal → Sea Blue', colors: ['#61aa90', '#33858d', '#1e5d86'] },
      { id: 'icefire', label: 'Icefire', desc: 'Blue → Dark → Crimson', colors: ['#4167c7', '#1f1e1e', '#b93540'] },
    ]
  },
  {
    group: '🔥 Sunset & Warm',
    palettes: [
      { id: 'flare', label: 'Flare', desc: 'Peach → Rose → Plum', colors: ['#e5715e', '#c14168', '#863071'] },
      { id: 'Spectral', label: 'Spectral', desc: 'Red → Amber → Green', colors: ['#d53e4f', '#fee08b', '#99d594'] },
      { id: 'copper', label: 'Copper Bronze', desc: 'Bronze → Copper → Amber', colors: ['#4f3220', '#9e6440', '#ed9660'] },
    ]
  },
  {
    group: '🎯 Categorical & Distinct',
    palettes: [
      { id: 'deep', label: 'Deep', desc: 'Classic Blue / Green / Red', colors: ['#4C72B0', '#55A868', '#C44E52'] },
      { id: 'pastel', label: 'Pastel', desc: 'Soft Calming Pastels', colors: ['#a1c9f4', '#8de5a1', '#ff9f9b'] },
      { id: 'Set2', label: 'Set2', desc: 'Muted Professional Tones', colors: ['#66c2a5', '#fc8d62', '#8da0cb'] },
      { id: 'colorblind', label: 'Pro Colorblind', desc: 'High-Contrast Accessible', colors: ['#0173b2', '#de8f05', '#029e73'] },
    ]
  }
];

export const PALETTES = PALETTE_GROUPS.flatMap((g) => g.palettes);

export const PROMPT_CATEGORIES = [
  { id: 'all', label: 'All', icon: '✨' },
  { id: 'compare', label: 'Compare', icon: '📊' },
  { id: 'dist', label: 'Distribute', icon: '🍩' },
  { id: 'correlate', label: 'Relations', icon: '🔥' },
  { id: 'theme', label: 'Styles', icon: '🎨' },
];

export const QUICK_PRESETS = [
  { label: '🌟 Clean Light', style: 'whitegrid', palette: 'deep' },
  { label: '🔥 Neon Sunset', style: 'dark_background', palette: 'inferno' },
  { label: '🌊 Emerald Ocean', style: 'whitegrid', palette: 'crest' },
  { label: '📰 538 Editorial', style: 'fivethirtyeight', palette: 'coolwarm' },
  { label: '📊 Dark Viridis', style: 'darkgrid', palette: 'viridis' },
  { label: '🌸 Soft Pastel', style: 'whitegrid', palette: 'pastel' },
];
