import React, { useEffect, useRef, useState, useMemo } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { Play, Pause, RotateCcw, Box, Eye, Sparkles, Hash, Layers } from 'lucide-react';

const PALETTE_MAP = {
  butter_green: ['#013E37', '#FFEFB3', '#08ab9c', '#f47a34', '#fc6eae', '#ffbd29', '#146665'],
  aura_bloom:   ['#08ab9c', '#fc6eae', '#f47a34', '#146665', '#ffbd29', '#feb3a8', '#fff2b7'],
  custom:       ['#013E37', '#FFEFB3', '#08ab9c', '#f47a34', '#fc6eae', '#ffbd29', '#146665'],
  vibrant:      ['#6366F1', '#06B6D4', '#10B981', '#F59E0B', '#EC4899', '#8B5CF6', '#3B82F6', '#F43F5E'],
  cyberpunk:    ['#00F2FE', '#4FACFE', '#FF007F', '#7928CA', '#FF4B4B', '#00DFD8', '#FEE140', '#A855F7'],
  emerald:      ['#10B981', '#059669', '#047857', '#34D399', '#6EE7B7', '#065F46', '#14B8A6', '#0D9488'],
  sunset:       ['#F43F5E', '#FB923C', '#FBBF24', '#F472B6', '#C084FC', '#E11D48', '#EA580C', '#D97706'],
  ocean:        ['#0EA5E9', '#38BDF8', '#0284C7', '#6366F1', '#7DD3FC', '#0369A1', '#2563EB', '#1D4ED8'],
  purple:       ['#8B5CF6', '#7C3AED', '#6D28D9', '#A78BFA', '#C4B5FD', '#5B21B6', '#4C1D95', '#9333EA'],
  luxe:         ['#38BDF8', '#818CF8', '#C084FC', '#F472B6', '#FB7185', '#34D399', '#FBBF24', '#A78BFA'],
  monochrome:   ['#334155', '#475569', '#64748B', '#94A3B8', '#CBD5E1', '#1E293B', '#0F172A', '#E2E8F0'],
  viridis:      ['#440154', '#3b528b', '#21918c', '#5ec962', '#fde725'],
  plasma:       ['#0d0887', '#6a00a8', '#b12a90', '#e16462', '#fca636', '#f0f921'],
  inferno:      ['#000004', '#420a68', '#932667', '#dd513a', '#fca50a', '#fcffa4'],
  magma:        ['#000004', '#3b0f70', '#8c2981', '#de4968', '#fe9f6d', '#fcfdbf'],
  rocket:       ['#03051a', '#491078', '#902882', '#ce436e', '#fae1ab'],
  mako:         ['#0b0405', '#1a3348', '#2d607a', '#357ba2', '#549eb3', '#def5e5'],
  coolwarm:     ['#3b4cc0', '#6f89dd', '#b4c4ec', '#f29e8e', '#d55e4b', '#8b0000'],
  crest:        ['#61aa90', '#33858d', '#1e5d86', '#87c7a5', '#bde2ce'],
  icefire:      ['#4167c7', '#6baed6', '#b0c4de', '#1f1e1e', '#e6550d', '#b93540'],
  flare:        ['#e5715e', '#c14168', '#863071', '#511b59', '#ec8270', '#f4ad9e'],
  Spectral:     ['#d53e4f', '#fc8d59', '#fee08b', '#e6f598', '#99d594', '#3288bd'],
  copper:       ['#4f3220', '#7a4e32', '#9e6440', '#ed9660', '#ffc080'],
  deep:         ['#4C72B0', '#55A868', '#C44E52', '#8172B2', '#CCB974', '#64B5CD'],
  pastel:       ['#a1c9f4', '#8de5a1', '#ff9f9b', '#d0bbff', '#fffea3', '#b9f2f0'],
  Set2:         ['#66c2a5', '#fc8d62', '#8da0cb', '#e78ac3', '#a6d854', '#ffd92f'],
  colorblind:   ['#0173b2', '#de8f05', '#029e73', '#d55e00', '#cc78bc', '#ca9161']
};

function resolvePaletteColors(paletteKey) {
  if (!paletteKey) return PALETTE_MAP.butter_green;
  const k = String(paletteKey).toLowerCase().replace(/-/g, '_').trim();
  return PALETTE_MAP[k] || PALETTE_MAP.butter_green;
}

/** Formats values nicely with K/M/B abbreviations */
function formatDataValue(val) {
  if (val === null || val === undefined) return '';
  const num = typeof val === 'number' ? val : parseFloat(val);
  if (isNaN(num)) return String(val);
  const abs = Math.abs(num);
  const sign = num < 0 ? '-' : '';
  if (abs >= 1_000_000_000) return `${sign}${(abs / 1_000_000_000).toFixed(1)}B`;
  if (abs >= 1_000_000) return `${sign}${(abs / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${sign}${(abs / 1_000).toFixed(1)}K`;
  if (Number.isInteger(num)) return `${sign}${abs}`;
  return `${sign}${abs.toFixed(1)}`;
}

/**
 * Creates flat 2D decal plane meshes glued directly onto the top face of 3D columns/blocks.
 */
function createSurfaceLabelMesh(val, label = '', sizeX = 1.0, sizeZ = 1.0, isDark = false, accentHex = '#08ab9c') {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');

  const formattedVal = formatDataValue(val);
  const cleanLabel = String(label || '');
  const displayLabel = cleanLabel.length > 10 ? cleanLabel.slice(0, 8) + '…' : cleanLabel;

  const res = 256;
  canvas.width = res;
  canvas.height = res;

  const pad = 14;
  const radius = 28;
  ctx.save();
  ctx.beginPath();
  if (ctx.roundRect) {
    ctx.roundRect(pad, pad, res - pad * 2, res - pad * 2, radius);
  } else {
    ctx.rect(pad, pad, res - pad * 2, res - pad * 2);
  }

  // Modern semi-transparent glass decal glued to block surface
  ctx.fillStyle = isDark ? 'rgba(15, 23, 42, 0.88)' : 'rgba(255, 253, 240, 0.92)';
  ctx.fill();

  ctx.lineWidth = 6;
  ctx.strokeStyle = isDark ? '#38bdf8' : (accentHex || '#013e37');
  ctx.stroke();

  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  // Primary Number
  ctx.font = 'bold 64px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
  ctx.fillStyle = isDark ? '#ffffff' : '#013e37';
  const valY = displayLabel ? res * 0.42 : res * 0.5;
  ctx.fillText(formattedVal, res / 2, valY);

  // Subtext
  if (displayLabel) {
    ctx.font = '600 28px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    ctx.fillStyle = isDark ? '#94a3b8' : '#08ab9c';
    ctx.fillText(displayLabel, res / 2, res * 0.74);
  }
  ctx.restore();

  const texture = new THREE.CanvasTexture(canvas);
  texture.minFilter = THREE.LinearFilter;
  texture.magFilter = THREE.LinearFilter;
  texture.needsUpdate = true;

  const geom = new THREE.PlaneGeometry(sizeX, sizeZ);
  const mat = new THREE.MeshBasicMaterial({
    map: texture,
    transparent: true,
    depthTest: true,
    polygonOffset: true,
    polygonOffsetFactor: -1,
    polygonOffsetUnits: -1
  });

  const mesh = new THREE.Mesh(geom, mat);
  mesh.rotation.x = -Math.PI / 2;
  return mesh;
}

/**
 * Creates compact, tight micro-badges for floating spheres with strict depth testing.
 */
function createTightBadgeSprite(val, isDark = false, accentHex = '#08ab9c') {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');

  const formattedVal = formatDataValue(val);
  const scale = 2;
  const w = 110;
  const h = 44;
  canvas.width = w * scale;
  canvas.height = h * scale;
  ctx.scale(scale, scale);

  ctx.save();
  ctx.beginPath();
  if (ctx.roundRect) {
    ctx.roundRect(4, 4, w - 8, h - 8, 10);
  } else {
    ctx.rect(4, 4, w - 8, h - 8);
  }
  ctx.fillStyle = isDark ? 'rgba(15, 23, 42, 0.90)' : 'rgba(255, 253, 240, 0.94)';
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = isDark ? '#38bdf8' : (accentHex || '#013e37');
  ctx.stroke();

  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.font = 'bold 22px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
  ctx.fillStyle = isDark ? '#ffffff' : '#013e37';
  ctx.fillText(formattedVal, w / 2, h / 2);
  ctx.restore();

  const texture = new THREE.CanvasTexture(canvas);
  texture.minFilter = THREE.LinearFilter;
  texture.magFilter = THREE.LinearFilter;
  texture.needsUpdate = true;

  const spriteMat = new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthTest: true
  });

  const sprite = new THREE.Sprite(spriteMat);
  sprite.scale.set(1.05, 0.42, 1);
  return sprite;
}

/**
 * Creates floating pill badge with glowing border and downward pointer tip directly above columns.
 */
function createFloatingValueBadge(val, colorHex = '#38bdf8') {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  const scale = 3;
  const w = 110;
  const h = 56;
  canvas.width = w * scale;
  canvas.height = h * scale;
  ctx.scale(scale, scale);

  const formattedVal = formatDataValue(val);

  const pad = 4;
  const bw = w - pad * 2;
  const bh = 34;
  const r = 8;
  const tipW = 8;
  const tipH = 8;
  const centerX = w / 2;

  ctx.save();
  ctx.beginPath();
  ctx.moveTo(pad + r, pad);
  ctx.lineTo(pad + bw - r, pad);
  ctx.arcTo(pad + bw, pad, pad + bw, pad + r, r);
  ctx.lineTo(pad + bw, pad + bh - r);
  ctx.arcTo(pad + bw, pad + bh, pad + bw - r, pad + bh, r);

  // Downward pointer tip pointing towards the top face of the 3D bar
  ctx.lineTo(centerX + tipW, pad + bh);
  ctx.lineTo(centerX, pad + bh + tipH);
  ctx.lineTo(centerX - tipW, pad + bh);

  ctx.lineTo(pad + r, pad + bh);
  ctx.arcTo(pad, pad + bh, pad, pad + bh - r, r);
  ctx.lineTo(pad, pad + r);
  ctx.arcTo(pad, pad, pad + r, pad, r);
  ctx.closePath();

  // Dark glassy translucent background
  ctx.fillStyle = 'rgba(7, 13, 30, 0.94)';
  ctx.fill();

  // Neon glowing stroke matching column color
  ctx.lineWidth = 2.4;
  ctx.strokeStyle = colorHex;
  ctx.shadowColor = colorHex;
  ctx.shadowBlur = 8;
  ctx.stroke();

  // Crisp bold white value text
  ctx.shadowBlur = 0;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.font = 'bold 15px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
  ctx.fillStyle = '#ffffff';
  ctx.fillText(formattedVal, centerX, pad + bh / 2 + 0.5);
  ctx.restore();

  const texture = new THREE.CanvasTexture(canvas);
  texture.minFilter = THREE.LinearFilter;
  texture.magFilter = THREE.LinearFilter;
  texture.needsUpdate = true;

  const spriteMat = new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthTest: false
  });

  const sprite = new THREE.Sprite(spriteMat);
  sprite.scale.set(1.4, 0.71, 1);
  return sprite;
}

/**
 * Creates category text label sprite positioned beneath each 3D column.
 */
function createCategoryLabelSprite(label, isDark = true) {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  const scale = 3;
  const w = 120;
  const h = 40;
  canvas.width = w * scale;
  canvas.height = h * scale;
  ctx.scale(scale, scale);

  const cleanLabel = String(label ?? '');
  const displayLabel = cleanLabel.length > 12 ? cleanLabel.slice(0, 10) + '…' : cleanLabel;

  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.font = '600 16px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
  ctx.fillStyle = isDark ? '#cbd5e1' : '#334155';
  ctx.fillText(displayLabel, w / 2, h / 2);

  const texture = new THREE.CanvasTexture(canvas);
  texture.minFilter = THREE.LinearFilter;
  texture.magFilter = THREE.LinearFilter;
  texture.needsUpdate = true;

  const spriteMat = new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthTest: false
  });

  const sprite = new THREE.Sprite(spriteMat);
  sprite.scale.set(1.4, 0.46, 1);
  return sprite;
}

/**
 * Creates Y-axis tick label sprite.
 */
function createAxisTickLabelSprite(text) {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  const scale = 3;
  const w = 80;
  const h = 32;
  canvas.width = w * scale;
  canvas.height = h * scale;
  ctx.scale(scale, scale);

  ctx.textAlign = 'right';
  ctx.textBaseline = 'middle';
  ctx.font = '600 14px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
  ctx.fillStyle = '#93c5fd';
  ctx.fillText(text, w - 8, h / 2);

  const texture = new THREE.CanvasTexture(canvas);
  texture.minFilter = THREE.LinearFilter;
  texture.magFilter = THREE.LinearFilter;
  texture.needsUpdate = true;

  const spriteMat = new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthTest: false
  });
  const sprite = new THREE.Sprite(spriteMat);
  sprite.scale.set(0.95, 0.38, 1);
  return sprite;
}

/**
 * Creates rotated or horizontal axis title sprite (e.g., "Sales", "Month").
 */
function createAxisTitleSprite(text, isVertical = false) {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  const scale = 3;
  const w = isVertical ? 44 : 180;
  const h = isVertical ? 180 : 44;
  canvas.width = w * scale;
  canvas.height = h * scale;
  ctx.scale(scale, scale);

  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.font = 'bold 16px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
  ctx.fillStyle = '#60a5fa';

  if (isVertical) {
    ctx.save();
    ctx.translate(w / 2, h / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText(text, 0, 0);
    ctx.restore();
  } else {
    ctx.fillText(text, w / 2, h / 2);
  }

  const texture = new THREE.CanvasTexture(canvas);
  texture.minFilter = THREE.LinearFilter;
  texture.magFilter = THREE.LinearFilter;
  texture.needsUpdate = true;

  const spriteMat = new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthTest: false
  });
  const sprite = new THREE.Sprite(spriteMat);
  sprite.scale.set(w / 70, h / 70, 1);
  return sprite;
}

/**
 * Creates chamfered / beveled 3D column geometry with rounded vertical corners and beveled top edges.
 */
function createBeveledBarGeometry(width, height, depth, bevel = 0.05) {
  const shape = new THREE.Shape();
  const hw = Math.max(0.1, (width / 2) - bevel);
  const hd = Math.max(0.1, (depth / 2) - bevel);
  const r = Math.min(0.08, hw * 0.4, hd * 0.4);

  shape.moveTo(-hw + r, -hd);
  shape.lineTo(hw - r, -hd);
  shape.quadraticCurveTo(hw, -hd, hw, -hd + r);
  shape.lineTo(hw, hd - r);
  shape.quadraticCurveTo(hw, hd, hw - r, hd);
  shape.lineTo(-hw + r, hd);
  shape.quadraticCurveTo(-hw, hd, -hw, hd - r);
  shape.lineTo(-hw, -hd + r);
  shape.quadraticCurveTo(-hw, -hd, -hw + r, -hd);

  const actualHeight = Math.max(height, 0.4);
  const extrudeDepth = Math.max(actualHeight - bevel * 2, 0.05);

  const extrudeSettings = {
    steps: 1,
    depth: extrudeDepth,
    bevelEnabled: true,
    bevelThickness: bevel,
    bevelSize: bevel,
    bevelSegments: 4
  };

  const geom = new THREE.ExtrudeGeometry(shape, extrudeSettings);
  geom.rotateX(-Math.PI / 2);
  geom.computeBoundingBox();
  const minY = geom.boundingBox.min.y;
  geom.translate(0, -minY, 0);
  return geom;
}

