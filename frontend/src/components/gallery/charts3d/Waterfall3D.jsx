import React, { useCallback } from 'react';
import * as THREE from 'three';
import ThreeScene from '../ThreeScene';

export default function Waterfall3D({ data, autoRotate, onResetRef, onHover }) {
  const buildScene = useCallback((scene, interactiveList, disposables) => {
    const count = data.length;
    const spacing = 1.7;
    const startX = -((count - 1) * spacing) / 2;
    const unitScale = 0.055; // Scales balance values to 3D world units

    let currentBalance = 0;

    data.forEach((d, i) => {
      const posX = startX + i * spacing;
      let bottomY = 0;
      let topY = 0;
      let colorHex = '#08ab9c';

      if (d.type === 'start' || d.type === 'total') {
        bottomY = 0;
        topY = d.balance * unitScale;
        colorHex = '#013E37';
        currentBalance = d.balance;
      } else if (d.type === 'positive') {
        bottomY = currentBalance * unitScale;
        topY = (currentBalance + d.delta) * unitScale;
        colorHex = '#10b981';
        currentBalance += d.delta;
      } else {
        // negative
        topY = currentBalance * unitScale;
        bottomY = (currentBalance + d.delta) * unitScale;
        colorHex = '#f43f5e';
        currentBalance += d.delta;
      }

      const prismHeight = Math.max(Math.abs(topY - bottomY), 0.15);
      const centerY = (topY + bottomY) / 2;

      // 3D Prism Mesh
      const geo = new THREE.BoxGeometry(1.1, prismHeight, 1.1);
      const mat = new THREE.MeshStandardMaterial({
        color: colorHex,
        metalness: 0.3,
        roughness: 0.35
      });
      const prism = new THREE.Mesh(geo, mat);
      prism.position.set(posX, centerY, 0);
      prism.castShadow = true;
      prism.receiveShadow = true;

      prism.userData = {
        data: {
          name: d.name,
          category: d.type.toUpperCase(),
          delta: d.delta,
          value: d.balance,
          color: colorHex
        }
      };

      scene.add(prism);
      interactiveList.push(prism);
      disposables.push(geo, mat);

      // Connector line to next prism
      if (i < count - 1) {
        const nextX = posX + spacing;
        const lineY = (d.type === 'start' || d.type === 'total') ? topY : (d.type === 'positive' ? topY : bottomY);

        const lineGeo = new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(posX + 0.55, lineY, 0),
          new THREE.Vector3(nextX - 0.55, lineY, 0)
        ]);
        const lineMat = new THREE.LineDashedMaterial({
          color: 0x013e37,
          dashSize: 0.2,
          gapSize: 0.1,
          opacity: 0.5,
          transparent: true
        });
        const line = new THREE.Line(lineGeo, lineMat);
        line.computeLineDistances();
        scene.add(line);
        disposables.push(lineGeo, lineMat);
      }
    });
  }, [data]);

  return (
    <ThreeScene
      buildScene={buildScene}
      autoRotate={autoRotate}
      onResetRef={onResetRef}
      onHover={onHover}
      cameraPos={[15, 12, 16]}
      lookAt={[0, 2.5, 0]}
    />
  );
}
