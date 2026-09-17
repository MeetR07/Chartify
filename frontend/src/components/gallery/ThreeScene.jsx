import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

export default function ThreeScene({
  buildScene,
  autoRotate = false,
  onResetRef,
  onHover,
  cameraPos = [14, 12, 16],
  lookAt = [0, 1.5, 0]
}) {
  const mountRef = useRef(null);
  const controlsRef = useRef(null);
  const cameraRef = useRef(null);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    // 1. Scene
    const scene = new THREE.Scene();

    const width = container.clientWidth || 360;
    const height = container.clientHeight || 280;

    // 2. Camera
    const camera = new THREE.PerspectiveCamera(42, width / height, 0.1, 1000);
    camera.position.set(...cameraPos);
    camera.lookAt(new THREE.Vector3(...lookAt));
    cameraRef.current = camera;

    // 3. Renderer
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance'
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFShadowMap;
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // 4. OrbitControls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.06;
    controls.target.set(...lookAt);
    controls.maxPolarAngle = Math.PI / 2 - 0.04; // Never clip below floor
    controls.minDistance = 5;
    controls.maxDistance = 45;
    controls.autoRotate = autoRotate;
    controls.autoRotateSpeed = 1.0;
    controlsRef.current = controls;

    if (onResetRef) {
      onResetRef.current = () => {
        camera.position.set(...cameraPos);
        controls.target.set(...lookAt);
        controls.update();
      };
    }

    // 5. Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.85);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 1.3);
    dirLight.position.set(12, 22, 12);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 1024;
    dirLight.shadow.mapSize.height = 1024;
    dirLight.shadow.camera.near = 0.5;
    dirLight.shadow.camera.far = 60;
    dirLight.shadow.bias = -0.0005;
    scene.add(dirLight);

    const rimLight = new THREE.DirectionalLight(0xffefb3, 0.5);
    rimLight.position.set(-12, 8, -12);
    scene.add(rimLight);

    // 6. Ground Grid & Shadow Receiver
    const gridHelper = new THREE.GridHelper(20, 20, 0x013e37, 0x013e37);
    gridHelper.position.y = 0;
    gridHelper.material.opacity = 0.22;
    gridHelper.material.transparent = true;
    scene.add(gridHelper);

    const shadowPlaneGeo = new THREE.PlaneGeometry(24, 24);
    const shadowPlaneMat = new THREE.ShadowMaterial({ opacity: 0.14 });
    const shadowPlane = new THREE.Mesh(shadowPlaneGeo, shadowPlaneMat);
    shadowPlane.rotation.x = -Math.PI / 2;
    shadowPlane.position.y = -0.01;
    shadowPlane.receiveShadow = true;
    scene.add(shadowPlane);

    // 7. Populate Scene with Chart-Specific Geometry
    const interactiveObjects = [];
    const disposables = [];

    if (buildScene) {
      buildScene(scene, interactiveObjects, disposables);
    }

    // 8. Raycaster for Tooltips
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const handlePointerMove = (e) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(interactiveObjects, true);

      if (intersects.length > 0) {
        let hitObj = intersects[0].object;
        while (hitObj && !hitObj.userData?.data && hitObj.parent !== scene) {
          hitObj = hitObj.parent;
        }

        if (hitObj?.userData?.data && onHover) {
          onHover(hitObj.userData.data, {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
          });
          container.style.cursor = 'pointer';
          return;
        }
      }

      if (onHover) onHover(null);
      container.style.cursor = 'grab';
    };

    renderer.domElement.addEventListener('pointermove', handlePointerMove);

    // 9. Animation Loop
    let animId;
    const animate = () => {
      animId = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // 10. Resize Observer
    const resizeObserver = new ResizeObserver(() => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    });
    resizeObserver.observe(container);

    // 11. Cleanup
    return () => {
      cancelAnimationFrame(animId);
      resizeObserver.disconnect();
      renderer.domElement.removeEventListener('pointermove', handlePointerMove);
      controls.dispose();

      disposables.forEach((item) => {
        if (item.geometry) item.geometry.dispose();
        if (item.material) {
          if (Array.isArray(item.material)) item.material.forEach((m) => m.dispose());
          else item.material.dispose();
        }
      });

      renderer.dispose();
      scene.clear();
    };
  }, [buildScene]);

  // Update autoRotate dynamically
  useEffect(() => {
    if (controlsRef.current) {
      controlsRef.current.autoRotate = autoRotate;
    }
  }, [autoRotate]);

  return <div ref={mountRef} className="three-scene-canvas" />;
}