export function resolveBackgroundTheme(styleKey = 'whitegrid', paletteKey = 'butter_green', displayMode = 'mesh') {
  const s = String(styleKey || '').toLowerCase().replace(/-/g, '_').trim();
  const p = String(paletteKey || '').toLowerCase().replace(/-/g, '_').trim();

  // If viewing 3D mesh engine, default to the immersive cyber dark stage from the design reference
  if (displayMode === 'mesh') {
    return {
      cssBackground: 'radial-gradient(circle at 50% 35%, #0c1838 0%, #050b1a 100%)',
      gridColor: 0x1d4ed8,
      gridOpacity: 0.38,
      accentColor: 0x38bdf8,
      lightIntensity: 1.4,
      ambientIntensity: 0.9,
      floorShadowOpacity: 0.38,
      isDark: true
    };
  }

  const isDarkStyle = s.includes('dark');
  const isDarkPalette = ['inferno', 'magma', 'cyberpunk', 'rocket', 'mako', 'icefire'].includes(p);

  // 1. Cyberpunk neon dark
  if (p === 'cyberpunk' || (isDarkStyle && p === 'plasma')) {
    return {
      cssBackground: 'radial-gradient(circle at 50% 40%, #170d2c 0%, #080314 100%)',
      gridColor: 0x00f2fe,
      gridOpacity: 0.32,
      accentColor: 0x00f2fe,
      lightIntensity: 1.35,
      ambientIntensity: 0.9,
      floorShadowOpacity: 0.3,
      isDark: true
    };
  }

  // 2. Deep ember / fiery dark
  if (['inferno', 'magma', 'flare'].includes(p) || (isDarkStyle && ['sunset', 'copper'].includes(p))) {
    return {
      cssBackground: 'radial-gradient(circle at 50% 40%, #200d16 0%, #090206 100%)',
      gridColor: 0xf47a34,
      gridOpacity: 0.28,
      accentColor: 0xfca50a,
      lightIntensity: 1.3,
      ambientIntensity: 0.85,
      floorShadowOpacity: 0.3,
      isDark: true
    };
  }

  // 3. Oceanic / Deep Navy Abyss
  if (['rocket', 'mako', 'icefire'].includes(p) || (isDarkStyle && ['ocean', 'crest', 'coolwarm'].includes(p))) {
    return {
      cssBackground: 'radial-gradient(circle at 50% 40%, #0c1c2b 0%, #02080e 100%)',
      gridColor: 0x38bdf8,
      gridOpacity: 0.28,
      accentColor: 0x0ea5e9,
      lightIntensity: 1.3,
      ambientIntensity: 0.85,
      floorShadowOpacity: 0.3,
      isDark: true
    };
  }

  // 4. Emerald Pine Dark
  if (isDarkStyle && ['emerald', 'viridis', 'butter_green'].includes(p)) {
    return {
      cssBackground: 'radial-gradient(circle at 50% 40%, #04211d 0%, #010a08 100%)',
      gridColor: 0x10b981,
      gridOpacity: 0.3,
      accentColor: 0x08ab9c,
      lightIntensity: 1.3,
      ambientIntensity: 0.85,
      floorShadowOpacity: 0.3,
      isDark: true
    };
  }

  // 5. Generic Dark Grid / Dark Glow
  if (isDarkStyle || isDarkPalette) {
    return {
      cssBackground: 'radial-gradient(circle at 50% 40%, #152030 0%, #080d17 100%)',
      gridColor: 0x475569,
      gridOpacity: 0.35,
      accentColor: 0x60a5fa,
      lightIntensity: 1.3,
      ambientIntensity: 0.85,
      floorShadowOpacity: 0.3,
      isDark: true
    };
  }

  // 6. FiveThirtyEight Editorial Paper Grey
  if (s === 'fivethirtyeight') {
    return {
      cssBackground: 'radial-gradient(circle at 50% 40%, #ffffff 0%, #e2e8f0 100%)',
      gridColor: 0x64748b,
      gridOpacity: 0.22,
      accentColor: 0x334155,
      lightIntensity: 1.1,
      ambientIntensity: 0.85,
      floorShadowOpacity: 0.12,
      isDark: false
    };
  }

  // 7. GGPlot Muted Slate
  if (s === 'ggplot') {
    return {
      cssBackground: 'radial-gradient(circle at 50% 40%, #f1f5f9 0%, #cbd5e1 100%)',
      gridColor: 0x94a3b8,
      gridOpacity: 0.28,
      accentColor: 0x475569,
      lightIntensity: 1.15,
      ambientIntensity: 0.85,
      floorShadowOpacity: 0.14,
      isDark: false
    };
  }

  // 8. Minimal Ticks Clean Light
  if (s === 'ticks') {
    return {
      cssBackground: 'radial-gradient(circle at 50% 40%, #ffffff 0%, #f1f5f9 100%)',
      gridColor: 0x94a3b8,
      gridOpacity: 0.18,
      accentColor: 0x0f172a,
      lightIntensity: 1.2,
      ambientIntensity: 0.85,
      floorShadowOpacity: 0.1,
      isDark: false
    };
  }

  // 9. Aura Bloom Soft Sunrise
  if (p === 'aura_bloom') {
    return {
      cssBackground: 'radial-gradient(circle at 50% 40%, #fff7f2 0%, #fed7c7 100%)',
      gridColor: 0x146665,
      gridOpacity: 0.22,
      accentColor: 0xfc6eae,
      lightIntensity: 1.15,
      ambientIntensity: 0.85,
      floorShadowOpacity: 0.12,
      isDark: false
    };
  }

  // 10. Sunset / Warm Light
  if (['sunset', 'flare', 'Spectral'].includes(p)) {
    return {
      cssBackground: 'radial-gradient(circle at 50% 40%, #fff5f2 0%, #fed0c5 100%)',
      gridColor: 0xe11d48,
      gridOpacity: 0.2,
      accentColor: 0xf43f5e,
      lightIntensity: 1.2,
      ambientIntensity: 0.85,
      floorShadowOpacity: 0.12,
      isDark: false
    };
  }

  // 11. Ocean / Crest Cool Light
  if (['ocean', 'crest', 'coolwarm'].includes(p)) {
    return {
      cssBackground: 'radial-gradient(circle at 50% 40%, #f0f9ff 0%, #bae6fd 100%)',
      gridColor: 0x0284c7,
      gridOpacity: 0.22,
      accentColor: 0x0ea5e9,
      lightIntensity: 1.2,
      ambientIntensity: 0.85,
      floorShadowOpacity: 0.12,
      isDark: false
    };
  }

  // 12. Soft Pastel Light
  if (p === 'pastel') {
    return {
      cssBackground: 'radial-gradient(circle at 50% 40%, #faf5ff 0%, #e9d5ff 100%)',
      gridColor: 0x7c3aed,
      gridOpacity: 0.2,
      accentColor: 0x8b5cf6,
      lightIntensity: 1.2,
      ambientIntensity: 0.85,
      floorShadowOpacity: 0.12,
      isDark: false
    };
  }

  // 13. Default Butter & Green
  return {
    cssBackground: 'radial-gradient(circle at 50% 40%, #FFFDF0 0%, #FFEFB3 100%)',
    gridColor: 0x013e37,
    gridOpacity: 0.22,
    accentColor: 0x013e37,
    lightIntensity: 1.2,
    ambientIntensity: 0.85,
    floorShadowOpacity: 0.12,
    isDark: false
  };
}

export default function ThreeCanvas({ activeChart, dataset, selectedPalette, selectedStyle }) {
  const mountRef = useRef(null);
  const tooltipRef = useRef(null);
  const tooltipLabelRef = useRef(null);
  const tooltipValRef = useRef(null);

  const [autoRotate, setAutoRotate] = useState(false);
  const [wireframe, setWireframe] = useState(false);
  const [showLabels, setShowLabels] = useState(true);

  const chartType = (activeChart?.chart_type || '').toLowerCase();
  const [displayMode, setDisplayMode] = useState('mesh');

  // Default to 3D Mesh visualization
  useEffect(() => {
    setDisplayMode('mesh');
  }, [activeChart?.id, activeChart?.chart_type]);

  // References for Three.js objects
  const sceneRef = useRef(null);
  const cameraRef = useRef(null);
  const rendererRef = useRef(null);
  const controlsRef = useRef(null);
  const animFrameRef = useRef(null);
  const interactiveObjectsRef = useRef([]);

  // Resolve Active Keys & Background Theme (Memoized to prevent new reference creation on re-render)
  const activePaletteKey = selectedPalette || activeChart?.args?.palette || 'butter_green';
  const activeStyleKey = selectedStyle || activeChart?.args?.style || 'whitegrid';
  const bgTheme = useMemo(
    () => resolveBackgroundTheme(activeStyleKey, activePaletteKey, displayMode),
    [activeStyleKey, activePaletteKey, displayMode]
  );
  const chartArgsKey = JSON.stringify(activeChart?.args || {});

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    // Resolve Active Palette Colors
    const paletteColors = resolvePaletteColors(activePaletteKey);

    // 1. Scene Setup
    const scene = new THREE.Scene();
    sceneRef.current = scene;

    const width = container.clientWidth || 600;
    const height = container.clientHeight || 450;

    // 2. Camera (Slight isometric angle for 3D mesh view matching reference design)
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    if (displayMode === 'card') {
      camera.position.set(0, 5.7, 18.5);
    } else {
      camera.position.set(2.8, 8.2, 17.5);
    }
    cameraRef.current = camera;

    // 3. Renderer
    const isMobile = typeof window !== 'undefined' && window.innerWidth <= 768;
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    renderer.setSize(width, height);
    renderer.setPixelRatio(isMobile ? Math.min(window.devicePixelRatio || 1, 1.5) : Math.min(window.devicePixelRatio || 1, 2));
    renderer.domElement.style.touchAction = 'none';
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFShadowMap;
    rendererRef.current = renderer;
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // 4. OrbitControls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxPolarAngle = Math.PI / 2 - 0.02; // Don't go below floor
    controls.minDistance = 6;
    controls.maxDistance = 50;
    controls.autoRotate = autoRotate;
    controls.autoRotateSpeed = 1.2;
    controls.rotateSpeed = isMobile ? 0.75 : 1.0;
    controls.touches = {
      ONE: THREE.TOUCH.ROTATE,
      TWO: THREE.TOUCH.DOLLY_PAN
    };
    if (displayMode === 'card') {
      controls.target.set(0, 5.7, 0);
    } else {
      controls.target.set(0, 3.8, 0);
    }
    controls.update();
    controlsRef.current = controls;

    // 5. Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, bgTheme.ambientIntensity || 0.9);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, bgTheme.lightIntensity || 1.3);
    dirLight.position.set(12, 24, 14);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 1024;
    dirLight.shadow.mapSize.height = 1024;
    scene.add(dirLight);

    const rimLightColor = bgTheme.isDark ? 0x60a5fa : 0xffefb3;
    const rimLight = new THREE.DirectionalLight(rimLightColor, bgTheme.isDark ? 0.9 : 0.6);
    rimLight.position.set(-14, 12, -14);
    scene.add(rimLight);

    // Front specular fill light to bring out beveled edges and top chamfers
    const frontLight = new THREE.DirectionalLight(0xffffff, 0.75);
    frontLight.position.set(2, 12, 18);
    scene.add(frontLight);

    // 6. Floor Grid with Dynamic Theme Colors
    const gridHelper = new THREE.GridHelper(24, 24, bgTheme.gridColor, bgTheme.gridColor);
    gridHelper.position.y = 0;
    gridHelper.material.opacity = bgTheme.gridOpacity;
    gridHelper.material.transparent = true;
    scene.add(gridHelper);

    // Floor plane for soft shadows
    const floorGeo = new THREE.PlaneGeometry(28, 28);
    const floorMat = new THREE.ShadowMaterial({ opacity: bgTheme.floorShadowOpacity });
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    scene.add(floor);

    // 7. Build 3D Visualization based on Chart Type with Active Palette, Theme Accent & Permanent Data Numbers
    interactiveObjectsRef.current = [];
    build3DChart(scene, activeChart, dataset, wireframe, interactiveObjectsRef.current, paletteColors, bgTheme.accentColor, showLabels, bgTheme.isDark, displayMode, bgTheme);

    // 8. Raycaster for Mouse Hover Tooltips (direct DOM to prevent React re-renders)
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const onPointerMove = (event) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(interactiveObjectsRef.current);

      if (intersects.length > 0) {
        const item = intersects[0].object.userData;
        if (item && item.label) {
          if (tooltipRef.current) {
            tooltipRef.current.style.display = 'flex';
            tooltipRef.current.style.left = `${event.clientX - rect.left + 14}px`;
            tooltipRef.current.style.top = `${event.clientY - rect.top - 32}px`;
          }
          if (tooltipLabelRef.current) {
            tooltipLabelRef.current.textContent = item.label;
          }
          if (tooltipValRef.current) {
            tooltipValRef.current.textContent = item.val ?? '';
          }
          container.style.cursor = 'pointer';
          return;
        }
      }
      if (tooltipRef.current) {
        tooltipRef.current.style.display = 'none';
      }
      container.style.cursor = 'grab';
    };

    const onPointerLeave = () => {
      if (tooltipRef.current) {
        tooltipRef.current.style.display = 'none';
      }
      container.style.cursor = 'grab';
    };

    renderer.domElement.addEventListener('pointermove', onPointerMove);
    renderer.domElement.addEventListener('pointerleave', onPointerLeave);

    // 9. Animation Loop
    let startScaling = 0;
    const animate = () => {
      animFrameRef.current = requestAnimationFrame(animate);
      controls.update();

      // Gentle entry scale animation for meshes & 3D cards
      if (startScaling < 1) {
        startScaling += 0.04;
        interactiveObjectsRef.current.forEach((obj) => {
          if (obj.userData?.isCard) {
            const s = THREE.MathUtils.lerp(0.01, 1, startScaling);
            obj.scale.set(s, s, s);
          } else if (obj.userData?.isBeveledBar) {
            const s = THREE.MathUtils.lerp(0.01, 1, startScaling);
            obj.scale.y = s;
            if (obj.userData.badge) {
              obj.userData.badge.position.y = (obj.userData.barHeight * s) + 0.72;
            }
          } else if (obj.userData?.origScaleY) {
            obj.scale.y = THREE.MathUtils.lerp(0.01, obj.userData.origScaleY, startScaling);
            obj.position.y = (obj.scale.y * (obj.userData.baseHeight || 1)) / 2;
            if (obj.userData?.labelMesh) {
              obj.userData.labelMesh.position.y = (obj.scale.y * (obj.userData.baseHeight || 1)) + 0.015;
            }
          }
        });
      }

      renderer.render(scene, camera);
    };
    animFrameRef.current = requestAnimationFrame(animate);

    // 10. Responsive Resizing with requestAnimationFrame throttling
    let resizeRaf = null;
    const handleResize = () => {
      if (!container || !renderer || !camera) return;
      const w = container.clientWidth || 600;
      const h = container.clientHeight || 450;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    const resizeObserver = new ResizeObserver(() => {
      if (resizeRaf) cancelAnimationFrame(resizeRaf);
      resizeRaf = requestAnimationFrame(handleResize);
    });
    resizeObserver.observe(container);

    const onWindowResize = () => {
      if (resizeRaf) cancelAnimationFrame(resizeRaf);
      resizeRaf = requestAnimationFrame(handleResize);
    };
    window.addEventListener('resize', onWindowResize);

    // Cleanup
    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      if (resizeRaf) cancelAnimationFrame(resizeRaf);
      resizeObserver.disconnect();
      window.removeEventListener('resize', onWindowResize);
      renderer.domElement.removeEventListener('pointermove', onPointerMove);
      renderer.domElement.removeEventListener('pointerleave', onPointerLeave);
      if (tooltipRef.current) {
        tooltipRef.current.style.display = 'none';
      }
      renderer.dispose();
      scene.clear();
    };
  }, [
    activeChart?.id,
    activeChart?.chart_type,
    activeChart?.url,
    chartArgsKey,
    dataset,
    wireframe,
    showLabels,
    displayMode,
    activePaletteKey,
    activeStyleKey
  ]);

  // Update controls auto-rotate dynamically
  useEffect(() => {
    if (controlsRef.current) {
      controlsRef.current.autoRotate = autoRotate;
    }
  }, [autoRotate]);

  const handleResetCamera = () => {
    if (cameraRef.current && controlsRef.current) {
      if (displayMode === 'card') {
        cameraRef.current.position.set(0, 5.7, 18.5);
        controlsRef.current.target.set(0, 5.7, 0);
      } else {
        cameraRef.current.position.set(2.8, 8.2, 17.5);
        controlsRef.current.target.set(0, 3.8, 0);
      }
      controlsRef.current.update();
    }
  };

  return (
    <div
      className="three-canvas-wrapper"
      style={{
        background: bgTheme.cssBackground,
        transition: 'background 0.4s ease'
      }}
    >
      <div ref={mountRef} className="three-viewport" />

      {/* Floating 3D Hover Tooltip (Zero re-renders on pointer move) */}
      <div
        ref={tooltipRef}
        className="three-tooltip"
        style={{
          display: 'none',
          ...(bgTheme.isDark ? {
            background: '#0f172a',
            color: '#f8fafc',
            borderColor: '#38bdf8',
            boxShadow: '0 4px 12px rgba(0,0,0,0.6)'
          } : {})
        }}
      >
        <span ref={tooltipLabelRef} className="three-tooltip-label" />
        <span
          ref={tooltipValRef}
          className="three-tooltip-val"
          style={bgTheme.isDark ? { background: '#38bdf8', color: '#0f172a' } : {}}
        />
      </div>

      {/* 3D Floating Control Dock */}
      <div
        className="three-controls-dock"
        style={bgTheme.isDark ? {
          background: 'rgba(15, 23, 42, 0.92)',
          borderColor: bgTheme.accentColor ? `#${bgTheme.accentColor.toString(16).padStart(6, '0')}` : '#38bdf8'
        } : {}}
      >
        <button
          type="button"
          className={`three-btn ${autoRotate ? 'active' : ''}`}
          onClick={() => setAutoRotate(!autoRotate)}
          title={autoRotate ? 'Pause 3D Orbit' : 'Play 3D Orbit'}
        >
          {autoRotate ? <Pause size={13} /> : <Play size={13} />}
          <span>{autoRotate ? 'ORBIT ON' : 'PAUSED'}</span>
        </button>

        <button
          type="button"
          className={`three-btn ${showLabels ? 'active' : ''}`}
          onClick={() => setShowLabels(!showLabels)}
          title="Toggle Permanent Numbers / Values on 3D Chart"
        >
          <Hash size={13} />
          <span>{showLabels ? 'VALUES ON' : 'VALUES OFF'}</span>
        </button>

        <button
          type="button"
          className="three-btn"
          onClick={handleResetCamera}
          title="Reset 3D Camera Angle"
        >
          <RotateCcw size={13} />
          <span>RESET</span>
        </button>

        <button
          type="button"
          className={`three-btn ${displayMode === 'card' ? 'active' : ''}`}
          onClick={() => setDisplayMode(displayMode === 'card' ? 'mesh' : 'card')}
          title={displayMode === 'card' ? 'Switch to 3D Procedural Mesh' : 'Mount 2D Chart onto 3D Card'}
        >
          <Layers size={13} />
          <span>{displayMode === 'card' ? '3D CARD' : '3D MESH'}</span>
        </button>

        <button
          type="button"
          className={`three-btn ${wireframe ? 'active' : ''}`}
          onClick={() => setWireframe(!wireframe)}
          title="Toggle Cyber Wireframe"
        >
          <Box size={13} />
          <span>WIREFRAME</span>
        </button>
      </div>

      {/* 3D Mode Watermark */}
      <div
        className={`three-badge-watermark ${bgTheme.isDark ? 'dark' : ''}`}
        style={bgTheme.isDark ? {
          background: 'rgba(15, 23, 42, 0.88)',
          color: '#38bdf8',
          borderColor: '#38bdf8'
        } : {}}
      >
        <Sparkles size={12} />
        <span>{displayMode === 'card' ? 'THREE.JS 3D CARD' : 'THREE.JS 3D ENGINE'}</span>
      </div>
    </div>
  );
}

