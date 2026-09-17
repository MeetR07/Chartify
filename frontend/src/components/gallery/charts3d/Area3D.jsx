import React, { useCallback } from 'react';
import * as THREE from 'three';
import ThreeScene from '../ThreeScene';

export default function Area3D({ data, autoRotate, onResetRef, onHover }) {
  const buildScene = useCallback((scene, interactiveList, disposables) => {
    const numPoints = data.labels.length;
    const spacingX = 1.8;
    const startX = -((numPoints - 1) * spacingX) / 2;
    const laneSpacingZ = 2.4;
    const numSeries = data.series.length;
    const startZ = -((numSeries - 1) * laneSpacingZ) / 2;
    const unitScale = 0.065;

    data.series.forEach((s, si) => {
      const posZ = startZ + si * laneSpacingZ;

      // Build 3D Extruded Ribbon Profile for this series
      const shape = new THREE.Shape();
      shape.moveTo(startX, 0);

      s.values.forEach((v, vi) => {
        const px = startX + vi * spacingX;
        const py = Math.max(v * unitScale, 0.2);
        shape.lineTo(px, py);
      });

      // Close polygon to ground
      shape.lineTo(startX + (numPoints - 1) * spacingX, 0);
      shape.closePath();

      const extrudeSettings = {
        depth: 0.8,
        bevelEnabled: true,
        bevelSegments: 2,
        steps: 1,
        bevelSize: 0.06,
        bevelThickness: 0.06
      };

      const geo = new THREE.ExtrudeGeometry(shape, extrudeSettings);
      const mat = new THREE.MeshStandardMaterial({
        color: s.color,
        metalness: 0.35,
        roughness: 0.3,
        transparent: true,
        opacity: 0.88
      });

      const mesh = new THREE.Mesh(geo, mat);
      // Center along Z-lane
      mesh.position.set(0, 0, posZ - 0.4);
      mesh.castShadow = true;
      mesh.receiveShadow = true;

      mesh.userData = {
        data: {
          name: s.name,
          category: `Z-Lane ${si + 1}`,
          value: `${s.values[s.values.length - 1]} Final`,
          color: s.color
        }
      };

      scene.add(mesh);
      interactiveList.push(mesh);
      disposables.push(geo, mat);

      // Data Marker Spheres on crest
      s.values.forEach((v, vi) => {
        const px = startX + vi * spacingX;
        const py = Math.max(v * unitScale, 0.2);
        const markerGeo = new THREE.SphereGeometry(0.18, 16, 16);
        const markerMat = new THREE.MeshStandardMaterial({ color: 0xffefb3, metalness: 0.5, roughness: 0.2 });
        const marker = new THREE.Mesh(markerGeo, markerMat);
        marker.position.set(px, py, posZ);
        marker.castShadow = true;

        marker.userData = {
          data: {
            name: `${s.name} (${data.labels[vi]})`,
            category: 'Time Metric',
            value: v,
            color: s.color
          }
        };

        scene.add(marker);
        interactiveList.push(marker);
        disposables.push(markerGeo, markerMat);
      });
    });
  }, [data]);

  return (
    <ThreeScene
      buildScene={buildScene}
      autoRotate={autoRotate}
      onResetRef={onResetRef}
      onHover={onHover}
      cameraPos={[15, 12, 16]}
      lookAt={[0, 2.2, 0]}
    />
  );
}
