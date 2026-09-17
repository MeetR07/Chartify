import React, { useCallback } from 'react';
import * as THREE from 'three';
import ThreeScene from '../ThreeScene';

export default function Treemap3D({ data, autoRotate, onResetRef, onHover }) {
  const buildScene = useCallback((scene, interactiveList, disposables) => {
    // Proportional layout grid over an 8x8 world plane
    const totalVal = data.reduce((sum, d) => sum + d.value, 0) || 1;
    const boxThickness = 0.9;

    // Simple robust squarified layout partition
    // Divide 8x8 units into proportional rectangular tiles
    const tiles = [
      { x: -2.0, z: -2.0, w: 4.0, d: 3.8 },
      { x: 2.1,  z: -2.0, w: 3.8, d: 2.2 },
      { x: 2.1,  z: 0.3,  w: 3.8, d: 1.5 },
      { x: -2.0, z: 2.0,  w: 2.4, d: 3.8 },
      { x: 0.5,  z: 2.0,  w: 2.2, d: 1.8 },
      { x: 2.8,  z: 2.0,  w: 3.1, d: 1.8 },
      { x: 0.5,  z: 3.9,  w: 5.4, d: 1.9 }
    ];

    data.slice(0, tiles.length).forEach((d, i) => {
      const tile = tiles[i];
      const percent = Math.round((d.value / totalVal) * 100);

      // Create 3D Box Geometry
      const geo = new THREE.BoxGeometry(tile.w - 0.12, boxThickness, tile.d - 0.12);
      const mat = new THREE.MeshStandardMaterial({
        color: d.color || '#08ab9c',
        metalness: 0.3,
        roughness: 0.35
      });
      const mesh = new THREE.Mesh(geo, mat);

      // Position center of box
      mesh.position.set(tile.x + tile.w / 2 - 2.0, boxThickness / 2, tile.z + tile.d / 2 - 2.0);
      mesh.castShadow = true;
      mesh.receiveShadow = true;

      mesh.userData = {
        data: {
          name: d.name,
          category: 'Treemap Node',
          value: d.value,
          percent: percent,
          color: d.color
        }
      };

      scene.add(mesh);
      interactiveList.push(mesh);
      disposables.push(geo, mat);
    });
  }, [data]);

  return (
    <ThreeScene
      buildScene={buildScene}
      autoRotate={autoRotate}
      onResetRef={onResetRef}
      onHover={onHover}
      cameraPos={[12, 14, 13]}
      lookAt={[0, 0.5, 0]}
    />
  );
}