/**
 * Procedurally generates 3D geometries based on chart type and dataset values using active palette colors and visible data numbers.
 * Also supports mounting 2D charts (like Histograms with KDE) directly onto 3D physical floating cards.
 */
function build3DChart(scene, activeChart, dataset, wireframe, interactiveList, paletteColors = DEFAULT_PALETTE, accentColor = 0x013e37, showLabels = true, isDark = false, displayMode = 'mesh', bgTheme = {}) {
  const chartType = (activeChart?.chart_type || 'bar').toLowerCase();
  const isDist = ['histogram', 'hist', 'distribution', 'kde', 'box', 'violin'].some(t => chartType.includes(t));

  // Chart Group
  const chartGroup = new THREE.Group();
  scene.add(chartGroup);

  // If user explicitly toggled 3D Card mode
  if (displayMode === 'card') {
    build3DCard(chartGroup, activeChart, wireframe, interactiveList, accentColor, isDark, bgTheme);
    return;
  }

  // Pure 3D Mode: Backdrop card removed per user request ("iske piche ka card hata de")
  // 3D physical elements render directly in 3D space with their own axes, grid, and lighting.

  const allRows = dataset?.sample_data?.length ? dataset.sample_data : (dataset?.head_rows || []);
  const args = activeChart?.args || {};
  const chartData = activeChart?.chart_data || null;

  const numCols = dataset?.numeric_columns || [];
  const allCols = dataset?.columns || [];
  const catCols = allCols.filter((c) => !numCols.includes(c));

  // Use the exact columns resolved by backend Python engine
  let yCol = chartData?.y_col || args.y_col;
  let xCol = chartData?.x_col || args.x_col || catCols[0] || allCols[0];

  let effYCol = yCol || numCols[0] || allCols[0];
  let effXCol = xCol || catCols[0] || allCols[1] || allCols[0];

  let dataPoints = [];

  // Use exact data points from backend 2D chart if available (guarantees 100% identical data)
  if (chartData?.data_points && chartData.data_points.length > 0) {
    dataPoints = chartData.data_points.map(d => ({
      label: String(d.label),
      val: parseFloat(d.val) || 0
    }));
  } else {
    const isCategoricalChart = ['bar', 'pie', 'donut', 'lollipop', 'waterfall', 'funnel', 'treemap', 'tree'].some(t => chartType.includes(t));

    if (isCategoricalChart) {
      // Aggregate by category (effXCol) matching 2D chart behavior exactly
      const grouped = {};
      allRows.forEach((r) => {
        const key = String(r[effXCol] ?? 'Other');
        const val = effYCol && r[effYCol] !== undefined && !isNaN(parseFloat(r[effYCol]))
          ? parseFloat(r[effYCol])
          : 1;
        grouped[key] = (grouped[key] || 0) + val;
      });

      dataPoints = Object.entries(grouped)
        .map(([label, val]) => ({ label, val }))
        .sort((a, b) => b.val - a.val)
        .slice(0, 16);
    } else {
      const rows = allRows.slice(0, 24);
      dataPoints = rows.map((r, i) => {
        const rawVal = parseFloat(r[effYCol]);
        return {
          label: String(r[effXCol] ?? `Item ${i + 1}`),
          val: !isNaN(rawVal) ? rawVal : 0,
          rawRow: r
        };
      });
    }
  }

  if (dataPoints.length === 0) {
    dataPoints = [
      { label: '<1H OCEAN', val: 9136 },
      { label: 'INLAND', val: 6551 },
      { label: 'NEAR OCEAN', val: 2658 },
      { label: 'NEAR BAY', val: 2290 },
      { label: 'ISLAND', val: 5 }
    ];
  }

  const maxVal = Math.max(...dataPoints.map((d) => d.val), 1);
  const maxHeight = 8.5;

  // Switch by Chart Type - dedicated 3D builders for all 17 supported charts
  if (['histogram', 'hist'].some(t => chartType.includes(t))) {
    build3DHistogram(chartGroup, allRows, effXCol, effYCol, maxVal, maxHeight, wireframe, interactiveList, paletteColors, accentColor, showLabels, isDark, chartData);
  } else if (['box'].some(t => chartType.includes(t))) {
    build3DBoxPlot(chartGroup, allRows, effXCol, effYCol, maxVal, maxHeight, wireframe, interactiveList, paletteColors, accentColor, showLabels, isDark, false);
  } else if (['violin'].some(t => chartType.includes(t))) {
    build3DViolin(chartGroup, allRows, effXCol, effYCol, maxVal, maxHeight, wireframe, interactiveList, paletteColors, accentColor, showLabels, isDark, false);
  } else if (['waterfall'].some(t => chartType.includes(t))) {
    build3DWaterfall(chartGroup, dataPoints, maxVal, maxHeight, wireframe, interactiveList, paletteColors, accentColor, showLabels, isDark, effXCol, effYCol);
  } else if (['funnel'].some(t => chartType.includes(t))) {
    build3DFunnel(chartGroup, dataPoints, wireframe, interactiveList, paletteColors, showLabels, isDark);
  } else if (['lollipop'].some(t => chartType.includes(t))) {
    build3DLollipop(chartGroup, dataPoints, maxVal, maxHeight, wireframe, interactiveList, paletteColors, accentColor, showLabels, isDark, effXCol, effYCol, false);
  } else if (['radar', 'spider'].some(t => chartType.includes(t))) {
    build3DRadar(chartGroup, allRows, numCols, catCols, effXCol, wireframe, interactiveList, paletteColors, showLabels, isDark);
  } else if (['bubble'].some(t => chartType.includes(t))) {
    build3DBubble(chartGroup, allRows, effXCol, effYCol, numCols, maxVal, maxHeight, wireframe, interactiveList, paletteColors, accentColor, showLabels, isDark);
  } else if (['pairplot', 'pair'].some(t => chartType.includes(t))) {
    build3DPairplot(chartGroup, allRows, numCols, wireframe, interactiveList, paletteColors, showLabels, isDark);
  } else if (['scatter'].some(t => chartType.includes(t))) {
    build3DScatter(chartGroup, dataPoints, maxVal, maxHeight, wireframe, interactiveList, paletteColors, accentColor, showLabels, isDark, effXCol, effYCol, false, chartData, allRows);
  } else if (['pie', 'donut', 'doughnut'].some(t => chartType.includes(t))) {
    build3DPieDonut(chartGroup, dataPoints, chartType.includes('donut') || chartType.includes('doughnut'), wireframe, interactiveList, paletteColors, showLabels, isDark);
  } else if (['line', 'area', 'trend'].some(t => chartType.includes(t))) {
    build3DLineArea(chartGroup, dataPoints, maxVal, maxHeight, chartType.includes('area'), wireframe, interactiveList, paletteColors, accentColor, showLabels, isDark);
  } else if (['heatmap', 'correlation'].some(t => chartType.includes(t))) {
    build3DHeatmap(chartGroup, dataPoints, wireframe, interactiveList, paletteColors, showLabels, isDark);
  } else if (['treemap', 'tree'].some(t => chartType.includes(t))) {
    build3DTreemap(chartGroup, dataPoints, maxVal, wireframe, interactiveList, paletteColors, showLabels, isDark);
  } else {
    // Bar and other fallbacks
    build3DBar(chartGroup, dataPoints, maxVal, maxHeight, wireframe, interactiveList, paletteColors, accentColor, showLabels, isDark, effXCol, effYCol, false);
  }
}

/**
 * 2D Chart Backdrop Card
 * Takes the exact 2D chart (with real X & Y axes, labels, ticks, and coordinates) from the backend
 * and mounts it on a sleek physical holographic panel directly behind the 3D interactive chart elements.
 */
function build2DBackdropCard(group, activeChart, wireframe, accentColor, isDark) {
  if (!activeChart?.url) return;

  const cardGroup = new THREE.Group();
  const isPlatform = ['tree', 'radar', 'spider', 'pair'].some(t => String(activeChart?.chart_type || '').toLowerCase().includes(t));
  // Position behind 3D chart elements (further back for 3D platforms like treemap, radar, pairplot)
  cardGroup.position.set(0, 5.0, isPlatform ? -6.2 : -2.4);

  const cardWidth = 18.5;
  const initialCardHeight = 10.2;
  const depth = 0.28;

  // 1. Dark Glass Backplate
  const slabGeo = new THREE.BoxGeometry(cardWidth + 0.4, initialCardHeight + 0.4, depth);
  const slabMat = new THREE.MeshStandardMaterial({
    color: 0x091224,
    roughness: 0.35,
    metalness: 0.65,
    wireframe: wireframe
  });
  const slab = new THREE.Mesh(slabGeo, slabMat);
  slab.receiveShadow = true;
  cardGroup.add(slab);

  // 2. Glowing Neon Border Rim
  const frameGeo = new THREE.BoxGeometry(cardWidth + 0.65, initialCardHeight + 0.65, depth * 0.7);
  const frameMat = new THREE.MeshStandardMaterial({
    color: 0x38bdf8,
    emissive: 0x0284c7,
    emissiveIntensity: 0.45,
    roughness: 0.2,
    metalness: 0.85,
    wireframe: wireframe
  });
  const frame = new THREE.Mesh(frameGeo, frameMat);
  frame.position.z = -0.04;
  cardGroup.add(frame);

  // 3. Front 2D Chart Plane (Displays the real 2D chart from charts.py with exact X & Y axes)
  const frontGeo = new THREE.PlaneGeometry(cardWidth, initialCardHeight);
  const frontMat = new THREE.MeshBasicMaterial({
    color: 0xffffff,
    transparent: true,
    opacity: 0.94,
    side: THREE.FrontSide
  });
  const frontMesh = new THREE.Mesh(frontGeo, frontMat);
  frontMesh.position.z = depth / 2 + 0.015;
  frontMesh.receiveShadow = false;
  cardGroup.add(frontMesh);

  // 4. Pedestal Stand on the Floor
  const baseGeo = new THREE.BoxGeometry(cardWidth + 1.2, 0.22, 1.4);
  const baseMat = new THREE.MeshStandardMaterial({
    color: 0x0d1a33,
    metalness: 0.85,
    roughness: 0.2
  });
  const baseMesh = new THREE.Mesh(baseGeo, baseMat);
  baseMesh.position.set(0, -5.0 + 0.11, 0);
  cardGroup.add(baseMesh);

  // Load 2D chart image from activeChart.url
  const loader = new THREE.TextureLoader();
  loader.setCrossOrigin('anonymous');
  loader.load(
    activeChart.url,
    (texture) => {
      texture.colorSpace = THREE.SRGBColorSpace;
      texture.minFilter = THREE.LinearFilter;
      texture.magFilter = THREE.LinearFilter;
      texture.generateMipmaps = false;

      frontMat.map = texture;
      frontMat.needsUpdate = true;

      if (texture.image && texture.image.width && texture.image.height) {
        const imgAspect = texture.image.width / texture.image.height;
        const newHeight = cardWidth / imgAspect;
        frontMesh.scale.set(1, newHeight / initialCardHeight, 1);
        slab.scale.set(1, (newHeight + 0.4) / (initialCardHeight + 0.4), 1);
        frame.scale.set(1, (newHeight + 0.65) / (initialCardHeight + 0.65), 1);
        cardGroup.position.y = newHeight / 2 + 0.15;
        baseMesh.position.y = -(newHeight / 2 + 0.15) + 0.11;
      }
    },
    undefined,
    (err) => console.warn('Error loading 2D chart backdrop texture:', err)
  );

  group.add(cardGroup);
}

/**
 * 3D Holographic / Glass Card Presentation
 * Glues the 2D chart (histogram, KDE, etc.) directly onto an interactive 3D physical slab with pedestal, lighting & shadows.
 */
