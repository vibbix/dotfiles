import * as THREE from 'three/webgpu';
import { SVGLoader } from 'three/addons/loaders/SVGLoader.js';
import { positionGeometry, vec2, distance, smoothstep, mix, color, clamp, abs } from 'three/tsl';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

// Importing the SVGs lets Bun's HTML bundler copy + content-hash them and
// rewrite these to the final asset URLs. SVGLoader fetches them at runtime.
import backstageUrl from './logos/backstage.svg';
import logoUrl from './logos/logo.svg';
import k8sUrl from './logos/k8s.svg';
import dockerUrl from './logos/docker.svg';
import aiShieldUrl from './logos/logo-ai-shield.svg';

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
        attenuationColor: new THREE.Color(0xffffff)
    });


    if (addExtraShapes) {
        const glassMaterial = new THREE.MeshPhysicalNodeMaterial({
            ...glassMaterialProps,
            attenuationColor: new THREE.Color(0xffffff)
        });

        for (let i = 0; i < 12; i++) {
            const shape = shapes[Math.floor(Math.random() * shapes.length)];
            const extrudeSettings = { depth: 0.5, bevelEnabled: true, bevelThickness: 0.1, bevelSize: 0.1 };
            const geometry = new THREE.ExtrudeGeometry(shape, extrudeSettings);

            const mesh = new THREE.Mesh(geometry, glassMaterial);
            addToScene(mesh, 0.4);
        }
    }
    
    //create bazel
    const bazel = createBazelLogo(glassMaterial);
    addToScene(bazel, 0.4);

    try {
        const data = await svgLoader.loadAsync(backstageUrl);
        const wrapper = createGroupFromSVGData(data, glassMaterialProps, 10, 2, 0.5, new THREE.Color('#7df3e1'));
        addToScene(wrapper, 0.001);

        const logo_2 = await svgLoader.loadAsync(logoUrl);
        const wrapper_2 = createGroupFromSVGData(logo_2, glassMaterialProps, 10, 2, 0.5, new THREE.Color('#1C75F6'), true);
        addToScene(wrapper_2, 0.05);


        const logo_3 = await svgLoader.loadAsync(k8sUrl);
        const wrapper_3 = createGroupFromSVGData(logo_3, glassMaterialProps, 10, 2, 0.5, undefined, false, 20);
        addToScene(wrapper_3, 0.005);


        const logo_4 = await svgLoader.loadAsync(dockerUrl);
        const wrapper_4 = createGroupFromSVGData(logo_4, glassMaterialProps, 10, 2, 0.5, undefined, false);
        addToScene(wrapper_4, 0.1);

        const logo_5 = await svgLoader.loadAsync(aiShieldUrl);
        const wrapper_5 = createGroupFromSVGData(logo_5, glassMaterialProps, 10, 2, 0.5, new THREE.Color('#DC1938'), false);
        addToScene(wrapper_5, 0.05);
    } catch (error) {
        console.error('An error happened loading the SVG:', error);
    }
}

function addToScene(obj: THREE.Object3D, scale: number = 1.0) {
    obj.position.set(
        (Math.random() - 0.5) * 15,
        (Math.random() - 0.5) * 10,
        (Math.random() - 0.5) * 5
    );
    obj.rotation.set(Math.random() * Math.PI, Math.random() * Math.PI, 0);
    obj.scale.set(scale, scale, scale);

    scene.add(obj);
    objects.push(obj);
}

function createGroupFromSVGData(data: any, baseMaterialProps: any, 
    depth = 10, bezelThickness: number = 2, bezelSize: number = 0.5,
    overrideColor?: THREE.Color, applyGradient: boolean = false, newZ: number = 0.05): THREE.Group {
    const paths = data.paths;
    const group = new THREE.Group(); // Put all parts in a group to manage them easily

    let zOffset = 0; // Added this to prevent Z-fighting!

    paths.forEach((path: any) => {
        // Use SVGLoader's createShapes which handles holes properly
        const shapes = SVGLoader.createShapes(path);

        // Get color from the SVG path
        const materialColor = overrideColor || path.color;

        // Create a glass material tinted with the SVG color
        const pathGlassMaterial = new THREE.MeshPhysicalNodeMaterial({
            ...baseMaterialProps,
            color: materialColor,
            attenuationColor: materialColor
        });

        if (applyGradient) {
            // TSL port of the radial-gradient fragment shader. The geometry's
            // local XY are the SVG coordinates; we blend two blues by distance
            // from the gradient center, replicating the SVG's radial stops.
            // (SVGLoader can flip Y, so abs() the Y to stay safe.)
            const center = vec2(15.2407, 18.5482);
            const coords = vec2(positionGeometry.x, abs(positionGeometry.y));
            const dist = distance(coords, center).div(17.8858);
            const stopParam = clamp(smoothstep(0.558071, 1.0, dist), 0.0, 1.0);
            pathGlassMaterial.colorNode = mix(color(0x1c75f6), color(0x1a4ac7), stopParam);
        }

        shapes.forEach((shape) => {
            const geometry = new THREE.ExtrudeGeometry(shape, {
                depth: depth, // Thicker for better glass refraction
                bevelEnabled: true,
                bevelThickness: bezelThickness,
                bevelSize: bezelSize
            });

            const mesh = new THREE.Mesh(geometry, pathGlassMaterial);
            
            // Slightly offset each shape on the Z-axis to prevent 
            // perfectly overlapping meshes from Z-fighting (clipping/glitching)
            mesh.position.z = zOffset;
            zOffset += newZ; // Tiny increment for the next layer

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

    return wrapper;
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

function createBazelLogo(material?: THREE.Material): THREE.Group {
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