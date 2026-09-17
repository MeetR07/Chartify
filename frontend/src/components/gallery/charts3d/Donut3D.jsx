import React, { useCallback } from 'react';
import * as THREE from 'three';
import ThreeScene from '../ThreeScene';

export default function Donut3D({ data, autoRotate, onResetRef, onHover }) {
  const buildScene = useCallback((scene, interactiveList, disposables) => {
    const total = data.reduce((sum, d) => sum + d.value, 0) || 1;
    let currentAngle = 0;
    const outerRadius = 4.2;
    const innerRadius = 2.2;
    const thickness = 1.3;
    const gapAngle = 0.04; // Angular gap between segments

    data.forEach((d) => {
      const sliceAngle = (d.value / total) * Math.PI * 2;
      const actualAngle = Math.max(sliceAngle - gapAngle, 0.02);
      const startA = currentAngle + gapAngle / 2;
      const endA = startA + actualAngle;
      const midA = (startA + endA) / 2;
      const percent = Math.round((d.value / total) * 100);

      // Construct 2D ring segment shape
      const shape = new THREE.Shape();
      shape.moveTo(Math.cos(startA) * innerRadius, Math.sin(startA) * innerRadius);
      shape.lineTo(Math.cos(startA) * outerRadius, Math.sin(startA) * outerRadius);
      shape.absarc(0, 0, outerRadius, startA, endA, false);
      shape.lineTo(Math.cos(endA) * innerRadius, Math.sin(endA) * innerRadius);
      shape.absarc(0, 0, innerRadius, endA, startA, true);
      shape.closePath();

      const extrudeSettings = {
        depth: thickness,
        bevelEnabled: true,
        bevelSegments: 3,
        steps: 1,
        bevelSize: 0.08,
        bevelThickness: 0.08
      };

      const geo = new THREE.ExtrudeGeometry(shape, extrudeSettings);
      const mat = new THREE.MeshStandardMaterial({
        color: d.color,
        metalness: 0.35,
        roughness: 0.3
      });

      const mesh = new THREE.Mesh(geo, mat);
      // Flat on X-Z floor with Y elevation
      mesh.rotation.x = -Math.PI / 2;
      mesh.position.y = 1.6;
      mesh.castShadow = true;
      mesh.receiveShadow = true;

      mesh.userData = {
        data: {
          name: d.name,
          category: 'Segment Share',
          value: d.value,
          percent: percent,
          color: d.color
        },
        midAngle: midA,
        baseY: 1.6
      };

      scene.add(mesh);
      interactiveList.push(mesh);
      disposables.push(geo, mat);

      currentAngle += sliceAngle;
    });
  }, [data]);

  return (
    <ThreeScene
      buildScene={buildScene}
      autoRotate={autoRotate}
      onResetRef={onResetRef}
      onHover={onHover}
      cameraPos={[11, 13, 13]}
      lookAt={[0, 1.6, 0]}
    />
  );
}