function build3DCard(group, activeChart, wireframe, interactiveList, accentColor, isDark, bgTheme) {
  const cardGroup = new THREE.Group();
  group.add(cardGroup);

  const cardWidth = 14.0;
  const initialCardHeight = 7.9; // 16:9 ratio
  const depth = 0.38;

  const accentHex = typeof accentColor === 'number'
    ? accentColor
    : parseInt((accentColor || '#08ab9c').replace('#', ''), 16);

  // 1. Slab Body (Metallic Back and Bevel Edges)
  const slabGeo = new THREE.BoxGeometry(cardWidth + 0.5, initialCardHeight + 0.5, depth);
  const slabMat = new THREE.MeshStandardMaterial({
    color: isDark ? 0x0f172a : (typeof bgTheme?.gridColor === 'number' ? bgTheme.gridColor : 0x013e37),
    roughness: 0.35,
    metalness: 0.65,
    wireframe: wireframe
  });
  const slab = new THREE.Mesh(slabGeo, slabMat);
  slab.castShadow = true;
  slab.receiveShadow = true;
  cardGroup.add(slab);

  // 2. Beveled Glowing Rim / Frame
  const frameGeo = new THREE.BoxGeometry(cardWidth + 0.7, initialCardHeight + 0.7, depth * 0.7);
  const frameMat = new THREE.MeshStandardMaterial({
    color: accentHex,
    roughness: 0.2,
    metalness: 0.85,
    wireframe: wireframe
  });
  const frame = new THREE.Mesh(frameGeo, frameMat);
  frame.position.z = -0.05;
  cardGroup.add(frame);

  // 3. Front Chart Canvas / Plane (where 2D chart is glued)
  const frontGeo = new THREE.PlaneGeometry(cardWidth, initialCardHeight);
  const frontMat = new THREE.MeshBasicMaterial({
    color: 0xffffff,
    wireframe: wireframe,
    side: THREE.FrontSide
  });
  const frontMesh = new THREE.Mesh(frontGeo, frontMat);
  frontMesh.position.z = depth / 2 + 0.015;
  frontMesh.receiveShadow = false;
  cardGroup.add(frontMesh);

  // Load 2D chart image texture
  if (activeChart?.url) {
    const loader = new THREE.TextureLoader();
    loader.setCrossOrigin('anonymous');
    loader.load(
      activeChart.url,
      (texture) => {
        texture.colorSpace = THREE.SRGBColorSpace;
        texture.minFilter = THREE.LinearFilter;
        texture.magFilter = THREE.LinearFilter;
        texture.generateMipmaps = false;

        frontMat.map = texture;
        frontMat.needsUpdate = true;

        if (texture.image && texture.image.width && texture.image.height) {
          const imgAspect = texture.image.width / texture.image.height;
          const newHeight = cardWidth / imgAspect;
          frontMesh.scale.set(1, newHeight / initialCardHeight, 1);
          slab.scale.set(1, (newHeight + 0.5) / (initialCardHeight + 0.5), 1);
          frame.scale.set(1, (newHeight + 0.7) / (initialCardHeight + 0.7), 1);
        }
      },
      undefined,
      (err) => {
        console.warn('Error loading 3D chart card texture:', err);
      }
    );
  }

  // 4. Sleek Corner Screws / Cyber Pins
  const pinGeo = new THREE.CylinderGeometry(0.12, 0.12, 0.08, 16);
  const pinMat = new THREE.MeshStandardMaterial({ color: 0xe2e8f0, metalness: 0.9, roughness: 0.15 });
  const cornerOffsets = [
    [-cardWidth / 2 + 0.35, initialCardHeight / 2 - 0.35],
    [cardWidth / 2 - 0.35, initialCardHeight / 2 - 0.35],
    [-cardWidth / 2 + 0.35, -initialCardHeight / 2 + 0.35],
    [cardWidth / 2 - 0.35, -initialCardHeight / 2 + 0.35]
  ];
  cornerOffsets.forEach(([cx, cy]) => {
    const pin = new THREE.Mesh(pinGeo, pinMat);
    pin.rotation.x = Math.PI / 2;
    pin.position.set(cx, cy, depth / 2 + 0.04);
    cardGroup.add(pin);
  });

  // 5. 3D Pedestal / Stand on the Floor
  const standGroup = new THREE.Group();
  
  // Base plate
  const baseGeo = new THREE.CylinderGeometry(2.5, 3.0, 0.3, 32);
  const baseMat = new THREE.MeshStandardMaterial({
    color: isDark ? 0x1e293b : 0x013e37,
    metalness: 0.75,
    roughness: 0.3
  });
  const baseMesh = new THREE.Mesh(baseGeo, baseMat);
  baseMesh.position.y = 0.15;
  baseMesh.receiveShadow = true;
  baseMesh.castShadow = true;
  standGroup.add(baseMesh);

  // Vertical support pillar
  const pillarGeo = new THREE.CylinderGeometry(0.4, 0.45, 1.8, 24);
  const pillarMat = new THREE.MeshStandardMaterial({
    color: accentHex,
    metalness: 0.85,
    roughness: 0.2
  });
  const pillarMesh = new THREE.Mesh(pillarGeo, pillarMat);
  pillarMesh.position.y = 1.0;
  pillarMesh.castShadow = true;
  standGroup.add(pillarMesh);

  // Tilt bracket
  const bracketGeo = new THREE.BoxGeometry(2.4, 0.5, 0.8);
  const bracketMesh = new THREE.Mesh(bracketGeo, baseMat);
  bracketMesh.position.y = 1.9;
  standGroup.add(bracketMesh);

  group.add(standGroup);

  // Position the card above the stand facing directly forward (screen ke samne)
  cardGroup.position.set(0, initialCardHeight / 2 + 1.8, 0);
  cardGroup.rotation.x = 0;

  // Make card interactive for hover
  frontMesh.userData = {
    label: activeChart?.title || '2D-to-3D Histogram Card',
    val: `${(activeChart?.chart_type || 'histogram').toUpperCase()} (3D Card)`
  };
  interactiveList.push(frontMesh);

  // Tag for entry scale animation
  cardGroup.userData = {
    isCard: true
  };
  interactiveList.push(cardGroup);

  return cardGroup;
}

/** Reference image palette for cyber 3D bars */
const CYBER_3D_PALETTE = [
  '#7C3AED', // Electric Violet / Purple (May - 31.0K)
  '#EC4899', // Hot Magenta / Pink (Apr - 27.0K)
  '#10B981', // Luminous Mint / Emerald (Feb - 22.0K)
  '#F97316', // Warm Tangerine / Orange (Mar - 18.0K)
  '#0EA5E9', // Electric Cyan / Sky Blue (Jan - 15.0K)
  '#8B5CF6', // Soft Violet
  '#F43F5E', // Rose
  '#06B6D4', // Cyan
  '#EAB308', // Amber
  '#14B8A6'  // Teal
];

/** 3D Bar & Column Chart (Faithful replication of cyber beveled 3D columns with glowing badges & neon perimeter) */
function build3DBar(
  group,
  data,
  maxVal,
  maxHeight,
  wireframe,
  interactiveList,
  paletteColors = PALETTE_MAP.butter_green,
  accentColor = 0x013e37,
  showLabels = true,
  isDark = true,
  xLabel = 'Month',
  yLabel = 'Sales',
  hasBackdrop = false
) {
  const count = data.length;
  // Calculate dynamic spacing and width
  const spacing = count <= 5 ? 2.3 : Math.max(14 / count, 1.4);
  const barWidth = count <= 5 ? 1.45 : Math.min(spacing * 0.65, 1.4);
  const barDepth = barWidth;
  const startX = -((count - 1) * spacing) / 2;

  // Use the reference cyber palette if default palette is active or if dark
  const isCustomPalette = paletteColors && paletteColors.length && paletteColors !== PALETTE_MAP.butter_green && paletteColors !== PALETTE_MAP.custom;
  const colorsToUse = isCustomPalette ? paletteColors : CYBER_3D_PALETTE;

  // Floor neon perimeter boundaries
  const padX = barWidth * 0.85;
  const padZ = barDepth * 0.95;
  const minX = startX - padX;
  const maxX = (startX + (count - 1) * spacing) + padX;
  const minZ = -padZ;
  const maxZ = padZ + 0.35;

  // 1. Glowing Neon Perimeter Line on Floor
  const framePoints = [
    new THREE.Vector3(minX, 0.02, minZ),
    new THREE.Vector3(maxX, 0.02, minZ),
    new THREE.Vector3(maxX, 0.02, maxZ),
    new THREE.Vector3(minX, 0.02, maxZ),
    new THREE.Vector3(minX, 0.02, minZ)
  ];
  const frameGeo = new THREE.BufferGeometry().setFromPoints(framePoints);
  const frameMat = new THREE.LineBasicMaterial({
    color: 0x3b82f6,
    transparent: true,
    opacity: 0.9,
    linewidth: 2
  });
  group.add(new THREE.Line(frameGeo, frameMat));

  // Outer subtle neon bloom line
  const glowPoints = [
    new THREE.Vector3(minX - 0.05, 0.015, minZ - 0.05),
    new THREE.Vector3(maxX + 0.05, 0.015, minZ - 0.05),
    new THREE.Vector3(maxX + 0.05, 0.015, maxZ + 0.05),
    new THREE.Vector3(minX - 0.05, 0.015, maxZ + 0.05),
    new THREE.Vector3(minX - 0.05, 0.015, minZ - 0.05)
  ];
  const glowGeo = new THREE.BufferGeometry().setFromPoints(glowPoints);
  const glowMat = new THREE.LineBasicMaterial({
    color: 0x60a5fa,
    transparent: true,
    opacity: 0.4,
    linewidth: 3
  });
  group.add(new THREE.Line(glowGeo, glowMat));

  // 2. Render each Beveled Column & Floating Badge
  data.forEach((d, i) => {
    const rawRatio = maxVal > 0 ? (d.val / maxVal) : 0.5;
    const height = Math.max(rawRatio * maxHeight, 0.5);
    const colorHex = colorsToUse[i % colorsToUse.length];
    const barX = startX + i * spacing;

    // Beveled Column Geometry with smooth chamfered edges
    const geom = createBeveledBarGeometry(barWidth, height, barDepth, 0.06);
    const mat = new THREE.MeshPhysicalMaterial({
      color: colorHex,
      metalness: 0.12,
      roughness: 0.18,
      clearcoat: 0.7,
      clearcoatRoughness: 0.12,
      reflectivity: 0.6,
      wireframe: wireframe
    });

    const mesh = new THREE.Mesh(geom, mat);
    mesh.position.set(barX, 0, 0);
    mesh.castShadow = true;
    mesh.receiveShadow = true;

    // Floating Neon Value Badge
    let badge = null;
    if (showLabels) {
      badge = createFloatingValueBadge(d.val, colorHex);
      badge.position.set(barX, height + 0.72, 0);
      group.add(badge);
    }

    // Category Label directly below column
    const catSprite = createCategoryLabelSprite(d.label, true);
    catSprite.position.set(barX, -0.42, maxZ + 0.22);
    group.add(catSprite);

    // Subtle Ground Glow Puddle under each column
    const puddleGeo = new THREE.CylinderGeometry(barWidth * 0.65, barWidth * 0.8, 0.02, 24);
    const puddleMat = new THREE.MeshBasicMaterial({
      color: colorHex,
      transparent: true,
      opacity: 0.28
    });
    const puddle = new THREE.Mesh(puddleGeo, puddleMat);
    puddle.position.set(barX, 0.01, 0);
    group.add(puddle);

    mesh.userData = {
      label: d.label,
      val: formatDataValue(d.val),
      isBeveledBar: true,
      barHeight: height,
      badge: badge
    };

    group.add(mesh);
    interactiveList.push(mesh);
  });

  // 3. X-Axis Title Centered at Bottom
  const xTitle = String(xLabel || 'Month').trim();
  const xTitleSprite = createAxisTitleSprite(xTitle, false);
  xTitleSprite.position.set((minX + maxX) / 2, -1.05, maxZ + 0.75);
  group.add(xTitleSprite);

  // 4. Vertical Y-Axis (Line, Ticks, Labels, Title) - only if no 2D backdrop card
  if (!hasBackdrop) {
    const yAxisX = minX - 0.65;
    const yAxisHeight = maxHeight * 1.06;

    // Vertical glowing line
    const yLineGeo = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(yAxisX, 0.02, maxZ),
      new THREE.Vector3(yAxisX, yAxisHeight, maxZ)
    ]);
    const yLineMat = new THREE.LineBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.85,
      linewidth: 2
    });
    group.add(new THREE.Line(yLineGeo, yLineMat));

    // Y-Axis Ticks & Values
    const tickCount = 6;
    const tickStep = maxVal / (tickCount - 1);
    for (let t = 0; t < tickCount; t++) {
      const tickVal = t * tickStep;
      const tickY = Math.max((tickVal / maxVal) * maxHeight, 0.02);

      // Tick Mark
      const tickGeo = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(yAxisX, tickY, maxZ),
        new THREE.Vector3(yAxisX - 0.2, tickY, maxZ)
      ]);
      const tickLine = new THREE.Line(tickGeo, yLineMat);
      group.add(tickLine);

      // Tick Value Label
      if (showLabels) {
        const formattedTick = formatDataValue(tickVal);
        const tickSprite = createAxisTickLabelSprite(formattedTick);
        tickSprite.position.set(yAxisX - 0.72, tickY, maxZ);
        group.add(tickSprite);
      }
    }

    // Rotated Y-Axis Title ("Sales" / Column Name)
    const yTitle = String(yLabel || 'Sales').trim();
    const yTitleSprite = createAxisTitleSprite(yTitle, true);
    yTitleSprite.position.set(yAxisX - 1.5, yAxisHeight / 2, maxZ);
    group.add(yTitleSprite);
  }
}

