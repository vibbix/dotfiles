
import * as THREE from 'three/webgpu';

// Custom Shapes
export function createGearShape(): THREE.Shape {
    const s = new THREE.Shape();
    s.absarc(0, 0, 3, 0, Math.PI * 2, false);
    const hole = new THREE.Path();
    hole.absarc(0, 0, 1.5, 0, Math.PI * 2, true);
    s.holes.push(hole);
    return s;
}

export function createPlayShape(): THREE.Shape {
    const s = new THREE.Shape();
    s.moveTo(0, 0); s.lineTo(0, 6); s.lineTo(5, 3); s.lineTo(0, 0);
    return s;
}

export function createPlusShape(): THREE.Shape {
    const s = new THREE.Shape();
    s.moveTo(-1, 3); s.lineTo(1, 3); s.lineTo(1, 1); s.lineTo(3, 1);
    s.lineTo(3, -1); s.lineTo(1, -1); s.lineTo(1, -3); s.lineTo(-1, -3);
    s.lineTo(-1, -1); s.lineTo(-3, -1); s.lineTo(-3, 1); s.lineTo(-1, 1);
    return s;
}

export function createBazelLogo(material?: THREE.Material): THREE.Group {
    const group = new THREE.Group();
    const geometry = new THREE.BoxGeometry(1, 1, 1);

    const mainMaterial = material ? material.clone() : new THREE.MeshStandardMaterial();
    if ('color' in mainMaterial) (mainMaterial as any).color.set('#76D275');

    const centerMaterial = material ? material.clone() : new THREE.MeshStandardMaterial();
    if ('color' in centerMaterial) (centerMaterial as any).color.set('#43A047');

    // The Bazel logo consists of 3 cubes arranged to form a heart-like shape
    // when viewed from an isometric perspective.
    const leftCube = new THREE.Mesh(geometry, mainMaterial);
    leftCube.position.set(-1, 0, 0);

    const rightCube = new THREE.Mesh(geometry, mainMaterial);
    rightCube.position.set(0, 0, -1);

    const bottomCube = new THREE.Mesh(geometry, centerMaterial);
    bottomCube.position.set(0, 0, 0);

    group.add(leftCube);
    group.add(rightCube);
    group.add(bottomCube);

    return group;
}