import React, { useCallback } from 'react';
import * as THREE from 'three';
import ThreeScene from '../ThreeScene';

export default function Radar3D({ data, autoRotate, onResetRef, onHover }) {
  const buildScene = useCallback((scene, interactiveList, disposables) => {
    const numAxes = data.length;
    const maxRadius = 4.8;
    const height = 1.2;
    const angleStep = (Math.PI * 2) / numAxes;

    // Concentric Web Grid Rings
    [0.25, 0.5, 0.75, 1.0].forEach((level) => {
      const ringPoints = [];
      for (let i = 0; i <= numAxes; i++) {
        const a = i * angleStep - Math.PI / 2;
        const r = maxRadius * level;
        ringPoints.push(new THREE.Vector3(Math.cos(a) * r, 0.05, Math.sin(a) * r));
      }
      const ringGeo = new THREE.BufferGeometry().setFromPoints(ringPoints);
      const ringMat = new THREE.LineBasicMaterial({
        color: 0x013e37,
        opacity: level === 1.0 ? 0.45 : 0.2,
        transparent: true
      });
      const ringLine = new THREE.Line(ringGeo, ringMat);
      scene.add(ringLine);
      disposables.push(ringGeo, ringMat);
    });

    // 3D Axis Poles
    data.forEach((d, i) => {
      const a = i * angleStep - Math.PI / 2;
      const x = Math.cos(a) * maxRadius;
      const z = Math.sin(a) * maxRadius;

      // Axis line
      const axisGeo = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(0, 0.05, 0),
        new THREE.Vector3(x, 0.05, z)
      ]);
      const axisMat = new THREE.LineBasicMaterial({ color: 0x013e37, opacity: 0.35, transparent: true });
      const axisLine = new THREE.Line(axisGeo, axisMat);
      scene.add(axisLine);
      disposables.push(axisGeo, axisMat);

      // Outer Axis Marker Pole
      const poleGeo = new THREE.CylinderGeometry(0.08, 0.08, 1.6, 12);
      const poleMat = new THREE.MeshStandardMaterial({ color: 0x013e37, metalness: 0.4, roughness: 0.3 });
      const pole = new THREE.Mesh(poleGeo, poleMat);
      pole.position.set(x, 0.8, z);
      scene.add(pole);
      disposables.push(poleGeo, poleMat);
    });

    // Build 3D Tiered Polygonal Mesh (Bottom and Top Faces + Side Walls)
    const topPoints = [];
    const bottomPoints = [];

    data.forEach((d, i) => {
      const a = i * angleStep - Math.PI / 2;
      const r = (d.value / d.fullMark) * maxRadius;
      const x = Math.cos(a) * r;
      const z = Math.sin(a) * r;

      topPoints.push(new THREE.Vector3(x, height, z));
      bottomPoints.push(new THREE.Vector3(x, 0.15, z));

      // 3D Marker Sphere on each vertex
      const nodeGeo = new THREE.SphereGeometry(0.24, 16, 16);
      const nodeMat = new THREE.MeshStandardMaterial({
        color: 0x08ab9c,
        metalness: 0.5,
        roughness: 0.2
      });
      const node = new THREE.Mesh(nodeGeo, nodeMat);
      node.position.set(x, height, z);
      node.castShadow = true;
      node.userData = {
        data: {
          name: d.axis,
          category: 'Radar Axis',
          value: d.value,
          percent: Math.round((d.value / d.fullMark) * 100),
          color: '#08ab9c'
        }
      };
      scene.add(node);
      interactiveList.push(node);
      disposables.push(nodeGeo, nodeMat);
    });

    // Side Walls & Top Cap using ExtrudeGeometry on custom 2D Shape
    const radarShape = new THREE.Shape();
    data.forEach((d, i) => {
      const a = i * angleStep - Math.PI / 2;
      const r = (d.value / d.fullMark) * maxRadius;
      const x = Math.cos(a) * r;
      const y = Math.sin(a) * r;
      if (i === 0) radarShape.moveTo(x, y);
      else radarShape.lineTo(x, y);
    });
    radarShape.closePath();

    const extrudeSettings = {
      depth: height - 0.15,
      bevelEnabled: true,
      bevelSegments: 2,
      steps: 1,
      bevelSize: 0.06,
      bevelThickness: 0.06
    };

    const radarMeshGeo = new THREE.ExtrudeGeometry(radarShape, extrudeSettings);
    const radarMeshMat = new THREE.MeshStandardMaterial({
      color: 0x08ab9c,
      metalness: 0.25,
      roughness: 0.35,
      transparent: true,
      opacity: 0.78
    });

    const radarMesh = new THREE.Mesh(radarMeshGeo, radarMeshMat);
    radarMesh.rotation.x = -Math.PI / 2;
    radarMesh.position.y = 0.15;
    radarMesh.castShadow = true;
    radarMesh.receiveShadow = true;

    radarMesh.userData = {
      data: {
        name: 'Full Radar Polygon',
        category: '3D Spatial Mesh',
        value: `${Math.round(data.reduce((a, b) => a + b.value, 0) / data.length)} Avg Score`,
        color: '#08ab9c'
      }
    };

    scene.add(radarMesh);
    interactiveList.push(radarMesh);
    disposables.push(radarMeshGeo, radarMeshMat);
  }, [data]);

  return (
    <ThreeScene
      buildScene={buildScene}
      autoRotate={autoRotate}
      onResetRef={onResetRef}
      onHover={onHover}
      cameraPos={[13, 11, 14]}
      lookAt={[0, 0.8, 0]}
    />
  );
}