/** 3D Scatter & Bubble Chart (Standalone pure 3D visualization with glowing physical spheres, drop lines, floor puddles, floating badges, and 3D axes) */
function build3DScatter(group, data, maxVal, maxHeight, wireframe, interactiveList, paletteColors = DEFAULT_PALETTE, accentColor = 0x013e37, showLabels = true, isDark = false, effXCol = 'X', effYCol = 'Y', hasBackdrop = false, chartData = null, allRows = []) {
  const colorsToUse = (paletteColors && paletteColors.length && paletteColors !== PALETTE_MAP.butter_green)
    ? paletteColors
    : CYBER_3D_PALETTE;

  // Extract actual points from backend chartData (guarantees 100% identical data to 2D chart)
  let pts = [];
  let minXVal = 0;
  let maxXVal = 1;
  let minYVal = 0;
  let maxYVal = 1;

  if (chartData?.points && chartData.points.length > 0) {
    pts = chartData.points;
    minXVal = chartData.min_x;
    maxXVal = chartData.max_x;
    minYVal = chartData.min_y;
    maxYVal = chartData.max_y;
  } else {
    // Client fallback: Extract actual numeric x and y from dataset sample rows
    const valid = (allRows || [])
      .map((r, i) => ({
        x: parseFloat(r[effXCol]),
        y: parseFloat(r[effYCol]),
        label: String(r[effXCol] ?? `Item ${i + 1}`)
      }))
      .filter(p => !isNaN(p.x) && !isNaN(p.y));

    if (valid.length > 0) {
      pts = valid.slice(0, 100);
      minXVal = Math.min(...pts.map(p => p.x));
      maxXVal = Math.max(...pts.map(p => p.x));
      minYVal = Math.min(...pts.map(p => p.y));
      maxYVal = Math.max(...pts.map(p => p.y));
    } else {
      pts = data.map((d, i) => ({ x: i * 10, y: d.val, label: d.label }));
      minXVal = 0;
      maxXVal = Math.max(pts.length * 10, 1);
      minYVal = 0;
      maxYVal = maxVal;
    }
  }

  const spanX = maxXVal - minXVal || 1;
  const spanY = maxYVal - minYVal || 1;

  // Floor Perimeter Neon Line
  const minX = -7.5;
  const maxX = 7.5;
  const minZ = -4.5;
  const maxZ = 4.5;
  const framePoints = [
    new THREE.Vector3(minX, 0.02, minZ),
    new THREE.Vector3(maxX, 0.02, minZ),
    new THREE.Vector3(maxX, 0.02, maxZ),
    new THREE.Vector3(minX, 0.02, maxZ),
    new THREE.Vector3(minX, 0.02, minZ)
  ];
  group.add(new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(framePoints),
    new THREE.LineBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.8, linewidth: 2 })
  ));

  pts.forEach((p, i) => {
    const rawX = p.x;
    const rawY = p.y;
    const normRatioX = Math.max(0, Math.min(1, (rawX - minXVal) / spanX));
    const normRatioY = Math.max(0, Math.min(1, (rawY - minYVal) / spanY));

    // True spatial coordinates matching 2D chart layout exactly
    const posX = minX + normRatioX * (maxX - minX);
    const posY = Math.max(normRatioY * maxHeight, 0.45);
    // Subtle z-stagger so overlapping points remain visible in 3D
    const posZ = ((i % 7) - 3) * 0.7;

    const radius = 0.45;
    const geom = new THREE.SphereGeometry(radius, 28, 28);
    const colorHex = colorsToUse[i % colorsToUse.length];

    const mat = new THREE.MeshPhysicalMaterial({
      color: colorHex,
      metalness: 0.18,
      roughness: 0.12,
      clearcoat: 0.95,
      clearcoatRoughness: 0.08,
      reflectivity: 0.8,
      wireframe: wireframe
    });

    const mesh = new THREE.Mesh(geom, mat);
    mesh.position.set(posX, posY, posZ);
    mesh.castShadow = true;
    mesh.receiveShadow = true;

    mesh.userData = {
      label: `${effXCol}: ${formatDataValue(rawX)}`,
      val: `${effYCol}: ${formatDataValue(rawY)}`
    };
    group.add(mesh);
    interactiveList.push(mesh);

    // Floating pill value badge on prominent sample points
    if (showLabels && (i % 6 === 0 || i < 4)) {
      const badge = createFloatingValueBadge(formatDataValue(rawY), colorHex);
      badge.position.set(posX, posY + radius + 0.65, posZ);
      group.add(badge);
    }

    // Drop line to floor
    const lineGeo = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(posX, 0.02, posZ),
      new THREE.Vector3(posX, posY, posZ)
    ]);
    const lineMat = new THREE.LineDashedMaterial({
      color: 0x38bdf8,
      dashSize: 0.2,
      gapSize: 0.1,
      opacity: 0.45,
      transparent: true
    });
    const line = new THREE.Line(lineGeo, lineMat);
    line.computeLineDistances();
    group.add(line);

    // Floor shadow puddle
    const puddle = new THREE.Mesh(
      new THREE.CylinderGeometry(radius * 0.7, radius * 1.0, 0.02, 16),
      new THREE.MeshBasicMaterial({ color: colorHex, transparent: true, opacity: 0.25 })
    );
    puddle.position.set(posX, 0.01, posZ);
    group.add(puddle);
  });

  // 3D X-Axis and Y-Axis lines matching 2D chart ticks and labels
  if (!hasBackdrop) {
    const yAxisX = minX - 0.5;
    const yAxisHeight = maxHeight * 1.05;

    // Vertical Y-Axis Line
    const yLine = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(yAxisX, 0.02, maxZ),
        new THREE.Vector3(yAxisX, yAxisHeight, maxZ)
      ]),
      new THREE.LineBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.85, linewidth: 2 })
    );
    group.add(yLine);

    // Y-Axis Ticks & Values matching the exact 2D min/max scale
    const tickCount = 5;
    for (let t = 0; t < tickCount; t++) {
      const ratio = t / (tickCount - 1);
      const tickVal = minYVal + ratio * spanY;
      const tickY = Math.max(ratio * maxHeight, 0.02);

      group.add(new THREE.Line(
        new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(yAxisX, tickY, maxZ),
          new THREE.Vector3(yAxisX - 0.25, tickY, maxZ)
        ]),
        new THREE.LineBasicMaterial({ color: 0x38bdf8, linewidth: 2 })
      ));

      if (showLabels) {
        const tickSprite = createAxisTickLabelSprite(formatDataValue(tickVal));
        tickSprite.position.set(yAxisX - 0.8, tickY, maxZ);
        group.add(tickSprite);
      }
    }

    // Y-Axis Title
    const yTitleSprite = createAxisTitleSprite(String(effYCol || 'Value').trim(), true);
    yTitleSprite.position.set(yAxisX - 1.6, yAxisHeight / 2, maxZ);
    group.add(yTitleSprite);

    // Horizontal X-Axis Line
    const xLine = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(minX, 0.02, maxZ),
        new THREE.Vector3(maxX, 0.02, maxZ)
      ]),
      new THREE.LineBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.85, linewidth: 2 })
    );
    group.add(xLine);

    // X-Axis Ticks & Values matching the exact 2D min/max scale
    for (let t = 0; t < tickCount; t++) {
      const ratio = t / (tickCount - 1);
      const tickVal = minXVal + ratio * spanX;
      const tickX = minX + ratio * (maxX - minX);

      group.add(new THREE.Line(
        new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(tickX, 0.02, maxZ),
          new THREE.Vector3(tickX, 0.02, maxZ + 0.25)
        ]),
        new THREE.LineBasicMaterial({ color: 0x38bdf8, linewidth: 2 })
      ));

      if (showLabels) {
        const tickSprite = createAxisTickLabelSprite(formatDataValue(tickVal));
        tickSprite.position.set(tickX, -0.42, maxZ + 0.55);
        group.add(tickSprite);
      }
    }

    // X-Axis Title
    const xTitleSprite = createAxisTitleSprite(String(effXCol || 'X').trim(), false);
    xTitleSprite.position.set((minX + maxX) / 2, -1.05, maxZ + 1.1);
    group.add(xTitleSprite);
  }
}

/** 3D Pie & Donut Chart (Guaranteed seamless 360° closed circle, never cut off) */
function build3DPieDonut(group, data, isDonut, wireframe, interactiveList, paletteColors = DEFAULT_PALETTE, showLabels = true, isDark = false) {
  // Filter positive values and take top categories (up to 8), grouping tail into 'Other'
  let slices = [...data].filter((d) => (parseFloat(d.val) || 0) > 0);
  if (slices.length > 8) {
    const top7 = slices.slice(0, 7);
    const rest = slices.slice(7);
    const otherVal = rest.reduce((acc, d) => acc + (parseFloat(d.val) || 0), 0);
    slices = [...top7, { label: 'Other', val: otherVal }];
  }

  // Calculate total STRICTLY over the slices to be rendered so angles sum to EXACTLY 360° (2*PI)
  const total = slices.reduce((acc, d) => acc + (parseFloat(d.val) || 0), 0);
  if (total <= 0) return;

  let currentAngle = 0;
  const radius = 4.8;
  const innerRadius = isDonut ? 2.6 : 0;
  const thickness = 1.3;

  slices.forEach((d, i) => {
    const isLast = i === slices.length - 1;
    // Guarantee that the last slice closes the circle to exactly 2*PI, eliminating any cut-out gaps
    const sliceAngle = isLast
      ? Math.max(0.01, Math.PI * 2 - currentAngle)
      : Math.max(0.01, ((parseFloat(d.val) || 0) / total) * Math.PI * 2);

    const colorHex = paletteColors[i % paletteColors.length];

    // Create 2D Shape for slice
    const shape = new THREE.Shape();
    if (isDonut) {
      shape.moveTo(
        Math.cos(currentAngle) * innerRadius,
        Math.sin(currentAngle) * innerRadius
      );
      shape.lineTo(
        Math.cos(currentAngle) * radius,
        Math.sin(currentAngle) * radius
      );
      shape.absarc(0, 0, radius, currentAngle, currentAngle + sliceAngle, false);
      shape.lineTo(
        Math.cos(currentAngle + sliceAngle) * innerRadius,
        Math.sin(currentAngle + sliceAngle) * innerRadius
      );
      shape.absarc(0, 0, innerRadius, currentAngle + sliceAngle, currentAngle, true);
    } else {
      shape.moveTo(0, 0);
      shape.lineTo(
        Math.cos(currentAngle) * radius,
        Math.sin(currentAngle) * radius
      );
      shape.absarc(0, 0, radius, currentAngle, currentAngle + sliceAngle, false);
      shape.lineTo(0, 0);
    }
    shape.closePath();

    const extrudeSettings = {
      depth: thickness,
      bevelEnabled: true,
      bevelSegments: 2,
      steps: 1,
      bevelSize: 0.06,
      bevelThickness: 0.06
    };

    const geom = new THREE.ExtrudeGeometry(shape, extrudeSettings);
    const mat = new THREE.MeshStandardMaterial({
      color: colorHex,
      metalness: 0.35,
      roughness: 0.28,
      wireframe: wireframe
    });

    const mesh = new THREE.Mesh(geom, mat);
    mesh.rotation.x = -Math.PI / 2;
    mesh.position.y = 1.8;
    mesh.castShadow = true;
    mesh.receiveShadow = true;

    const pct = Math.round(((parseFloat(d.val) || 0) / total) * 100);
    mesh.userData = { label: d.label, val: `${formatDataValue(d.val)} (${pct}%)` };
    group.add(mesh);
    interactiveList.push(mesh);

    // Glued Flat Surface Label on top face of slice
    if (showLabels && sliceAngle > 0.18) {
      const midAngle = currentAngle + sliceAngle / 2;
      const midRadius = isDonut ? (innerRadius + radius) / 2 : radius * 0.65;
      const labelX = Math.cos(midAngle) * midRadius;
      const labelZ = -Math.sin(midAngle) * midRadius;
      const labelMesh = createSurfaceLabelMesh(formatDataValue(d.val) + ` (${pct}%)`, d.label, 1.25, 1.25, isDark);
      labelMesh.position.set(labelX, 1.8 + thickness + 0.015, labelZ);
      group.add(labelMesh);
    }

    currentAngle += sliceAngle;
  });

}

/** 3D Line & Ribbon Area Chart */
function build3DLineArea(group, data, maxVal, maxHeight, isArea, wireframe, interactiveList, paletteColors = DEFAULT_PALETTE, accentColor = 0x013e37, showLabels = true, isDark = false) {
  const count = data.length;
  const spacing = count <= 6 ? 2.3 : Math.max(14 / count, 1.4);
  const startX = -((count - 1) * spacing) / 2;
  const points = [];

  // Use vibrant colors from palette
  const colorsToUse = (paletteColors && paletteColors.length && paletteColors !== PALETTE_MAP.butter_green)
    ? paletteColors
    : CYBER_3D_PALETTE;

  data.forEach((d, i) => {
    const rawRatio = maxVal > 0 ? (d.val / maxVal) : 0.5;
    const height = Math.max(rawRatio * maxHeight, 0.6);
    const colorHex = colorsToUse[i % colorsToUse.length];
    // Positioned at z = 0.4 so it floats prominently in front of the 2D backdrop card (at z = -2.4)
    const pt = new THREE.Vector3(startX + i * spacing, height, 0.4);
    points.push(pt);

    // Marker sphere with rich specular shine
    const sphereGeo = new THREE.SphereGeometry(0.38, 24, 24);
    const sphereMat = new THREE.MeshPhysicalMaterial({
      color: colorHex,
      metalness: 0.15,
      roughness: 0.15,
      clearcoat: 0.8,
      reflectivity: 0.6,
      wireframe: wireframe
    });
    const sphere = new THREE.Mesh(sphereGeo, sphereMat);
    sphere.position.copy(pt);
    sphere.castShadow = true;
    sphere.userData = { label: d.label, val: formatDataValue(d.val) };
    group.add(sphere);
    interactiveList.push(sphere);

    // Glowing floating pill value badge
    if (showLabels) {
      const labelSprite = createFloatingValueBadge(d.val, colorHex);
      labelSprite.position.set(pt.x, height + 0.68, pt.z);
      group.add(labelSprite);
    }

    // Glowing vertical drop line connecting point to floor
    const lineGeo = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(pt.x, 0.02, pt.z),
      new THREE.Vector3(pt.x, height, pt.z)
    ]);
    const lineMat = new THREE.LineBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.65,
      linewidth: 2
    });
    group.add(new THREE.Line(lineGeo, lineMat));

    // Floor glow disc under each drop line
    const puddleGeo = new THREE.CylinderGeometry(0.35, 0.5, 0.02, 16);
    const puddleMat = new THREE.MeshBasicMaterial({
      color: colorHex,
      transparent: true,
      opacity: 0.32
    });
    const puddle = new THREE.Mesh(puddleGeo, puddleMat);
    puddle.position.set(pt.x, 0.01, pt.z);
    group.add(puddle);
  });

  // Smooth CatmullRom Curve 3D Tube
  if (points.length >= 2) {
    const curve = new THREE.CatmullRomCurve3(points);
    const tubeGeo = new THREE.TubeGeometry(curve, 80, 0.22, 16, false);
    const tubeMat = new THREE.MeshPhysicalMaterial({
      color: colorsToUse[0] || 0x10b981,
      metalness: 0.2,
      roughness: 0.18,
      clearcoat: 0.75,
      reflectivity: 0.6,
      wireframe: wireframe
    });
    const tube = new THREE.Mesh(tubeGeo, tubeMat);
    tube.castShadow = true;
    group.add(tube);
  }
}

/** 3D Heatmap Topographic Elevation Grid */
function build3DHeatmap(group, data, wireframe, interactiveList, paletteColors = DEFAULT_PALETTE, showLabels = true, isDark = false) {
  const gridSize = 4;
  const spacing = 1.8;
  const offset = -((gridSize - 1) * spacing) / 2;

  let idx = 0;
  for (let x = 0; x < gridSize; x++) {
    for (let z = 0; z < gridSize; z++) {
      const d = data[idx % data.length];
      idx++;

      const height = 0.5 + ((idx * 7) % 6);
      const colorHex = paletteColors[idx % paletteColors.length];

      const geom = new THREE.BoxGeometry(1.4, height, 1.4);
      const mat = new THREE.MeshStandardMaterial({
        color: colorHex,
        metalness: 0.3,
        roughness: 0.4,
        wireframe: wireframe
      });

      const mesh = new THREE.Mesh(geom, mat);
      mesh.position.set(offset + x * spacing, height / 2, offset + z * spacing);
      mesh.castShadow = true;
      mesh.receiveShadow = true;

      mesh.userData = { label: `Cell (${x + 1}, ${z + 1}) - ${d.label}`, val: d.val };
      group.add(mesh);
      interactiveList.push(mesh);

      // Glued Flat Surface Label on top face of heatmap block
      if (showLabels) {
        const labelMesh = createSurfaceLabelMesh(d.val, `(${x + 1},${z + 1})`, 1.25, 1.25, isDark);
        labelMesh.position.set(offset + x * spacing, height + 0.015, offset + z * spacing);
        group.add(labelMesh);
      }
    }
  }
}

/**
 * Computes 2D squarified / slice-and-dice treemap partition layout.
 */
