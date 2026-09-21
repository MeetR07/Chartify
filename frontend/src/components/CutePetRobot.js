import * as THREE from 'three';

/**
 * Cute Pet Robot 3D Companion
 * Interactive, animated kawaii robot that stands beside the 3D chart card.
 * Features:
 *  - Blinking glowing eyes & blushing cheeks
 *  - Antenna wobble with glowing heart tip
 *  - Head smoothly tracks mouse / touch position
 *  - Idle bounce & cheerful arm waves
 *  - Interactive click / tap: jumps with joy, waves arms & bursts floating hearts 💖
 *  - Ambient magical sparkles ✨⭐
 */
export function createCutePetRobot({
  scene,
  camera,
  domElement,
  position = [8.5, 0, 1.0],
  scale = 1.12,
  rotationY = -Math.PI / 8,
  onPetClick = null
}) {
  const robotRoot = new THREE.Group();
  robotRoot.position.set(position[0], position[1], position[2]);
  robotRoot.scale.set(scale, scale, scale);
  robotRoot.rotation.y = rotationY;
  scene.add(robotRoot);

  // Dedicated light for cute pastel shading
  const robotLight = new THREE.PointLight(0xffd5ea, 0.95, 16);
  robotLight.position.set(2, 4, 3);
  robotRoot.add(robotLight);

  // Reusable Materials
  const mat = (c, r = 0.35, m = 0.05) =>
    new THREE.MeshStandardMaterial({ color: c, roughness: r, metalness: m });

  const pearl = mat(0xfff6f9, 0.3, 0.04);
  const pink = mat(0xffb3d1, 0.35, 0.05);
  const lav = mat(0xcdb8ff, 0.35, 0.05);
  const plate = mat(0x3a2f4a, 0.25, 0.2);
  const glow = new THREE.MeshBasicMaterial({ color: 0x9ffcff });
  const white = new THREE.MeshBasicMaterial({ color: 0xffffff });
  const blushMat = new THREE.MeshBasicMaterial({ color: 0xff8fb8, transparent: true, opacity: 0.85 });
  const heartTip = new THREE.MeshBasicMaterial({ color: 0xff6fa8 });

  // Geometry helper
  function sph(r, mt, sx = 1, sy = 1, sz = 1, seg = 32) {
    const m = new THREE.Mesh(new THREE.SphereGeometry(r, seg, seg), mt);
    m.scale.set(sx, sy, sz);
    m.castShadow = true;
    m.receiveShadow = true;
    return m;
  }

  // Blob shadow texture
  function createShadowTexture() {
    const c = document.createElement('canvas');
    c.width = c.height = 128;
    const g = c.getContext('2d');
    const gr = g.createRadialGradient(64, 64, 4, 64, 64, 62);
    gr.addColorStop(0, 'rgba(120,60,110,0.45)');
    gr.addColorStop(1, 'rgba(120,60,110,0)');
    g.fillStyle = gr;
    g.fillRect(0, 0, 128, 128);
    const tex = new THREE.CanvasTexture(c);
    tex.generateMipmaps = false;
    tex.minFilter = THREE.LinearFilter;
    return tex;
  }

  const shadowTex = createShadowTexture();
  const shadowGeo = new THREE.PlaneGeometry(2.6, 2.6);
  const shadowMat = new THREE.MeshBasicMaterial({ map: shadowTex, transparent: true, depthWrite: false });
  const shadow = new THREE.Mesh(shadowGeo, shadowMat);
  shadow.rotation.x = -Math.PI / 2;
  shadow.position.y = 0.02;
  robotRoot.add(shadow);

  // Main Pet Group (moves with bounce / jump)
  const pet = new THREE.Group();
  robotRoot.add(pet);

  // Body & Belly
  const body = sph(0.6, pink, 1, 1.05, 0.9);
  body.position.y = 0.85;
  pet.add(body);

  const belly = sph(0.38, pearl, 1, 1, 0.4);
  belly.position.set(0, 0.8, 0.46);
  pet.add(belly);

  // Feet
  [-1, 1].forEach((s) => {
    const f = sph(0.2, lav, 1, 0.6, 1.3);
    f.position.set(s * 0.28, 0.14, 0.12);
    pet.add(f);
  });

  // Arms
  function makeArm(x) {
    const g = new THREE.Group();
    g.position.set(x, 1.2, 0);
    const a = sph(0.16, lav, 0.9, 1.8, 0.9);
    a.position.y = -0.22;
    g.add(a);
    pet.add(g);
    return g;
  }
  const armL = makeArm(-0.62);
  const armR = makeArm(0.62);

  // Head Group
  const head = new THREE.Group();
  head.position.y = 2.2;
  pet.add(head);

  // Head Base
  head.add(sph(0.95, pearl, 1.15, 0.95, 1, 48));

  // Visor Face Screen
  const face = sph(1, plate, 0.85, 0.6, 0.35, 48);
  face.position.z = 0.72;
  head.add(face);

  // Eyes, Cheeks, Ears
  const eyes = [];
  [-1, 1].forEach((s) => {
    const eg = new THREE.Group();
    eg.position.set(s * 0.32, 0.05, 1.04);
    eg.add(sph(0.14, glow, 1, 1.3, 0.4));
    const h = sph(0.045, white, 1, 1, 0.5);
    h.position.set(0.04, 0.09, 0.05);
    eg.add(h);
    head.add(eg);
    eyes.push(eg);

    const b = sph(0.12, blushMat, 1, 0.6, 0.3);
    b.position.set(s * 0.55, -0.15, 0.97);
    head.add(b);

    const ear = sph(0.24, pink, 1, 1, 0.6);
    ear.position.set(s * 0.95, 0.65, -0.05);
    head.add(ear);
    const inner = sph(0.12, pearl, 1, 1, 0.5);
    inner.position.set(s * 0.95, 0.65, 0.07);
    head.add(inner);
  });

  // Torus Smile Mouth
  const mouth = new THREE.Mesh(new THREE.TorusGeometry(0.07, 0.013, 8, 20, Math.PI), glow);
  mouth.rotation.z = Math.PI;
  mouth.position.set(0, -0.14, 1.07);
  head.add(mouth);

  // Antenna + Heart Tip
  const ant = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.35, 8), lav);
  ant.position.y = 1.07;
  head.add(ant);

  const tip = sph(0.12, heartTip);
  tip.position.y = 1.3;
  head.add(tip);

  // Emoji Canvas Texture Cache
  const texCache = {};
  function emojiTex(ch) {
    if (texCache[ch]) return texCache[ch];
    const c = document.createElement('canvas');
    c.width = c.height = 128;
    const g = c.getContext('2d');
    g.font = '92px "Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",sans-serif';
    g.textAlign = 'center';
    g.textBaseline = 'middle';
    g.fillText(ch, 64, 70);
    const tex = new THREE.CanvasTexture(c);
    tex.generateMipmaps = false;
    tex.minFilter = THREE.LinearFilter;
    return (texCache[ch] = tex);
  }

  function makeSprite(ch, spriteSize) {
    const s = new THREE.Sprite(
      new THREE.SpriteMaterial({ map: emojiTex(ch), transparent: true, depthWrite: false })
    );
    s.scale.set(spriteSize, spriteSize, 1);
    return s;
  }

  // Floating Sparkles around the pet
  const sparkles = [];
  for (let i = 0; i < 18; i++) {
    const s = makeSprite(i % 2 ? '✨' : '⭐', 0.28 + Math.random() * 0.2);
    s.position.set(
      (Math.random() - 0.5) * 4.5,
      Math.random() * 3.8 + 0.3,
      (Math.random() - 0.5) * 3.5
    );
    s.userData = {
      base: s.position.clone(),
      ph: Math.random() * 6.28,
      sp: 0.4 + Math.random() * 0.6
    };
    robotRoot.add(s);
    sparkles.push(s);
  }

  // Heart Burst Particles
  const hearts = [];
  function burst(n = 8) {
    const heartEmojis = ['💖', '💕', '💗', '💓'];
    for (let i = 0; i < n; i++) {
      const ch = heartEmojis[i % heartEmojis.length];
      const s = makeSprite(ch, 0.38 + Math.random() * 0.25);
      s.position.set(
        (Math.random() - 0.5) * 0.8,
        3.2,
        (Math.random() - 0.5) * 0.8
      );
      s.userData = {
        v: new THREE.Vector3(
          (Math.random() - 0.5) * 1.8,
          1.5 + Math.random() * 1.4,
          (Math.random() - 0.5) * 1.2
        ),
        life: 0,
        max: 1.6 + Math.random() * 0.8
      };
      robotRoot.add(s);
      hearts.push(s);
    }
  }

  // Interactive State
  const ray = new THREE.Raycaster();
  const ptr = new THREE.Vector2();
  let look = { x: 0, y: 0 };
  let jump = -1;
  let wave = 0;
  let nextBlink = 2;
  let blinkT = -1;
  let downAt = null;

  // Pointer tracking & click reactions
  const onPointerMove = (e) => {
    if (!domElement) return;
    const rect = domElement.getBoundingClientRect();
    look.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    look.y = ((e.clientY - rect.top) / rect.height) * 2 - 1;
  };

  const onPointerDown = (e) => {
    downAt = { x: e.clientX, y: e.clientY };
  };

  const onPointerUp = (e) => {
    if (!downAt || !domElement || !camera) return;
    if (Math.hypot(e.clientX - downAt.x, e.clientY - downAt.y) > 8) return; // Ignore drag/orbit

    const rect = domElement.getBoundingClientRect();
    ptr.set(
      ((e.clientX - rect.left) / rect.width) * 2 - 1,
      -((e.clientY - rect.top) / rect.height) * 2 + 1
    );

    ray.setFromCamera(ptr, camera);
    const hits = ray.intersectObject(pet, true);
    if (hits.length > 0) {
      jump = 0;
      wave = 1.8;
      burst(9);
      if (typeof onPetClick === 'function') {
        onPetClick();
      }
    }
  };

  if (domElement) {
    domElement.addEventListener('pointermove', onPointerMove);
    domElement.addEventListener('pointerdown', onPointerDown);
    domElement.addEventListener('pointerup', onPointerUp);
  }

  // Tag meshes for hover identification
  pet.traverse((child) => {
    if (child.isMesh) {
      child.userData = {
        label: 'Cute Pet Robot 💖',
        val: 'Tap me to jump & wave!'
      };
    }
  });

  // Initial greeting burst
  setTimeout(() => burst(6), 400);

  // Animation Update Function (called in ThreeCanvas render loop)
  const update = (dt = 0.016, t = 0) => {
    // 1. Idle bounce + jump
    let h = Math.abs(Math.sin(t * 2.4)) * 0.06;
    let sy = 1 + Math.sin(t * 4.8) * 0.015;

    if (jump >= 0) {
      jump += dt;
      const p = Math.min(jump / 0.8, 1);
      h += Math.sin(p * Math.PI) * 1.15;
      sy = 1 + Math.sin(p * Math.PI) * 0.12 - (p < 0.12 || p > 0.88 ? 0.1 : 0);
      if (jump > 0.8) jump = -1;
    }

    pet.position.y = h;
    pet.scale.set(1 / Math.sqrt(sy), sy, 1 / Math.sqrt(sy));

    const sh = 1 - h * 0.35;
    shadow.scale.set(sh, sh, sh);
    shadow.material.opacity = Math.max(0.4, 1 - h * 0.4);

    // 2. Head follows cursor
    head.rotation.y += (look.x * 0.45 + Math.sin(t * 0.8) * 0.06 - head.rotation.y) * 0.08;
    head.rotation.x += (look.y * 0.2 - head.rotation.x) * 0.08;
    head.rotation.z = Math.sin(t * 1.4) * 0.04;

    // 3. Blinking animation
    if (blinkT < 0 && t > nextBlink) blinkT = 0;
    let eyeScaleY = 1;
    if (blinkT >= 0) {
      blinkT += dt;
      eyeScaleY = Math.abs(1 - Math.sin(Math.min(blinkT / 0.18, 1) * Math.PI) * 0.92);
      if (blinkT > 0.18) {
        blinkT = -1;
        nextBlink = t + 2.2 + Math.random() * 3.5;
        eyeScaleY = 1;
      }
    }
    eyes.forEach((g) => {
      g.scale.y = eyeScaleY;
    });

    // 4. Arms waving / idle swing
    wave = Math.max(0, wave - dt);
    armR.rotation.z = wave > 0 ? 2.3 + Math.sin(t * 14) * 0.35 : 0.15 + Math.sin(t * 2.4) * 0.05;
    armL.rotation.z = wave > 0 ? -2.3 - Math.sin(t * 14) * 0.35 : -0.15 - Math.sin(t * 2.4 + 1) * 0.05;

    // 5. Antenna wobble & glow pulsation
    tip.scale.setScalar(1 + Math.sin(t * 5) * 0.15);
    ant.rotation.z = Math.sin(t * 3) * 0.12;
    tip.position.x = Math.sin(ant.rotation.z) * -0.23;

    // 6. Ambient sparkles float
    sparkles.forEach((s) => {
      const d = s.userData;
      s.position.y = d.base.y + Math.sin(t * d.sp + d.ph) * 0.3;
      s.position.x = d.base.x + Math.cos(t * d.sp * 0.7 + d.ph) * 0.15;
      s.material.opacity = 0.5 + Math.sin(t * 2 * d.sp + d.ph) * 0.4;
    });

    // 7. Heart burst particle physics
    for (let i = hearts.length - 1; i >= 0; i--) {
      const s = hearts[i];
      const d = s.userData;
      d.life += dt;
      d.v.y -= dt * 0.9;
      s.position.addScaledVector(d.v, dt);
      s.material.opacity = Math.max(0, 1 - d.life / d.max);
      if (d.life > d.max) {
        robotRoot.remove(s);
        s.material.dispose();
        hearts.splice(i, 1);
      }
    }
  };

  // Cleanup / Dispose
  const dispose = () => {
    if (domElement) {
      domElement.removeEventListener('pointermove', onPointerMove);
      domElement.removeEventListener('pointerdown', onPointerDown);
      domElement.removeEventListener('pointerup', onPointerUp);
    }
    scene.remove(robotRoot);
    robotRoot.traverse((child) => {
      if (child.geometry) child.geometry.dispose();
      if (child.material) {
        if (Array.isArray(child.material)) {
          child.material.forEach((m) => m.dispose());
        } else {
          child.material.dispose();
        }
      }
    });
    shadowTex.dispose();
    Object.values(texCache).forEach((tex) => tex.dispose());
  };

  return {
    group: robotRoot,
    pet,
    head,
    update,
    burst,
    dispose
  };
}
