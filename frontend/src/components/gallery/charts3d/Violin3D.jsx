import React, { useCallback } from 'react';
import * as THREE from 'three';
import ThreeScene from '../ThreeScene';

const VIOLIN_COLORS = ['#013E37', '#08ab9c', '#f47a34'];

export default function Violin3D({ data, autoRotate, onResetRef, onHover }) {
  const buildScene = useCallback((scene, interactiveList, disposables) => {
    const count = data.length;
    const spacing = 3.8;
    const startX = -((count - 1) * spacing) / 2;

    data.forEach((cohort, ci) => {
      const posX = startX + ci * spacing;
      const colorHex = VIOLIN_COLORS[ci % VIOLIN_COLORS.length];

      // Central backbone stem
      const stemGeo = new THREE.CylinderGeometry(0.06, 0.06, 7.0, 12);
      const stemMat = new THREE.MeshBasicMaterial({ color: 0x013e37, opacity: 0.4, transparent: true });
      const stem = new THREE.Mesh(stemGeo, stemMat);
      stem.position.set(posX, 3.5, 0);
      scene.add(stem);
      disposables.push(stemGeo, stemMat);

      // Median Marker Disc
      const medianY = (cohort.median / 100) * 6.5 + 0.5;
      const discGeo = new THREE.CylinderGeometry(0.7, 0.7, 0.12, 24);
      const discMat = new THREE.MeshStandardMaterial({ color: 0xffefb3, metalness: 0.6, roughness: 0.2 });
      const disc = new THREE.Mesh(discGeo, discMat);
      disc.position.set(posX, medianY, 0);
      scene.add(disc);
      disposables.push(discGeo, discMat);

      // Construct Real 3D Bilateral Kernel Density Surface Mesh
      // Using a curved lathe / loft profile computed from the data points
      const points = [];
      const numSteps = 24;

      for (let s = 0; s <= numSteps; s++) {
        const yNorm = s / numSteps; // 0 to 1
        const yVal = yNorm * 100;
        const yPos = yNorm * 6.5 + 0.5;

        // Gaussian kernel density estimation at this height
        let density = 0;
        cohort.points.forEach((pt) => {
          const diff = (yVal - pt) / 10;
          density += Math.exp(-0.5 * diff * diff);
        });

        const radius = Math.min(Math.max((density / cohort.points.length) * 2.8, 0.1), 1.6);
        points.push(new THREE.Vector2(radius, yPos));
      }

      const latheGeo = new THREE.LatheGeometry(points, 24);
      const latheMat = new THREE.MeshStandardMaterial({
        color: colorHex,
        metalness: 0.35,
        roughness: 0.35,
        transparent: true,
        opacity: 0.85
      });
      const latheMesh = new THREE.Mesh(latheGeo, latheMat);
      latheMesh.position.set(posX, 0, 0);
      latheMesh.castShadow = true;
      latheMesh.receiveShadow = true;

      latheMesh.userData = {
        data: {
          name: cohort.group,
          category: 'KDE Distribution Volume',
          value: `${cohort.median} Median`,
          color: colorHex
        }
      };

      scene.add(latheMesh);
      interactiveList.push(latheMesh);
      disposables.push(latheGeo, latheMat);
    });
  }, [data]);

  return (
    <ThreeScene
      buildScene={buildScene}
      autoRotate={autoRotate}
      onResetRef={onResetRef}
      onHover={onHover}
      cameraPos={[14, 12, 16]}
      lookAt={[0, 3.2, 0]}
    />
  );
}