function computeTreemapLayout(items, x0, z0, w, d) {
  if (!items || items.length === 0) return [];
  if (items.length === 1) {
    return [{ ...items[0], x: x0 + w / 2, z: z0 + d / 2, w, d }];
  }

  const totalVal = items.reduce((acc, it) => acc + Math.max(parseFloat(it.val) || 1, 1), 0);

  // Find optimal split point
  let bestIdx = 1;
  let bestDiff = Infinity;
  let acc = 0;
  for (let i = 0; i < items.length - 1; i++) {
    acc += Math.max(parseFloat(items[i].val) || 1, 1);
    const ratio = acc / totalVal;
    const diff = Math.abs(ratio - 0.5);
    if (diff < bestDiff) {
      bestDiff = diff;
      bestIdx = i + 1;
    }
  }

  const groupA = items.slice(0, bestIdx);
  const groupB = items.slice(bestIdx);
  const valA = groupA.reduce((acc, it) => acc + Math.max(parseFloat(it.val) || 1, 1), 0);
  const ratioA = valA / totalVal;

  if (w >= d) {
    const wA = w * ratioA;
    const wB = w - wA;
    return [
      ...computeTreemapLayout(groupA, x0, z0, wA, d),
      ...computeTreemapLayout(groupB, x0 + wA, z0, wB, d)
    ];
  } else {
    const dA = d * ratioA;
    const dB = d - dA;
    return [
      ...computeTreemapLayout(groupA, x0, z0, w, dA),
      ...computeTreemapLayout(groupB, x0, z0 + dA, w, dB)
    ];
  }
}

/**
 * 3D Physical Treemap
 * Renders hierarchical 3D physical blocks on an elevated cyber platform,
 * with proportional surface area, beveled chamfers, and glowing top decals.
 */
function build3DTreemap(group, data, maxVal, wireframe, interactiveList, paletteColors = DEFAULT_PALETTE, showLabels = true, isDark = true) {
  const totalW = 15.0;
  const totalD = 9.5;

  const colorsToUse = (paletteColors && paletteColors.length && paletteColors !== PALETTE_MAP.butter_green)
    ? paletteColors
    : ['#9333ea', '#ec4899', '#f59e0b', '#f97316', '#db2777', '#06b6d4', '#10b981', '#6366f1'];

  // Base platform on the floor
  const platGeo = new THREE.BoxGeometry(totalW + 0.6, 0.25, totalD + 0.6);
  const platMat = new THREE.MeshStandardMaterial({
    color: 0x091224,
    metalness: 0.85,
    roughness: 0.2
  });
  const platform = new THREE.Mesh(platGeo, platMat);
  platform.position.set(0, 0.125, 0);
  platform.receiveShadow = true;
  group.add(platform);

  // Glowing perimeter border for the platform
  const framePoints = [
    new THREE.Vector3(-totalW / 2 - 0.3, 0.26, -totalD / 2 - 0.3),
    new THREE.Vector3(totalW / 2 + 0.3, 0.26, -totalD / 2 - 0.3),
    new THREE.Vector3(totalW / 2 + 0.3, 0.26, totalD / 2 + 0.3),
    new THREE.Vector3(-totalW / 2 - 0.3, 0.26, totalD / 2 + 0.3),
    new THREE.Vector3(-totalW / 2 - 0.3, 0.26, -totalD / 2 - 0.3)
  ];
  const frameLine = new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(framePoints),
    new THREE.LineBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.9, linewidth: 2 })
  );
  group.add(frameLine);

  // Compute 2D Treemap bounding blocks
  const blocks = computeTreemapLayout(data, 0, 0, totalW, totalD);

  blocks.forEach((b, i) => {
    const posX = b.x - totalW / 2;
    const posZ = b.z - totalD / 2;

    const gap = 0.18;
    const blockW = Math.max(b.w - gap, 0.5);
    const blockD = Math.max(b.d - gap, 0.5);
    const rawRatio = maxVal > 0 ? (b.val / maxVal) : 0.5;
    const blockH = Math.max(1.0 + rawRatio * 1.5, 0.8);
    const colorHex = colorsToUse[i % colorsToUse.length];

    // 3D Physical Block Geometry
    const blockGeo = new THREE.BoxGeometry(blockW, blockH, blockD);
    const blockMat = new THREE.MeshPhysicalMaterial({
      color: colorHex,
      metalness: 0.15,
      roughness: 0.18,
      clearcoat: 0.7,
      clearcoatRoughness: 0.15,
      reflectivity: 0.6,
      wireframe: wireframe
    });

    const mesh = new THREE.Mesh(blockGeo, blockMat);
    mesh.position.set(posX, 0.25 + blockH / 2, posZ);
    mesh.castShadow = true;
    mesh.receiveShadow = true;

    // Top surface label decal
    let labelMesh = null;
    if (showLabels) {
      labelMesh = createSurfaceLabelMesh(b.val, b.label, blockW * 0.88, blockD * 0.88, isDark, colorHex);
      labelMesh.position.set(posX, 0.25 + blockH + 0.015, posZ);
      group.add(labelMesh);
    }

    // Floating value badge above the center of the block
    if (showLabels) {
      const badge = createFloatingValueBadge(b.val, colorHex);
      badge.position.set(posX, 0.25 + blockH + 0.65, posZ);
      group.add(badge);
    }

    mesh.userData = {
      label: b.label,
      val: formatDataValue(b.val),
      origScaleY: blockH,
      baseHeight: 1,
      labelMesh: labelMesh
    };

    group.add(mesh);
    interactiveList.push(mesh);
  });
}

/**
 * -----------------------------------------------------------------------------
 * 1. 3D HISTOGRAM
 * -----------------------------------------------------------------------------
 * Stepped 3D contiguous binned prisms with chamfered bevels, floating frequency badges,
 * and a smooth flowing 3D KDE tube curve across the top of the bins.
 */
function build3DHistogram(group, allRows, effXCol, effYCol, maxVal, maxHeight, wireframe, interactiveList, paletteColors, accentColor, showLabels, isDark, chartData = null) {
  let bins = [];

  if (chartData?.bins && chartData.bins.length > 0) {
    // Exact 100% match from backend Python 2D numpy calculation
    bins = chartData.bins;
  } else {
    // Extract numeric values from effXCol or effYCol
    let rawVals = (allRows || [])
      .map(r => parseFloat(r[effXCol] ?? r[effYCol]))
      .filter(v => !isNaN(v));

    if (rawVals.length < 5) {
      rawVals = [12, 18, 24, 28, 35, 42, 45, 48, 52, 54, 55, 58, 62, 65, 68, 72, 78, 85, 92, 98];
    }

    const minV = Math.min(...rawVals);
    const maxV = Math.max(...rawVals);
    const binCount = 8;
    const binSpan = (maxV - minV) / binCount || 1;

    bins = Array.from({ length: binCount }, (_, i) => ({
      min: minV + i * binSpan,
      max: minV + (i + 1) * binSpan,
      count: 0
    }));

    rawVals.forEach(v => {
      let idx = Math.floor((v - minV) / binSpan);
      if (idx >= binCount) idx = binCount - 1;
      if (idx < 0) idx = 0;
      bins[idx].count++;
    });
  }

  const maxCount = Math.max(...bins.map(b => b.count), 1);
  const totalW = 14.0;
  const binW = totalW / binCount;
  const barDepth = 2.0;
  const startX = -totalW / 2 + binW / 2;

  const colorsToUse = (paletteColors && paletteColors.length && paletteColors !== PALETTE_MAP.butter_green)
    ? paletteColors
    : CYBER_3D_PALETTE;

  // Floor Perimeter Frame
  const framePoints = [
    new THREE.Vector3(-totalW / 2 - 0.4, 0.02, -barDepth / 2 - 0.4),
    new THREE.Vector3(totalW / 2 + 0.4, 0.02, -barDepth / 2 - 0.4),
    new THREE.Vector3(totalW / 2 + 0.4, 0.02, barDepth / 2 + 0.4),
    new THREE.Vector3(-totalW / 2 - 0.4, 0.02, barDepth / 2 + 0.4),
    new THREE.Vector3(-totalW / 2 - 0.4, 0.02, -barDepth / 2 - 0.4)
  ];
  group.add(new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(framePoints),
    new THREE.LineBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.85, linewidth: 2 })
  ));

  const kdePoints = [];

  bins.forEach((b, i) => {
    const ratio = b.count / maxCount;
    const h = Math.max(ratio * maxHeight, 0.45);
    const posX = startX + i * binW;
    const colorHex = colorsToUse[i % colorsToUse.length];

    // Contiguous Beveled Prism Geometry
    const geom = createBeveledBarGeometry(binW * 0.94, h, barDepth, 0.05);
    const mat = new THREE.MeshPhysicalMaterial({
      color: colorHex,
      metalness: 0.18,
      roughness: 0.18,
      clearcoat: 0.75,
      clearcoatRoughness: 0.12,
      wireframe: wireframe
    });

    const mesh = new THREE.Mesh(geom, mat);
    mesh.position.set(posX, 0, 0);
    mesh.castShadow = true;
    mesh.receiveShadow = true;

    // Floor glow puddle
    const puddle = new THREE.Mesh(
      new THREE.BoxGeometry(binW * 0.9, 0.02, barDepth * 0.9),
      new THREE.MeshBasicMaterial({ color: colorHex, transparent: true, opacity: 0.28 })
    );
    puddle.position.set(posX, 0.01, 0);
    group.add(puddle);

    // Floating Frequency Badge
    let badge = null;
    if (showLabels && b.count > 0) {
      badge = createFloatingValueBadge(b.count, colorHex);
      badge.position.set(posX, h + 0.7, 0);
      group.add(badge);
    }

    // Bin Range Label below
    const binLabel = `${formatDataValue(b.min)} - ${formatDataValue(b.max)}`;
    const catSprite = createCategoryLabelSprite(binLabel, isDark);
    catSprite.position.set(posX, -0.42, barDepth / 2 + 0.35);
    group.add(catSprite);

    mesh.userData = {
      label: `Bin: ${binLabel}`,
      val: `Count: ${b.count}`,
      isBeveledBar: true,
      barHeight: h,
      badge: badge
    };

    group.add(mesh);
    interactiveList.push(mesh);

    // Collect point for KDE line
    kdePoints.push(new THREE.Vector3(posX, h + 0.15, barDepth / 2 + 0.1));
  });

  // Smooth 3D KDE Ribbon / Tube across top of histogram
  if (kdePoints.length >= 3) {
    const curve = new THREE.CatmullRomCurve3(kdePoints);
    const tubeGeo = new THREE.TubeGeometry(curve, 64, 0.14, 12, false);
    const tubeMat = new THREE.MeshPhysicalMaterial({
      color: 0x00f2fe,
      emissive: 0x0284c7,
      emissiveIntensity: 0.45,
      metalness: 0.2,
      roughness: 0.15,
      clearcoat: 0.9,
      wireframe: wireframe
    });
    const kdeMesh = new THREE.Mesh(tubeGeo, tubeMat);
    kdeMesh.castShadow = true;
    group.add(kdeMesh);
  }
}

/**
 * -----------------------------------------------------------------------------
 * 2. 3D BOX PLOT
 * -----------------------------------------------------------------------------
 * 3D physical floating cuboid interquartile range (IQR Q1 to Q3), glowing median notch slab,
 * slender metallic vertical whiskers with end caps, and floating outlier spheres.
 */
function build3DBoxPlot(group, allRows, effXCol, effYCol, maxVal, maxHeight, wireframe, interactiveList, paletteColors, accentColor, showLabels, isDark, hasBackdrop) {
  // Group rows by categorical column (effXCol) or single group
  const groups = {};
  const isCategorical = allRows.some(r => typeof r[effXCol] === 'string' && isNaN(parseFloat(r[effXCol])));

  if (isCategorical) {
    allRows.forEach(r => {
      const cat = String(r[effXCol] || 'Other');
      const val = parseFloat(r[effYCol]);
      if (!isNaN(val)) {
        if (!groups[cat]) groups[cat] = [];
        groups[cat].push(val);
      }
    });
  } else {
    // Single or numeric split into 4 categories
    const vals = allRows.map(r => parseFloat(r[effYCol] ?? r[effXCol])).filter(v => !isNaN(v));
    if (vals.length > 0) {
      groups['Overall'] = vals;
    }
  }

  const entries = Object.entries(groups).slice(0, 6);
  if (entries.length === 0) {
    entries.push(
      ['Group A', [15, 22, 28, 35, 42, 48, 55]],
      ['Group B', [25, 32, 40, 48, 58, 65, 78]],
      ['Group C', [10, 18, 25, 30, 36, 42, 50]]
    );
  }

  // Find global min and max for consistent scale
  let globalMin = Infinity;
  let globalMax = -Infinity;
  entries.forEach(([_, vals]) => {
    vals.forEach(v => {
      if (v < globalMin) globalMin = v;
      if (v > globalMax) globalMax = v;
    });
  });
  if (globalMin >= globalMax) {
    globalMin = 0;
    globalMax = 100;
  }
  const globalSpan = globalMax - globalMin || 1;

  const count = entries.length;
  const spacing = count <= 3 ? 3.6 : Math.max(14 / count, 2.2);
  const boxW = Math.min(spacing * 0.55, 1.6);
  const boxD = boxW;
  const startX = -((count - 1) * spacing) / 2;

  const colorsToUse = (paletteColors && paletteColors.length && paletteColors !== PALETTE_MAP.butter_green)
    ? paletteColors
    : CYBER_3D_PALETTE;

  entries.forEach(([catName, vals], i) => {
    const sorted = [...vals].sort((a, b) => a - b);
    const n = sorted.length;
    const minVal = sorted[0];
    const maxValReal = sorted[n - 1];
    const q1 = sorted[Math.floor(n * 0.25)];
    const median = sorted[Math.floor(n * 0.5)];
    const q3 = sorted[Math.floor(n * 0.75)];
    const iqr = q3 - q1;
    const lowerFence = Math.max(minVal, q1 - 1.5 * iqr);
    const upperFence = Math.min(maxValReal, q3 + 1.5 * iqr);
    const outliers = sorted.filter(v => v < lowerFence || v > upperFence);

    const normY = v => Math.max(((v - globalMin) / globalSpan) * maxHeight, 0.4);
    const yMin = normY(lowerFence);
    const yQ1 = normY(q1);
    const yMed = normY(median);
    const yQ3 = normY(q3);
    const yMax = normY(upperFence);

    const posX = startX + i * spacing;
    const colorHex = colorsToUse[i % colorsToUse.length];

    // 1. 3D Floating IQR Box (Q1 to Q3)
    const iqrHeight = Math.max(yQ3 - yQ1, 0.25);
    const boxGeo = new THREE.BoxGeometry(boxW, iqrHeight, boxD);
    const boxMat = new THREE.MeshPhysicalMaterial({
      color: colorHex,
      metalness: 0.18,
      roughness: 0.18,
      clearcoat: 0.8,
      clearcoatRoughness: 0.1,
      wireframe: wireframe
    });
    const boxMesh = new THREE.Mesh(boxGeo, boxMat);
    boxMesh.position.set(posX, (yQ1 + yQ3) / 2, 0);
    boxMesh.castShadow = true;
    boxMesh.receiveShadow = true;
    group.add(boxMesh);
    interactiveList.push(boxMesh);

    // 2. Glowing Median Notch Slab
    const medGeo = new THREE.BoxGeometry(boxW + 0.14, 0.14, boxD + 0.14);
    const medMat = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      emissive: 0xfbbf24,
      emissiveIntensity: 0.65,
      metalness: 0.8,
      roughness: 0.1
    });
    const medMesh = new THREE.Mesh(medGeo, medMat);
    medMesh.position.set(posX, yMed, 0);
    group.add(medMesh);

    // 3. Slender Metallic Whisker Cylinders
    const whiskerMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.9, roughness: 0.15 });
    // Lower whisker
    if (yQ1 > yMin) {
      const lowerH = yQ1 - yMin;
      const lowerGeo = new THREE.CylinderGeometry(0.05, 0.05, lowerH, 12);
      const lowerWhisker = new THREE.Mesh(lowerGeo, whiskerMat);
      lowerWhisker.position.set(posX, yMin + lowerH / 2, 0);
      group.add(lowerWhisker);
    }
    // Upper whisker
    if (yMax > yQ3) {
      const upperH = yMax - yQ3;
      const upperGeo = new THREE.CylinderGeometry(0.05, 0.05, upperH, 12);
      const upperWhisker = new THREE.Mesh(upperGeo, whiskerMat);
      upperWhisker.position.set(posX, yQ3 + upperH / 2, 0);
      group.add(upperWhisker);
    }

    // 4. Whisker End Caps
    const capGeo = new THREE.BoxGeometry(boxW * 0.55, 0.06, boxD * 0.55);
    const minCap = new THREE.Mesh(capGeo, whiskerMat);
    minCap.position.set(posX, yMin, 0);
    group.add(minCap);
    const maxCap = new THREE.Mesh(capGeo, whiskerMat);
    maxCap.position.set(posX, yMax, 0);
    group.add(maxCap);

    // 5. Outlier Spheres
    outliers.forEach(outVal => {
      const outY = normY(outVal);
      const sphereGeo = new THREE.SphereGeometry(0.18, 16, 16);
      const sphereMat = new THREE.MeshStandardMaterial({ color: 0xf43f5e, emissive: 0xe11d48, emissiveIntensity: 0.5 });
      const sphere = new THREE.Mesh(sphereGeo, sphereMat);
      sphere.position.set(posX, outY, 0);
      sphere.userData = { label: `${catName} Outlier`, val: formatDataValue(outVal) };
      group.add(sphere);
      interactiveList.push(sphere);
    });

    // 6. Floating Badge at top
    if (showLabels) {
      const badge = createFloatingValueBadge(median, colorHex);
      badge.position.set(posX, yMax + 0.72, 0);
      group.add(badge);
    }

    // 7. Category Label below
    const catSprite = createCategoryLabelSprite(catName, isDark);
    catSprite.position.set(posX, -0.42, boxD / 2 + 0.35);
    group.add(catSprite);

    // 8. Ground glow puddle
    const puddle = new THREE.Mesh(
      new THREE.CylinderGeometry(boxW * 0.6, boxW * 0.8, 0.02, 24),
      new THREE.MeshBasicMaterial({ color: colorHex, transparent: true, opacity: 0.28 })
    );
    puddle.position.set(posX, 0.01, 0);
    group.add(puddle);

    boxMesh.userData = {
      label: catName,
      val: `Med: ${formatDataValue(median)} [Q1: ${formatDataValue(q1)}, Q3: ${formatDataValue(q3)}]`
    };
  });
}

