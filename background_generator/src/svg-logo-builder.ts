import * as THREE from 'three/webgpu';
import { SVGLoader } from 'three/addons/loaders/SVGLoader.js';
import { positionGeometry, vec2, distance, smoothstep, mix, color, clamp, abs } from 'three/tsl';

/** Parameters accepted by the glass material the logos are built from. */
export type GlassMaterialProps = NonNullable<
    ConstructorParameters<typeof THREE.MeshPhysicalNodeMaterial>[0]
>;

/** The parsed result handed back by `SVGLoader.loadAsync`. */
export type SvgData = Awaited<ReturnType<SVGLoader['loadAsync']>>;

export interface ExtrudeOptions {
    depth: number;
    bevelThickness: number;
    bevelSize: number;
}

/** Radial gradient applied via a TSL `colorNode`. Defaults match the blue logo. */
export interface RadialGradientOptions {
    inner: THREE.ColorRepresentation;
    outer: THREE.ColorRepresentation;
    center: [number, number];
    radius: number;
    innerStop: number;
}

const DEFAULT_EXTRUDE: ExtrudeOptions = { depth: 10, bevelThickness: 2, bevelSize: 0.5 };
const DEFAULT_GRADIENT: RadialGradientOptions = {
    inner: 0x1c75f6,
    outer: 0x1a4ac7,
    center: [15.2407, 18.5482],
    radius: 17.8858,
    innerStop: 0.558071,
};

/**
 * Random-places `obj`, scales it, and registers it for animation.
 * Shared by the builder and by non-SVG objects (e.g. the Bazel cubes).
 */
export function stageObject(
    scene: THREE.Scene,
    objects: THREE.Object3D[],
    obj: THREE.Object3D,
    scale = 1.0,
): THREE.Object3D {
    obj.position.set(
        (Math.random() - 0.5) * 15,
        (Math.random() - 0.5) * 10,
        (Math.random() - 0.5) * 5,
    );
    obj.rotation.set(Math.random() * Math.PI, Math.random() * Math.PI, 0);
    obj.scale.set(scale, scale, scale);

    scene.add(obj);
    objects.push(obj);
    return obj;
}

/**
 * Fluent builder that turns parsed SVG data into an extruded, glass-material
 * `THREE.Group`. Replaces the old `createGroupFromSVGData` positional overloads
 * with chainable, intent-named options. Terminate the chain with `addToScene`.
 *
 * @example
 * SvgLogoBuilder.from(data, glassMaterialProps)
 *     .color('#1C75F6')
 *     .radialGradient()
 *     .addToScene(scene, objects, 0.05);
 */
export class SvgLogoBuilder {
    private overrideColor?: THREE.Color;
    private gradient?: RadialGradientOptions;
    private extrudeOpts: ExtrudeOptions = { ...DEFAULT_EXTRUDE };
    private layerSpacingZ = 0.05;

    constructor(
        private readonly data: SvgData,
        private readonly baseMaterialProps: GlassMaterialProps,
    ) {}

    static from(data: SvgData, baseMaterialProps: GlassMaterialProps): SvgLogoBuilder {
        return new SvgLogoBuilder(data, baseMaterialProps);
    }

    /** Tint every path with this color instead of the SVG's own path colors. */
    color(c: THREE.ColorRepresentation): this {
        this.overrideColor = new THREE.Color(c);
        return this;
    }

    /** Apply a radial gradient (TSL `colorNode`). Defaults to the blue logo's. */
    radialGradient(options: Partial<RadialGradientOptions> = {}): this {
        this.gradient = { ...DEFAULT_GRADIENT, ...options };
        return this;
    }

    /** Override extrude depth / bevel (defaults: depth 10, bevel 2 / 0.5). */
    extrude(options: Partial<ExtrudeOptions>): this {
        this.extrudeOpts = { ...this.extrudeOpts, ...options };
        return this;
    }

    /** Z gap between stacked path layers, used to avoid z-fighting. */
    layerSpacing(z: number): this {
        this.layerSpacingZ = z;
        return this;
    }

    /** Build the centered, wrapped group without adding it to a scene. */
    build(): THREE.Group {
        const group = new THREE.Group();
        let zOffset = 0;

        for (const path of this.data.paths) {
            // createShapes handles holes (e.g. the inside of an "o") properly.
            const shapes = SVGLoader.createShapes(path);
            const materialColor = this.overrideColor ?? path.color;

            const material = new THREE.MeshPhysicalNodeMaterial({
                ...this.baseMaterialProps,
                color: materialColor,
                attenuationColor: materialColor,
            });

            if (this.gradient) {
                const [cx, cy] = this.gradient.center;
                // Geometry-local XY are the SVG coordinates; blend two colors by
                // distance from the gradient center. SVGLoader can flip Y, so abs() it.
                const coords = vec2(positionGeometry.x, abs(positionGeometry.y));
                const dist = distance(coords, vec2(cx, cy)).div(this.gradient.radius);
                const stop = clamp(smoothstep(this.gradient.innerStop, 1.0, dist), 0.0, 1.0);
                const inner = color(new THREE.Color(this.gradient.inner));
                const outer = color(new THREE.Color(this.gradient.outer));
                material.colorNode = mix(inner, outer, stop);
            }

            for (const shape of shapes) {
                const geometry = new THREE.ExtrudeGeometry(shape, {
                    depth: this.extrudeOpts.depth,
                    bevelEnabled: true,
                    bevelThickness: this.extrudeOpts.bevelThickness,
                    bevelSize: this.extrudeOpts.bevelSize,
                });

                const mesh = new THREE.Mesh(geometry, material);
                // Offset each layer on Z so coincident faces don't z-fight.
                mesh.position.z = zOffset;
                zOffset += this.layerSpacingZ;
                group.add(mesh);
            }
        }

        // Center the combined SVG around the origin...
        const box = new THREE.Box3().setFromObject(group);
        const center = new THREE.Vector3();
        box.getCenter(center);
        group.position.sub(center);

        // ...then wrap it so rotation/scaling don't disturb that centering.
        const wrapper = new THREE.Group();
        wrapper.add(group);
        return wrapper;
    }

    /** Terminal: build, stage in the scene, and register for animation. */
    addToScene(scene: THREE.Scene, objects: THREE.Object3D[], scale = 1.0): THREE.Group {
        const wrapper = this.build();
        stageObject(scene, objects, wrapper, scale);
        return wrapper;
    }
}
