import React, { useCallback } from 'react';
import * as THREE from 'three';
import ThreeScene from '../ThreeScene';

export default function Pie3D({ data, autoRotate, onResetRef, onHover }) {
  const buildScene = useCallback((scene, interactiveList, disposables) => {
    const total = data.reduce((sum, d) => sum + d.value, 0) || 1;
    let currentAngle = 0;
    const radius = 4.4;
    const thickness = 1.3;
    const gapAngle = 0.035;

    data.forEach((d) => {
      const sliceAngle = (d.value / total) * Math.PI * 2;
      const actualAngle = Math.max(sliceAngle - gapAngle, 0.02);
      const startA = currentAngle + gapAngle / 2;
      const endA = startA + actualAngle;
      const midA = (startA + endA) / 2;
      const percent = Math.round((d.value / total) * 100);

      // Construct wedge 2D shape
      const shape = new THREE.Shape();
      shape.moveTo(0, 0);
      shape.lineTo(Math.cos(startA) * radius, Math.sin(startA) * radius);
      shape.absarc(0, 0, radius, startA, endA, false);
      shape.lineTo(0, 0);
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
      mesh.rotation.x = -Math.PI / 2;

      // Slight natural radial offset so wedges don't fight at apex
      const radialOffset = 0.18;
      const offX = Math.cos(midA) * radialOffset;
      const offZ = -Math.sin(midA) * radialOffset; // Note inverted Z for X-Z plane

      mesh.position.set(offX, 1.6, offZ);
      mesh.castShadow = true;
      mesh.receiveShadow = true;

      mesh.userData = {
        data: {
          name: d.name,
          category: 'Pie Slice',
          value: d.value,
          percent: percent,
          color: d.color
        },
        origX: offX,
        origZ: offZ,
        midAngle: midA
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
