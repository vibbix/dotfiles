import * as THREE from 'three';
import { SVGLoader } from 'three/addons/loaders/SVGLoader.js';

let scene: THREE.Scene, camera: THREE.PerspectiveCamera, renderer: THREE.WebGLRenderer, container: HTMLElement | null;
const objects: THREE.Object3D[] = [];

const addExtraShapes = false;

init();
animate();

function init() {
    container = document.getElementById('display-container');
    if (!container) return;

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
    camera.position.z = 12;

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);

    // Enhanced Lighting for Purple Environment
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
    scene.add(ambientLight);

    const purpleLight = new THREE.PointLight(0xbd93f9, 100);
    purpleLight.position.set(-5, 5, 5);
    scene.add(purpleLight);

    const whiteLight = new THREE.PointLight(0xffffff, 80);
    whiteLight.position.set(5, -5, 10);
    scene.add(whiteLight);

    // Frosted Glass Material base components
    const glassMaterialProps = {
        thickness: 0.8,
        roughness: 0.1,
        transmission: 1,
        ior: 1.45,
        attenuationDistance: 0.5,
        transparent: true,
        opacity: 0.9,
        envMapIntensity: 1
    };

    // Geometry Generation
    const shapes = [createGearShape(), createPlayShape(), createPlusShape()];

    if (addExtraShapes) {
        const glassMaterial = new THREE.MeshPhysicalMaterial({
            ...glassMaterialProps,
            attenuationColor: new THREE.Color(0xffffff)
        });

        for (let i = 0; i < 12; i++) {
            const shape = shapes[Math.floor(Math.random() * shapes.length)];
            const extrudeSettings = { depth: 0.5, bevelEnabled: true, bevelThickness: 0.1, bevelSize: 0.1 };
            const geometry = new THREE.ExtrudeGeometry(shape, extrudeSettings);

            const mesh = new THREE.Mesh(geometry, glassMaterial);

            mesh.position.set(
                (Math.random() - 0.5) * 15,
                (Math.random() - 0.5) * 10,
                (Math.random() - 0.5) * 5
            );
            mesh.rotation.set(Math.random() * Math.PI, Math.random() * Math.PI, 0);
            mesh.scale.set(0.4, 0.4, 0.4);

            scene.add(mesh);
            objects.push(mesh);
        }
    }

    const loader = new SVGLoader();
    loader.load('https://upload.wikimedia.org/wikipedia/commons/7/7d/Bazel_logo.svg', (data) => {
        const paths = data.paths;
        const group = new THREE.Group(); // Put all parts in a group to manage them easily

        paths.forEach((path: any) => {
            // Use SVGLoader's createShapes which handles holes properly
            const shapes = SVGLoader.createShapes(path);

            // Get color from the SVG path
            const materialColor = path.color;

            // Create a glass material tinted with the SVG color
            const pathGlassMaterial = new THREE.MeshPhysicalMaterial({
                ...glassMaterialProps,
                color: materialColor,
                attenuationColor: materialColor
            });

            shapes.forEach((shape) => {
                const geometry = new THREE.ExtrudeGeometry(shape, {
                    depth: 2, // Thicker for better glass refraction
                    bevelEnabled: true,
                    bevelThickness: 0.5,
                    bevelSize: 0.5
                });

                const mesh = new THREE.Mesh(geometry, pathGlassMaterial);
                group.add(mesh);
            });
        });

        // Center the entire SVG after combining
        const box = new THREE.Box3().setFromObject(group);
        const center = new THREE.Vector3();
        box.getCenter(center);
        group.position.sub(center); // Offset the group to be centered around(0,0,0)

        // We use a wrapper group so we can apply rotation and scaling
        // without messing up our center offset
        const wrapper = new THREE.Group();
        wrapper.add(group);

        // 2. Scale it down! SVG pixels (100+) -> Three.js units (~1-5)
        wrapper.scale.set(0.02, 0.02, 0.02);

        // 3. Correct the orientation (SVGs are Y-down, Three.js is Y-up)
        wrapper.rotation.x = Math.PI;
        // To help fix visual errors between overlapping extrusions sharing exactly the same Z plan, slightly angle it or disable depthWrite for pure transparents.

        scene.add(wrapper);
        objects.push(wrapper); // Add to your animation array
    },
        // Progress callback
        undefined,
        // Error callback
        (error: any) => {
            console.error('An error happened loading the SVG:', error);
        });
}

// Custom Shapes
function createGearShape(): THREE.Shape {
    const s = new THREE.Shape();
    s.absarc(0, 0, 3, 0, Math.PI * 2, false);
    const hole = new THREE.Path();
    hole.absarc(0, 0, 1.5, 0, Math.PI * 2, true);
    s.holes.push(hole);
    return s;
}

function createPlayShape(): THREE.Shape {
    const s = new THREE.Shape();
    s.moveTo(0, 0); s.lineTo(0, 6); s.lineTo(5, 3); s.lineTo(0, 0);
    return s;
}

function createPlusShape(): THREE.Shape {
    const s = new THREE.Shape();
    s.moveTo(-1, 3); s.lineTo(1, 3); s.lineTo(1, 1); s.lineTo(3, 1);
    s.lineTo(3, -1); s.lineTo(1, -1); s.lineTo(1, -3); s.lineTo(-1, -3);
    s.lineTo(-1, -1); s.lineTo(-3, -1); s.lineTo(-3, 1); s.lineTo(-1, 1);
    return s;
}

function animate() {
    requestAnimationFrame(animate);
    objects.forEach((obj, i) => {
        obj.rotation.x += 0.005;
        obj.rotation.y += 0.005;
        obj.position.y += Math.sin(Date.now() * 0.001 + i) * 0.003;
    });
    if (scene && camera && renderer) {
        renderer.render(scene, camera);
    }
}

window.addEventListener('resize', () => {
    if (!camera || !renderer || !container) return;
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
});