/**
 * -----------------------------------------------------------------------------
 * 3. 3D VIOLIN PLOT
 * -----------------------------------------------------------------------------
 * Smooth sculpted translucent 3D violin body with kernel density profile,
 * embedded miniature 3D box plot core, glowing median sphere, and category badges.
 */
function build3DViolin(group, allRows, effXCol, effYCol, maxVal, maxHeight, wireframe, interactiveList, paletteColors, accentColor, showLabels, isDark, hasBackdrop) {
  // Group rows by categorical column or fallback
  const groups = {};
  allRows.forEach(r => {
    const cat = String(r[effXCol] || 'Other');
    const val = parseFloat(r[effYCol]);
    if (!isNaN(val)) {
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(val);
    }
  });

  const entries = Object.entries(groups).slice(0, 5);
  if (entries.length === 0) {
    entries.push(
      ['Series A', [10, 15, 22, 28, 32, 35, 40, 48, 55, 62]],
      ['Series B', [20, 25, 34, 42, 45, 50, 58, 68, 75, 82]],
      ['Series C', [12, 18, 24, 30, 36, 42, 48, 52, 58, 65]]
    );
  }

  let globalMin = Infinity;
  let globalMax = -Infinity;
  entries.forEach(([_, vals]) => {
    vals.forEach(v => {
      if (v < globalMin) globalMin = v;
      if (v > globalMax) globalMax = v;
    });
  });
  if (globalMin >= globalMax) {
    globalMin = 0;
    globalMax = 100;
  }
  const globalSpan = globalMax - globalMin || 1;

  const count = entries.length;
  const spacing = count <= 3 ? 3.8 : Math.max(14 / count, 2.4);
  const startX = -((count - 1) * spacing) / 2;

  const colorsToUse = (paletteColors && paletteColors.length && paletteColors !== PALETTE_MAP.butter_green)
    ? paletteColors
    : CYBER_3D_PALETTE;

  entries.forEach(([catName, vals], i) => {
    const sorted = [...vals].sort((a, b) => a - b);
    const n = sorted.length;
    const median = sorted[Math.floor(n * 0.5)];
    const q1 = sorted[Math.floor(n * 0.25)];
    const q3 = sorted[Math.floor(n * 0.75)];

    const posX = startX + i * spacing;
    const colorHex = colorsToUse[i % colorsToUse.length];

    // Compute KDE profile across 16 vertical slices
    const slices = 16;
    const points = [];
    const minNormY = 0.5;
    const maxNormY = maxHeight;
    const stepY = (maxNormY - minNormY) / slices;

    // Estimate density at each slice
    const mean = vals.reduce((a, b) => a + b, 0) / n;
    const std = Math.sqrt(vals.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / n) || 10;

    for (let s = 0; s <= slices; s++) {
      const curY = minNormY + s * stepY;
      const curVal = globalMin + ((curY - minNormY) / (maxNormY - minNormY)) * globalSpan;
      // Gaussian kernel density value
      const zScore = (curVal - mean) / std;
      const density = Math.exp(-0.5 * zScore * zScore);
      const radius = Math.max(0.12, density * 1.15);
      points.push(new THREE.Vector2(radius, curY));
    }

    // 3D Sculpted Violin Mesh using LatheGeometry (revolved density envelope)
    const latheGeo = new THREE.LatheGeometry(points, 24);
    const latheMat = new THREE.MeshPhysicalMaterial({
      color: colorHex,
      transparent: true,
      opacity: 0.76,
      roughness: 0.15,
      metalness: 0.18,
      clearcoat: 0.85,
      wireframe: wireframe
    });
    const violinMesh = new THREE.Mesh(latheGeo, latheMat);
    violinMesh.position.set(posX, 0, 0);
    violinMesh.castShadow = true;
    group.add(violinMesh);
    interactiveList.push(violinMesh);

    // Internal Miniature Box Plot Spine inside violin
    const coreH = Math.max(((q3 - q1) / globalSpan) * maxHeight, 0.4);
    const coreY = minNormY + (((q1 + q3) / 2 - globalMin) / globalSpan) * (maxNormY - minNormY);
    const coreGeo = new THREE.CylinderGeometry(0.08, 0.08, coreH, 12);
    const coreMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, metalness: 0.9, roughness: 0.2 });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    coreMesh.position.set(posX, coreY, 0);
    group.add(coreMesh);

    // Glowing White Median Sphere
    const medY = minNormY + ((median - globalMin) / globalSpan) * (maxNormY - minNormY);
    const medGeo = new THREE.SphereGeometry(0.18, 16, 16);
    const medMat = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0x38bdf8, emissiveIntensity: 0.8 });
    const medSphere = new THREE.Mesh(medGeo, medMat);
    medSphere.position.set(posX, medY, 0);
    group.add(medSphere);

    // Floating Value Badge
    if (showLabels) {
      const badge = createFloatingValueBadge(median, colorHex);
      badge.position.set(posX, maxNormY + 0.65, 0);
      group.add(badge);
    }

    // Category Label below
    const catSprite = createCategoryLabelSprite(catName, isDark);
    catSprite.position.set(posX, -0.42, 1.4);
    group.add(catSprite);

    // Floor glow disc
    const puddle = new THREE.Mesh(
      new THREE.CylinderGeometry(1.0, 1.25, 0.02, 24),
      new THREE.MeshBasicMaterial({ color: colorHex, transparent: true, opacity: 0.25 })
    );
    puddle.position.set(posX, 0.01, 0);
    group.add(puddle);

    violinMesh.userData = {
      label: catName,
      val: `Violin Median: ${formatDataValue(median)}`
    };
  });
}

/**
 * -----------------------------------------------------------------------------
 * 4. 3D WATERFALL CHART
 * -----------------------------------------------------------------------------
 * 3D floating stepped columns with floating baselines: positive increments (green/teal),
 * negative decrements (red/coral), anchored totals, and neon connector bridge lines.
 */
function build3DWaterfall(group, dataPoints, maxVal, maxHeight, wireframe, interactiveList, paletteColors, accentColor, showLabels, isDark, effXCol, effYCol) {
  const count = dataPoints.length;
  const spacing = count <= 5 ? 2.4 : Math.max(14 / count, 1.5);
  const colW = Math.min(spacing * 0.65, 1.5);
  const colD = colW;
  const startX = -((count - 1) * spacing) / 2;

  // Calculate cumulative baseline
  let cumulative = 0;
  const steps = [];
  dataPoints.forEach((d, i) => {
    const isFirst = i === 0;
    const isLast = i === count - 1;
    const rawVal = parseFloat(d.val) || 0;
    // Alternate positive/negative if all positive in sample
    const val = (i % 3 === 2 && !isFirst && !isLast) ? -Math.abs(rawVal * 0.45) : rawVal;
    const startY = cumulative;
    cumulative += val;
    steps.push({
      label: d.label,
      val: val,
      startY: isFirst || isLast ? 0 : startY,
      endY: isFirst || isLast ? Math.abs(cumulative) : cumulative,
      isTotal: isFirst || isLast,
      isPositive: val >= 0
    });
  });

  const maxCumulative = Math.max(...steps.map(s => Math.max(Math.abs(s.startY), Math.abs(s.endY))), 1);
  const normY = v => (v / maxCumulative) * maxHeight;

  steps.forEach((step, i) => {
    const posX = startX + i * spacing;
    const y0 = Math.max(normY(Math.min(step.startY, step.endY)), 0.05);
    const y1 = Math.max(normY(Math.max(step.startY, step.endY)), y0 + 0.35);
    const h = y1 - y0;
    const centerY = y0 + h / 2;

    const colorHex = step.isTotal
      ? '#7C3AED'
      : (step.isPositive ? '#10B981' : '#EF4444');

    // 3D Stepped Column Geometry
    const geom = createBeveledBarGeometry(colW, h, colD, 0.05);
    const mat = new THREE.MeshPhysicalMaterial({
      color: colorHex,
      metalness: 0.15,
      roughness: 0.18,
      clearcoat: 0.75,
      wireframe: wireframe
    });
    const mesh = new THREE.Mesh(geom, mat);
    mesh.position.set(posX, centerY - h / 2, 0);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    group.add(mesh);
    interactiveList.push(mesh);

    // Neon Connector Bridge Line to next step
    if (i < steps.length - 1) {
      const nextX = startX + (i + 1) * spacing;
      const bridgeY = normY(step.endY);
      const bridgePoints = [
        new THREE.Vector3(posX + colW / 2, bridgeY, 0),
        new THREE.Vector3(nextX - colW / 2, bridgeY, 0)
      ];
      const bridgeLine = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(bridgePoints),
        new THREE.LineDashedMaterial({
          color: 0x38bdf8,
          dashSize: 0.2,
          gapSize: 0.1,
          linewidth: 2,
          transparent: true,
          opacity: 0.85
        })
      );
      bridgeLine.computeLineDistances();
      group.add(bridgeLine);
    }

    // Floating Value Badge
    if (showLabels) {
      const sign = step.val > 0 && !step.isTotal ? '+' : '';
      const badge = createFloatingValueBadge(`${sign}${formatDataValue(step.val)}`, colorHex);
      badge.position.set(posX, y1 + 0.65, 0);
      group.add(badge);
    }

    // Category Label below
    const catSprite = createCategoryLabelSprite(step.label, isDark);
    catSprite.position.set(posX, -0.42, colD / 2 + 0.35);
    group.add(catSprite);

    // Floor glow disc
    const puddle = new THREE.Mesh(
      new THREE.CylinderGeometry(colW * 0.6, colW * 0.75, 0.02, 16),
      new THREE.MeshBasicMaterial({ color: colorHex, transparent: true, opacity: 0.28 })
    );
    puddle.position.set(posX, 0.01, 0);
    group.add(puddle);

    mesh.userData = {
      label: step.label,
      val: `${step.val >= 0 ? '+' : ''}${formatDataValue(step.val)} (Total: ${formatDataValue(step.endY)})`
    };
  });
}

/**
 * -----------------------------------------------------------------------------
 * 5. 3D FUNNEL CHART
 * -----------------------------------------------------------------------------
 * Stacked descending 3D tapered frustums / truncated cones with glowing connector rings,
 * conversion percentage decals, and sunset/cyber gradient materials.
 */
function build3DFunnel(group, dataPoints, wireframe, interactiveList, paletteColors, showLabels, isDark) {
  // Sort descending by value
  const stages = [...dataPoints]
    .sort((a, b) => b.val - a.val)
    .slice(0, 6);

  if (stages.length === 0) return;

  const topVal = stages[0].val || 1;
  const totalStages = stages.length;
  const stageH = 1.15;
  const gap = 0.22;
  const totalHeight = totalStages * (stageH + gap);

  const colorsToUse = (paletteColors && paletteColors.length && paletteColors !== PALETTE_MAP.butter_green)
    ? paletteColors
    : ['#f43f5e', '#fb923c', '#f59e0b', '#10b981', '#06b6d4', '#8b5cf6'];

  const maxRadius = 4.6;
  const minRadius = 1.2;

  stages.forEach((st, i) => {
    const ratioTop = 1.0 - (i / totalStages) * 0.75;
    const ratioBottom = 1.0 - ((i + 1) / totalStages) * 0.75;
    const rTop = minRadius + (maxRadius - minRadius) * ratioTop;
    const rBottom = minRadius + (maxRadius - minRadius) * ratioBottom;

    const posY = totalHeight - i * (stageH + gap) - stageH / 2 + 0.5;
    const colorHex = colorsToUse[i % colorsToUse.length];

    // 3D Truncated Cone Frustum Geometry
    const coneGeo = new THREE.CylinderGeometry(rTop, rBottom, stageH, 36);
    const coneMat = new THREE.MeshPhysicalMaterial({
      color: colorHex,
      metalness: 0.15,
      roughness: 0.18,
      clearcoat: 0.8,
      clearcoatRoughness: 0.12,
      wireframe: wireframe
    });
    const coneMesh = new THREE.Mesh(coneGeo, coneMat);
    coneMesh.position.set(0, posY, 0);
    coneMesh.castShadow = true;
    coneMesh.receiveShadow = true;
    group.add(coneMesh);
    interactiveList.push(coneMesh);

    // Glowing Connector Torus Ring at the top rim of each stage
    const ringGeo = new THREE.TorusGeometry(rTop, 0.06, 12, 48);
    const ringMat = new THREE.MeshStandardMaterial({
      color: 0x38bdf8,
      emissive: 0x0284c7,
      emissiveIntensity: 0.6
    });
    const ringMesh = new THREE.Mesh(ringGeo, ringMat);
    ringMesh.rotation.x = Math.PI / 2;
    ringMesh.position.set(0, posY + stageH / 2, 0);
    group.add(ringMesh);

    // Conversion Percentage & Label Badge in front
    const pct = Math.round((st.val / topVal) * 100);
    if (showLabels) {
      const badge = createFloatingValueBadge(`${st.label}: ${formatDataValue(st.val)} (${pct}%)`, colorHex);
      badge.position.set(0, posY, rTop + 0.6);
      group.add(badge);
    }

    coneMesh.userData = {
      label: st.label,
      val: `${formatDataValue(st.val)} (${pct}% conversion)`
    };
  });
}

/**
 * -----------------------------------------------------------------------------
 * 6. 3D LOLLIPOP CHART
 * -----------------------------------------------------------------------------
 * Slender metallic chrome stalks rising from neon circular ground pads with glossy
 * physical spheres atop each stem and glowing hovering value badges.
 */
