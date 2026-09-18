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

export function resolveBackgroundTheme(styleKey = 'whitegrid', paletteKey = 'butter_green') {
  const s = String(styleKey || '').toLowerCase().replace(/-/g, '_').trim();
  const p = String(paletteKey || '').toLowerCase().replace(/-/g, '_').trim();

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

  // Determine if active chart is a distribution plot (histogram, kde, box, etc.)
  const chartType = (activeChart?.chart_type || '').toLowerCase();
  const isDistributionChart = ['histogram', 'hist', 'distribution', 'kde', 'box', 'violin'].some(t =>
    chartType.includes(t)
  );
  const [displayMode, setDisplayMode] = useState(isDistributionChart ? 'card' : 'mesh');

  // Automatically default to 3D Card for histogram/distribution charts
  useEffect(() => {
    const isDist = ['histogram', 'hist', 'distribution', 'kde', 'box', 'violin'].some(t =>
      (activeChart?.chart_type || '').toLowerCase().includes(t)
    );
    setDisplayMode(isDist ? 'card' : 'mesh');
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
    () => resolveBackgroundTheme(activeStyleKey, activePaletteKey),
    [activeStyleKey, activePaletteKey]
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

    // 2. Camera (Centered straight in front of screen)
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    if (displayMode === 'card') {
      camera.position.set(0, 5.7, 18.5);
    } else {
      camera.position.set(0, 8.5, 21.0);
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
      controls.target.set(0, 3.2, 0);
    }
    controls.update();
    controlsRef.current = controls;

    // 5. Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, bgTheme.ambientIntensity || 0.85);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, bgTheme.lightIntensity || 1.2);
    dirLight.position.set(15, 25, 15);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 1024;
    dirLight.shadow.mapSize.height = 1024;
    scene.add(dirLight);

    const rimLightColor = bgTheme.isDark ? 0x60a5fa : 0xffefb3;
    const rimLight = new THREE.DirectionalLight(rimLightColor, bgTheme.isDark ? 0.8 : 0.6);
    rimLight.position.set(-15, 10, -15);
    scene.add(rimLight);

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
        cameraRef.current.position.set(0, 8.5, 21.0);
        controlsRef.current.target.set(0, 3.2, 0);
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

  // If user selected 3D Card OR it's a distribution chart (histogram, KDE, etc.) and not explicitly set to mesh
  if (displayMode === 'card' || (isDist && displayMode !== 'mesh')) {
    build3DCard(chartGroup, activeChart, wireframe, interactiveList, accentColor, isDark, bgTheme);
    return;
  }

  const allRows = dataset?.sample_data?.length ? dataset.sample_data : (dataset?.head_rows || []);
  const args = activeChart?.args || {};

  const numCols = dataset?.numeric_columns || [];
  const allCols = dataset?.columns || [];
  const catCols = allCols.filter((c) => !numCols.includes(c));

  let yCol = args.y_col;
  let xCol = args.x_col || catCols[0] || allCols[0];

  // Auto-swap if xCol is numeric and yCol is categorical
  if (xCol && yCol && numCols.includes(xCol) && !numCols.includes(yCol)) {
    const temp = xCol;
    xCol = yCol;
    yCol = temp;
  }

  let dataPoints = [];

  let effYCol = yCol || numCols[0] || allCols[0];
  let effXCol = xCol || catCols[0] || allCols[1] || allCols[0];

  // Auto-swap if x_col is numeric and y_col is categorical
  if (numCols.includes(effXCol) && !numCols.includes(effYCol)) {
    const temp = effXCol;
    effXCol = effYCol;
    effYCol = temp;
  }

  const isCategoricalChart = ['bar', 'pie', 'donut', 'lollipop', 'waterfall', 'funnel'].some(t => chartType.includes(t));

  if (isCategoricalChart) {
    // Aggregate by category (effXCol) matching 2D bar chart behavior exactly
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
    const rows = allRows.slice(0, 16);
    dataPoints = rows.map((r, i) => {
      const rawVal = parseFloat(r[effYCol]);
      return {
        label: String(r[effXCol] ?? `Item ${i + 1}`),
        val: !isNaN(rawVal) ? rawVal : (i + 1) * 8 + Math.floor(Math.random() * 10),
        rawRow: r
      };
    });
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

  // Switch by Chart Type
  if (['scatter', 'bubble'].includes(chartType)) {
    build3DScatter(chartGroup, dataPoints, maxVal, maxHeight, wireframe, interactiveList, paletteColors, accentColor, showLabels, isDark);
  } else if (['pie', 'donut'].includes(chartType)) {
    build3DPieDonut(chartGroup, dataPoints, chartType === 'donut', wireframe, interactiveList, paletteColors, showLabels, isDark);
  } else if (['line', 'area'].includes(chartType)) {
    build3DLineArea(chartGroup, dataPoints, maxVal, maxHeight, chartType === 'area', wireframe, interactiveList, paletteColors, accentColor, showLabels, isDark);
  } else if (['heatmap'].includes(chartType)) {
    build3DHeatmap(chartGroup, dataPoints, wireframe, interactiveList, paletteColors, showLabels, isDark);
  } else {
    // Bar, lollipop, waterfall fallback to 3D Columns
    build3DBar(chartGroup, dataPoints, maxVal, maxHeight, wireframe, interactiveList, paletteColors, accentColor, showLabels, isDark);
  }
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
  const frontMat = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    roughness: 0.2,
    metalness: 0.05,
    wireframe: wireframe,
    side: THREE.FrontSide
  });
  const frontMesh = new THREE.Mesh(frontGeo, frontMat);
  frontMesh.position.z = depth / 2 + 0.015;
  frontMesh.receiveShadow = true;
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

/** 3D Bar & Column Chart */
function build3DBar(group, data, maxVal, maxHeight, wireframe, interactiveList, paletteColors = DEFAULT_PALETTE, accentColor = 0x013e37, showLabels = true, isDark = false) {
  const count = data.length;
  const spacing = 1.6;
  const startX = -((count - 1) * spacing) / 2;
  const accentHex = typeof accentColor === 'number' ? `#${accentColor.toString(16).padStart(6, '0')}` : accentColor;

  data.forEach((d, i) => {
    const height = Math.max((d.val / maxVal) * maxHeight, 0.4);
    const colorHex = paletteColors[i % paletteColors.length];

    const geom = new THREE.BoxGeometry(1.0, 1, 1.0);
    const mat = new THREE.MeshStandardMaterial({
      color: colorHex,
      metalness: 0.25,
      roughness: 0.35,
      wireframe: wireframe
    });

    const mesh = new THREE.Mesh(geom, mat);
    mesh.position.set(startX + i * spacing, height / 2, 0);
    mesh.scale.set(1, height, 1);
    mesh.castShadow = true;
    mesh.receiveShadow = true;

    // Glued Flat Surface Label (2D decal on top of the 3D bar)
    let labelMesh = null;
    if (showLabels) {
      labelMesh = createSurfaceLabelMesh(d.val, d.label, 0.92, 0.92, isDark, accentHex);
      labelMesh.position.set(startX + i * spacing, height + 0.015, 0);
      group.add(labelMesh);
    }

    mesh.userData = {
      label: d.label,
      val: d.val,
      origScaleY: height,
      baseHeight: 1,
      labelMesh: labelMesh
    };

    group.add(mesh);
    interactiveList.push(mesh);

    // Base marker
    const baseGeo = new THREE.CylinderGeometry(0.65, 0.65, 0.08, 16);
    const baseMat = new THREE.MeshBasicMaterial({ color: accentColor, opacity: 0.3, transparent: true });
    const base = new THREE.Mesh(baseGeo, baseMat);
    base.position.set(startX + i * spacing, 0.04, 0);
    group.add(base);
  });
}

/** 3D Scatter & Bubble Chart */
function build3DScatter(group, data, maxVal, maxHeight, wireframe, interactiveList, paletteColors = DEFAULT_PALETTE, accentColor = 0x013e37, showLabels = true, isDark = false) {
  const accentHex = typeof accentColor === 'number' ? `#${accentColor.toString(16).padStart(6, '0')}` : accentColor;

  data.forEach((d, i) => {
    const normY = (d.val / maxVal) * maxHeight;
    const posX = (Math.sin(i * 1.3) * 6);
    const posZ = (Math.cos(i * 1.3) * 6);
    const posY = Math.max(normY, 1.0);

    const radius = 0.5 + (d.val / maxVal) * 0.4;
    const geom = new THREE.SphereGeometry(radius, 32, 32);
    const colorHex = paletteColors[i % paletteColors.length];

    const mat = new THREE.MeshStandardMaterial({
      color: colorHex,
      metalness: 0.5,
      roughness: 0.2,
      wireframe: wireframe
    });

    const mesh = new THREE.Mesh(geom, mat);
    mesh.position.set(posX, posY, posZ);
    mesh.castShadow = true;
    mesh.receiveShadow = true;

    mesh.userData = { label: d.label, val: d.val };
    group.add(mesh);
    interactiveList.push(mesh);

    // Tight micro-badge attached directly to sphere top (depth tested)
    if (showLabels) {
      const labelSprite = createTightBadgeSprite(d.val, isDark, accentHex);
      labelSprite.position.set(posX, posY + radius + 0.1, posZ);
      group.add(labelSprite);
    }

    // Drop line to floor
    const lineGeo = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(posX, 0, posZ),
      new THREE.Vector3(posX, posY, posZ)
    ]);
    const lineMat = new THREE.LineDashedMaterial({
      color: accentColor,
      dashSize: 0.2,
      gapSize: 0.1,
      opacity: 0.4,
      transparent: true
    });
    const line = new THREE.Line(lineGeo, lineMat);
    line.computeLineDistances();
    group.add(line);
  });
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
  const spacing = 1.6;
  const startX = -((count - 1) * spacing) / 2;
  const points = [];
  const accentHex = typeof accentColor === 'number' ? `#${accentColor.toString(16).padStart(6, '0')}` : accentColor;

  data.forEach((d, i) => {
    const height = Math.max((d.val / maxVal) * maxHeight, 0.5);
    const pt = new THREE.Vector3(startX + i * spacing, height, 0);
    points.push(pt);

    // Marker sphere
    const sphereGeo = new THREE.SphereGeometry(0.35, 16, 16);
    const sphereMat = new THREE.MeshStandardMaterial({
      color: paletteColors[i % paletteColors.length],
      metalness: 0.4,
      roughness: 0.2,
      wireframe: wireframe
    });
    const sphere = new THREE.Mesh(sphereGeo, sphereMat);
    sphere.position.copy(pt);
    sphere.castShadow = true;
    sphere.userData = { label: d.label, val: d.val };
    group.add(sphere);
    interactiveList.push(sphere);

    // Tight micro-badge attached directly to marker sphere (depth tested)
    if (showLabels) {
      const labelSprite = createTightBadgeSprite(d.val, isDark, accentHex);
      labelSprite.position.set(pt.x, height + 0.38, pt.z);
      group.add(labelSprite);
    }

    // Vertical column support
    const postGeo = new THREE.CylinderGeometry(0.08, 0.08, height, 8);
    const postMat = new THREE.MeshBasicMaterial({ color: accentColor, opacity: 0.3, transparent: true });
    const post = new THREE.Mesh(postGeo, postMat);
    post.position.set(pt.x, height / 2, 0);
    group.add(post);
  });

  // Curve tube
  if (points.length >= 2) {
    const curve = new THREE.CatmullRomCurve3(points);
    const tubeGeo = new THREE.TubeGeometry(curve, 64, 0.2, 12, false);
    const tubeMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(paletteColors[0] || 0x08ab9c),
      metalness: 0.5,
      roughness: 0.25,
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
