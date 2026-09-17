import React, { useCallback } from 'react';
import * as THREE from 'three';
import ThreeScene from '../ThreeScene';

const PALETTE = ['#013E37', '#08ab9c', '#f47a34', '#fc6eae', '#ffbd29', '#146665', '#38bdf8'];

export default function Lollipop3D({ data, autoRotate, onResetRef, onHover }) {
  const buildScene = useCallback((scene, interactiveList, disposables) => {
    const maxVal = Math.max(...data.map((d) => d.value), 1);
    const count = data.length;
    const spacing = 1.8;
    const startX = -((count - 1) * spacing) / 2;
    const maxHeight = 7.0;

    data.forEach((d, i) => {
      const height = Math.max((d.value / maxVal) * maxHeight, 0.6);
      const posX = startX + i * spacing;
      const colorHex = PALETTE[i % PALETTE.length];

      const itemGroup = new THREE.Group();
      itemGroup.position.set(posX, 0, 0);

      // 1. Base ring on ground
      const baseGeo = new THREE.CylinderGeometry(0.5, 0.5, 0.08, 16);
      const baseMat = new THREE.MeshStandardMaterial({ color: 0x013e37, roughness: 0.5 });
      const baseMesh = new THREE.Mesh(baseGeo, baseMat);
      baseMesh.position.y = 0.04;
      itemGroup.add(baseMesh);
      disposables.push(baseGeo, baseMat);

      // 2. Vertical cylinder stem
      const stemRadius = 0.1;
      const stemGeo = new THREE.CylinderGeometry(stemRadius, stemRadius, height, 16);
      const stemMat = new THREE.MeshStandardMaterial({
        color: 0x013e37,
        metalness: 0.4,
        roughness: 0.3
      });
      const stemMesh = new THREE.Mesh(stemGeo, stemMat);
      stemMesh.position.y = height / 2;
      stemMesh.castShadow = true;
      stemMesh.receiveShadow = true;
      itemGroup.add(stemMesh);
      disposables.push(stemGeo, stemMat);

      // 3. Metallic Sphere Tip on top
      const tipRadius = 0.42;
      const tipGeo = new THREE.SphereGeometry(tipRadius, 24, 24);
      const tipMat = new THREE.MeshStandardMaterial({
        color: colorHex,
        metalness: 0.5,
        roughness: 0.25
      });
      const tipMesh = new THREE.Mesh(tipGeo, tipMat);
      tipMesh.position.y = height;
      tipMesh.castShadow = true;
      itemGroup.add(tipMesh);
      disposables.push(tipGeo, tipMat);

      itemGroup.userData = {
        data: {
          name: d.name,
          category: 'Category Metric',
          value: d.value,
          color: colorHex
        }
      };

      scene.add(itemGroup);
      interactiveList.push(itemGroup);
    });
  }, [data]);

  return (
    <ThreeScene
      buildScene={buildScene}
      autoRotate={autoRotate}
      onResetRef={onResetRef}
      onHover={onHover}
      cameraPos={[14, 11, 15]}
      lookAt={[0, 3.2, 0]}
    />
  );
}
