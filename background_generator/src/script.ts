import * as THREE from 'three/webgpu';
import { SVGLoader } from 'three/addons/loaders/SVGLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { SvgLogoBuilder, stageObject, type GlassMaterialProps } from './svg-logo-builder';

// Importing the SVGs lets Bun's HTML bundler copy + content-hash them and
// rewrite these to the final asset URLs. SVGLoader fetches them at runtime.
import backstageUrl from '../logos/backstage.svg';
import logoUrl from '../logos/logo.svg';
import k8sUrl from '../logos/k8s.svg';
import dockerUrl from '../logos/docker.svg';
import aiShieldUrl from '../logos/logo-ai-shield.svg';
import { createGearShape, createPlayShape, createPlusShape, createBazelLogo } from './shapes';

let scene: THREE.Scene, camera: THREE.PerspectiveCamera, renderer: THREE.Renderer, container: HTMLElement | null;
const objects: THREE.Object3D[] = [];
const svgLoader = new SVGLoader();

const addExtraShapes = false;

init().then(() => {
    renderer.setAnimationLoop(animate);
}).catch((error) => {
    console.error('An error occurred during initialization:', error);
});

async function init() {
    container = document.getElementById('display-container');
    if (!container) return;

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
    camera.position.z = 12;

    renderer = new THREE.WebGPURenderer({ antialias: true, alpha: true });
    await renderer.init(); // WebGPU device/adapter setup is async
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);

    // Transmissive glass shows the environment via reflection/refraction.
    // Without an environment map, WebGPU renders these surfaces black, so we
    // bake a neutral studio environment (PMREM) for the glass to sample.
    const pmrem = new THREE.PMREMGenerator(renderer);
    scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    pmrem.dispose();

    // Enhanced Lighting for Purple Environment
    const ambientLight = new THREE.AmbientLight("#ffffff", 0.8);
    scene.add(ambientLight);

    const purpleLight = new THREE.PointLight("#bd93f9", 100);
    purpleLight.position.set(-5, 5, 5);
    scene.add(purpleLight);

    const whiteLight = new THREE.PointLight("#ffffff", 80);
    whiteLight.position.set(5, -5, 10);
    scene.add(whiteLight);

    // Frosted Glass Material base components
    const glassMaterialProps: GlassMaterialProps = {
        thickness: 1.0,        // Increased thickness refracts more
        roughness: 0.4,        // Higher roughness diffuses the background heavily (the "frosting")
        transmission: 0.6,     // <1 so the albedo / colorNode (logo color & gradient) still shows
        ior: 1.5,              // Slight indexing tweak (glass is ~1.5)
        attenuationDistance: 0.4, // Shorter distance => stronger tint from attenuationColor
        transparent: true,
        opacity: 1.0,          // Can usually stay at 1 with physical transmission
        envMapIntensity: 1.0,  // Lower so reflections don't wash out the tint (was very mirror-like)
        clearcoat: 1.0,        // Adds a polished sheen on top of the rough frosting
        clearcoatRoughness: 0.1 // Keeps the exterior sheen sharp while interior is frosted
    };

    // Geometry Generation
    const shapes = [createGearShape(), createPlayShape(), createPlusShape()];
    const glassMaterial = new THREE.MeshPhysicalNodeMaterial({
        ...glassMaterialProps,
        attenuationColor: new THREE.Color("#ffffff")
    });


    if (addExtraShapes) {
        const glassMaterial = new THREE.MeshPhysicalNodeMaterial({
            ...glassMaterialProps,
            attenuationColor: new THREE.Color("#ffffff")
        });

        for (let i = 0; i < 12; i++) {
            const shape = shapes[Math.floor(Math.random() * shapes.length)];
            const extrudeSettings = { depth: 0.5, bevelEnabled: true, bevelThickness: 0.1, bevelSize: 0.1 };
            const geometry = new THREE.ExtrudeGeometry(shape, extrudeSettings);

            const mesh = new THREE.Mesh(geometry, glassMaterial);
            stageObject(scene, objects, mesh, 0.4);
        }
    }

    //create bazel
    const bazel = createBazelLogo(glassMaterial);
    stageObject(scene, objects, bazel, 0.4);

    try {
        const backstage = await svgLoader.loadAsync(backstageUrl);
        SvgLogoBuilder.from(backstage, glassMaterialProps)
            .color('#7df3e1')
            .addToScene(scene, objects, 0.001);

        const logo = await svgLoader.loadAsync(logoUrl);
        SvgLogoBuilder.from(logo, glassMaterialProps)
            .color('#1C75F6')
            .radialGradient()
            .addToScene(scene, objects, 0.05);

        const k8s = await svgLoader.loadAsync(k8sUrl);
        SvgLogoBuilder.from(k8s, glassMaterialProps)
            .layerSpacing(20)
            .addToScene(scene, objects, 0.005);

        const docker = await svgLoader.loadAsync(dockerUrl);
        SvgLogoBuilder.from(docker, glassMaterialProps)
            .addToScene(scene, objects, 0.1);

        const aiShield = await svgLoader.loadAsync(aiShieldUrl);
        SvgLogoBuilder.from(aiShield, glassMaterialProps)
            .color('#DC1938')
            .addToScene(scene, objects, 0.05);
    } catch (error) {
        console.error('An error happened loading the SVG:', error);
    }
}

function animate() {
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