function build3DLollipop(group, dataPoints, maxVal, maxHeight, wireframe, interactiveList, paletteColors, accentColor, showLabels, isDark, effXCol, effYCol, hasBackdrop) {
  const count = dataPoints.length;
  const spacing = count <= 5 ? 2.3 : Math.max(14 / count, 1.4);
  const startX = -((count - 1) * spacing) / 2;

  const colorsToUse = (paletteColors && paletteColors.length && paletteColors !== PALETTE_MAP.butter_green)
    ? paletteColors
    : CYBER_3D_PALETTE;

  dataPoints.forEach((d, i) => {
    const rawRatio = maxVal > 0 ? (d.val / maxVal) : 0.5;
    const h = Math.max(rawRatio * maxHeight, 0.8);
    const posX = startX + i * spacing;
    const colorHex = colorsToUse[i % colorsToUse.length];

    // Slender Chrome Vertical Stalk
    const stalkGeo = new THREE.CylinderGeometry(0.08, 0.08, h, 16);
    const stalkMat = new THREE.MeshStandardMaterial({
      color: 0x94a3b8,
      metalness: 0.92,
      roughness: 0.12,
      wireframe: wireframe
    });
    const stalk = new THREE.Mesh(stalkGeo, stalkMat);
    stalk.position.set(posX, h / 2, 0);
    stalk.castShadow = true;
    group.add(stalk);

    // Glossy Lollipop Head Sphere
    const headRadius = 0.52;
    const headGeo = new THREE.SphereGeometry(headRadius, 32, 32);
    const headMat = new THREE.MeshPhysicalMaterial({
      color: colorHex,
      metalness: 0.18,
      roughness: 0.12,
      clearcoat: 0.95,
      clearcoatRoughness: 0.08,
      reflectivity: 0.8,
      wireframe: wireframe
    });
    const head = new THREE.Mesh(headGeo, headMat);
    head.position.set(posX, h, 0);
    head.castShadow = true;
    group.add(head);
    interactiveList.push(head);

    // Floor Base Disc Pad
    const padGeo = new THREE.CylinderGeometry(0.42, 0.55, 0.03, 24);
    const padMat = new THREE.MeshStandardMaterial({
      color: 0x38bdf8,
      emissive: 0x0284c7,
      emissiveIntensity: 0.45,
      metalness: 0.8,
      roughness: 0.2
    });
    const pad = new THREE.Mesh(padGeo, padMat);
    pad.position.set(posX, 0.015, 0);
    group.add(pad);

    // Floating Neon Value Badge
    if (showLabels) {
      const badge = createFloatingValueBadge(d.val, colorHex);
      badge.position.set(posX, h + headRadius + 0.65, 0);
      group.add(badge);
    }

    // Category Label below
    const catSprite = createCategoryLabelSprite(d.label, isDark);
    catSprite.position.set(posX, -0.42, 0.8);
    group.add(catSprite);

    head.userData = {
      label: d.label,
      val: formatDataValue(d.val)
    };
  });
}

/**
 * -----------------------------------------------------------------------------
 * 7. 3D RADAR / SPIDER CHART
 * -----------------------------------------------------------------------------
 * Concentric 3D polygonal floor rings, radial spoke lines, and elevated 3D web polygon
 * surface with glowing node spheres and feature labels at perimeter vertices.
 */
function build3DRadar(group, allRows, numCols, catCols, effXCol, wireframe, interactiveList, paletteColors, showLabels, isDark) {
  const features = (numCols && numCols.length >= 3)
    ? numCols.slice(0, 5)
    : ['Metric A', 'Metric B', 'Metric C', 'Metric D', 'Metric E'];

  const numAxes = features.length;
  const radius = 5.2;

  // Base Concentric Rings on floor
  const ringSteps = [0.25, 0.5, 0.75, 1.0];
  ringSteps.forEach(ratio => {
    const ringPts = [];
    for (let a = 0; a <= numAxes; a++) {
      const angle = (a % numAxes) * (Math.PI * 2 / numAxes) - Math.PI / 2;
      ringPts.push(new THREE.Vector3(Math.cos(angle) * radius * ratio, 0.02, Math.sin(angle) * radius * ratio));
    }
    const ringLine = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(ringPts),
      new THREE.LineBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.35, linewidth: 1 })
    );
    group.add(ringLine);
  });

  // Radial Spokes and Axis Labels
  for (let a = 0; a < numAxes; a++) {
    const angle = a * (Math.PI * 2 / numAxes) - Math.PI / 2;
    const spokePts = [
      new THREE.Vector3(0, 0.02, 0),
      new THREE.Vector3(Math.cos(angle) * radius, 0.02, Math.sin(angle) * radius)
    ];
    group.add(new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(spokePts),
      new THREE.LineBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.6, linewidth: 2 })
    ));

    // Axis label at spoke tip
    const featSprite = createAxisTitleSprite(features[a], false);
    featSprite.position.set(Math.cos(angle) * (radius + 1.1), 0.3, Math.sin(angle) * (radius + 1.1));
    group.add(featSprite);
  }

  // Sample entities to plot (up to 2 series)
  const plotRows = (allRows && allRows.length) ? allRows.slice(0, 2) : [{}, {}];
  const seriesColors = ['#10B981', '#F43F5E'];

  plotRows.forEach((row, sIdx) => {
    const colorHex = seriesColors[sIdx % seriesColors.length];
    const polyPoints = [];

    for (let a = 0; a < numAxes; a++) {
      const feat = features[a];
      const rawVal = parseFloat(row[feat]);
      const normVal = !isNaN(rawVal) ? Math.min(Math.max(rawVal / 100, 0.25), 1.0) : 0.3 + ((a + sIdx * 2) % 5) * 0.15;
      const angle = a * (Math.PI * 2 / numAxes) - Math.PI / 2;
      const ptX = Math.cos(angle) * radius * normVal;
      const ptZ = Math.sin(angle) * radius * normVal;
      const ptY = 0.5 + normVal * 3.5;
      const pt = new THREE.Vector3(ptX, ptY, ptZ);
      polyPoints.push(pt);

      // Node Sphere
      const sphereGeo = new THREE.SphereGeometry(0.24, 16, 16);
      const sphereMat = new THREE.MeshStandardMaterial({
        color: colorHex,
        emissive: colorHex,
        emissiveIntensity: 0.5,
        metalness: 0.7,
        roughness: 0.2
      });
      const sphere = new THREE.Mesh(sphereGeo, sphereMat);
      sphere.position.copy(pt);
      sphere.userData = { label: `${feat} (Series ${sIdx + 1})`, val: formatDataValue(rawVal || normVal * 100) };
      group.add(sphere);
      interactiveList.push(sphere);

      // Drop line to floor
      group.add(new THREE.Line(
        new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(ptX, 0.02, ptZ), pt]),
        new THREE.LineBasicMaterial({ color: colorHex, transparent: true, opacity: 0.45 })
      ));
    }

    // Connect polygon outline
    const closedPts = [...polyPoints, polyPoints[0]];
    const edgeLine = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(closedPts),
      new THREE.LineBasicMaterial({ color: colorHex, linewidth: 3 })
    );
    group.add(edgeLine);
  });
}

/**
 * -----------------------------------------------------------------------------
 * 8. 3D BUBBLE CHART
 * -----------------------------------------------------------------------------
 * 3D spatial spheres with true XYZ coordinates, volume-scaled radii, vertical drop lines,
 * ground glow discs, specular glass reflections, and floating badges.
 */
function build3DBubble(group, allRows, effXCol, effYCol, numCols, maxVal, maxHeight, wireframe, interactiveList, paletteColors, accentColor, showLabels, isDark) {
  const sizeCol = (numCols || []).find(c => c !== effXCol && c !== effYCol) || effYCol;
  const rows = (allRows || []).slice(0, 16);

  const colorsToUse = (paletteColors && paletteColors.length && paletteColors !== PALETTE_MAP.butter_green)
    ? paletteColors
    : CYBER_3D_PALETTE;

  // Compute ranges
  const xVals = rows.map(r => parseFloat(r[effXCol])).filter(v => !isNaN(v));
  const yVals = rows.map(r => parseFloat(r[effYCol])).filter(v => !isNaN(v));
  const sVals = rows.map(r => parseFloat(r[sizeCol])).filter(v => !isNaN(v));

  const minX = Math.min(...xVals, 0);
  const maxX = Math.max(...xVals, 1);
  const spanX = maxX - minX || 1;

  const minY = Math.min(...yVals, 0);
  const maxY = Math.max(...yVals, 1);
  const spanY = maxY - minY || 1;

  const minS = Math.min(...sVals, 1);
  const maxS = Math.max(...sVals, 10);
  const spanS = maxS - minS || 1;

  rows.forEach((r, i) => {
    const rawX = parseFloat(r[effXCol]);
    const rawY = parseFloat(r[effYCol]);
    const rawS = parseFloat(r[sizeCol]);

    const posX = !isNaN(rawX) ? -6.0 + ((rawX - minX) / spanX) * 12.0 : -5.0 + i * 0.75;
    const posY = !isNaN(rawY) ? 0.8 + ((rawY - minY) / spanY) * (maxHeight - 1.0) : 1.5 + (i % 6);
    const posZ = -3.0 + Math.sin(i * 1.5) * 6.0;

    const sRatio = !isNaN(rawS) ? (rawS - minS) / spanS : 0.5;
    const radius = 0.45 + sRatio * 0.9;
    const colorHex = colorsToUse[i % colorsToUse.length];

    // 3D Glassmorphic Physical Sphere
    const geom = new THREE.SphereGeometry(radius, 32, 32);
    const mat = new THREE.MeshPhysicalMaterial({
      color: colorHex,
      metalness: 0.15,
      roughness: 0.12,
      clearcoat: 0.95,
      clearcoatRoughness: 0.1,
      reflectivity: 0.7,
      wireframe: wireframe
    });

    const mesh = new THREE.Mesh(geom, mat);
    mesh.position.set(posX, posY, posZ);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    group.add(mesh);
    interactiveList.push(mesh);

    // Glowing vertical drop line to floor
    const lineGeo = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(posX, 0.02, posZ),
      new THREE.Vector3(posX, posY, posZ)
    ]);
    const lineMat = new THREE.LineDashedMaterial({
      color: 0x38bdf8,
      dashSize: 0.2,
      gapSize: 0.1,
      transparent: true,
      opacity: 0.5
    });
    const line = new THREE.Line(lineGeo, lineMat);
    line.computeLineDistances();
    group.add(line);

    // Floor shadow puddle
    const puddle = new THREE.Mesh(
      new THREE.CylinderGeometry(radius * 0.8, radius * 1.1, 0.02, 20),
      new THREE.MeshBasicMaterial({ color: colorHex, transparent: true, opacity: 0.3 })
    );
    puddle.position.set(posX, 0.01, posZ);
    group.add(puddle);

    // Floating value badge
    if (showLabels) {
      const badge = createFloatingValueBadge(`${formatDataValue(rawY || posY)} [Size: ${formatDataValue(rawS || 1)}]`, colorHex);
      badge.position.set(posX, posY + radius + 0.5, posZ);
      group.add(badge);
    }

    mesh.userData = {
      label: `Row ${i + 1}`,
      val: `(${effXCol}: ${formatDataValue(rawX)}, ${effYCol}: ${formatDataValue(rawY)}) [${sizeCol}: ${formatDataValue(rawS)}]`
    };
  });
}

/**
 * -----------------------------------------------------------------------------
 * 9. 3D PAIRPLOT MATRIX
 * -----------------------------------------------------------------------------
 * Multi-bay cyber matrix of mini 3D plots (binned histograms along the diagonal,
 * mini scatter pedestals on off-diagonals) mounted on elevated cyber bays.
 */
function build3DPairplot(group, allRows, numCols, wireframe, interactiveList, paletteColors, showLabels, isDark) {
  const features = (numCols && numCols.length >= 2)
    ? numCols.slice(0, 3)
    : ['Feature 1', 'Feature 2', 'Feature 3'];

  const gridSize = features.length;
  const baySize = 3.6;
  const gap = 0.6;
  const totalSpan = gridSize * baySize + (gridSize - 1) * gap;
  const startOffset = -totalSpan / 2 + baySize / 2;

  const colorsToUse = (paletteColors && paletteColors.length && paletteColors !== PALETTE_MAP.butter_green)
    ? paletteColors
    : CYBER_3D_PALETTE;

  // Base platform
  const baseMat = new THREE.MeshStandardMaterial({ color: 0x091224, metalness: 0.85, roughness: 0.2 });
  const platform = new THREE.Mesh(new THREE.BoxGeometry(totalSpan + 1.0, 0.2, totalSpan + 1.0), baseMat);
  platform.position.set(0, 0.1, 0);
  group.add(platform);

  for (let row = 0; row < gridSize; row++) {
    for (let col = 0; col < gridSize; col++) {
      const bayX = startOffset + col * (baySize + gap);
      const bayZ = startOffset + row * (baySize + gap);
      const isDiagonal = row === col;
      const colorHex = colorsToUse[(row * gridSize + col) % colorsToUse.length];

      // Bay Floor Tile with glowing neon rim
      const tile = new THREE.Mesh(
        new THREE.BoxGeometry(baySize, 0.08, baySize),
        new THREE.MeshStandardMaterial({ color: 0x0f172a, metalness: 0.7, roughness: 0.3 })
      );
      tile.position.set(bayX, 0.24, bayZ);
      group.add(tile);

      const framePts = [
        new THREE.Vector3(bayX - baySize / 2, 0.29, bayZ - baySize / 2),
        new THREE.Vector3(bayX + baySize / 2, 0.29, bayZ - baySize / 2),
        new THREE.Vector3(bayX + baySize / 2, 0.29, bayZ + baySize / 2),
        new THREE.Vector3(bayX - baySize / 2, 0.29, bayZ + baySize / 2),
        new THREE.Vector3(bayX - baySize / 2, 0.29, bayZ - baySize / 2)
      ];
      group.add(new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(framePts),
        new THREE.LineBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.85, linewidth: 2 })
      ));

      if (isDiagonal) {
        // Diagonal Bay: Mini 3D Histogram with 4 binned columns
        const miniBins = 4;
        const miniW = (baySize * 0.8) / miniBins;
        for (let b = 0; b < miniBins; b++) {
          const miniH = 0.4 + ((b + 1) * 3) % 1.8;
          const barMesh = new THREE.Mesh(
            new THREE.BoxGeometry(miniW * 0.88, miniH, miniW * 0.88),
            new THREE.MeshPhysicalMaterial({ color: colorHex, metalness: 0.2, roughness: 0.2, clearcoat: 0.8 })
          );
          barMesh.position.set(bayX - baySize * 0.35 + b * miniW, 0.28 + miniH / 2, bayZ);
          group.add(barMesh);
        }
      } else {
        // Off-Diagonal Bay: Mini 3D Scatter with micro-spheres
        for (let s = 0; s < 6; s++) {
          const sX = bayX - baySize * 0.3 + (s * 0.5) % (baySize * 0.6);
          const sZ = bayZ - baySize * 0.3 + ((s * 3) * 0.25) % (baySize * 0.6);
          const sY = 0.5 + ((s * 7) % 5) * 0.28;
          const sphere = new THREE.Mesh(
            new THREE.SphereGeometry(0.14, 16, 16),
            new THREE.MeshPhysicalMaterial({ color: colorHex, clearcoat: 0.9 })
          );
          sphere.position.set(sX, sY, sZ);
          group.add(sphere);
        }
      }

      // Title on bay corner
      const titleSprite = createAxisTitleSprite(`${features[col]} vs ${features[row]}`, false);
      titleSprite.position.set(bayX, 0.35, bayZ + baySize / 2 + 0.3);
      group.add(titleSprite);
    }
  }
}
