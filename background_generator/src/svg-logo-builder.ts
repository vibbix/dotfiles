import * as THREE from 'three/webgpu';
import { SVGLoader } from 'three/addons/loaders/SVGLoader.js';
import { positionGeometry, vec2, vec3, distance, smoothstep, mix, color, clamp, abs, atan, fract } from 'three/tsl';

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

/**
 * Angular (conic) gradient applied via a TSL `colorNode`. `colors`/`stops` are
 * parallel arrays (positions in [0,1]); `from` is the start angle in radians.
 * Defaults match logo-ai.svg's shield: a two-red sweep around the center.
 */
export interface AngularGradientOptions {
    colors: THREE.ColorRepresentation[];
    stops: number[];
    center: [number, number];
    from: number;
}

const DEFAULT_EXTRUDE: ExtrudeOptions = { depth: 10, bevelThickness: 2, bevelSize: 0.5 };
const DEFAULT_GRADIENT: RadialGradientOptions = {
    inner: "#1c75f6",
    outer: "#1a4ac7",
    center: [15.2407, 18.5482],
    radius: 17.8858,
    innerStop: 0.558071,
};
// Ported from logo-ai.svg's `data-figma-gradient-fill` (GRADIENT_ANGULAR):
// conic-gradient(from 90deg, #DC1938 0deg, #EA6378 200.905deg, #DC1938 360deg).
const DEFAULT_ANGULAR_GRADIENT: AngularGradientOptions = {
    colors: ["#dc1938", "#ea6378", "#dc1938"],
    stops: [0, 0.558071, 1],
    center: [14.7222, 18.129],
    from: Math.PI / 2,
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
    private radial?: RadialGradientOptions;
    private angular?: AngularGradientOptions;
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
        this.radial = { ...DEFAULT_GRADIENT, ...options };
        this.angular = undefined;
        return this;
    }

    /** Apply an angular/conic gradient. Defaults to logo-ai.svg's shield sweep. */
    angularGradient(options: Partial<AngularGradientOptions> = {}): this {
        this.angular = { ...DEFAULT_ANGULAR_GRADIENT, ...options };
        this.radial = undefined;
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

        // The gradient colorNode (if any) is position-based, so one shared
        // node graph works for every path's material.
        const colorNode = this.gradientColorNode();

        for (const path of this.data.paths) {
            // createShapes handles holes (e.g. the inside of an "o") properly.
            const shapes = SVGLoader.createShapes(path);
            const materialColor = this.overrideColor ?? path.color;

            const material = new THREE.MeshPhysicalNodeMaterial({
                ...this.baseMaterialProps,
                color: materialColor,
                attenuationColor: materialColor,
            });

            if (colorNode) material.colorNode = colorNode;

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

    /** Builds the TSL `colorNode` for the configured gradient, or undefined. */
    private gradientColorNode() {
        if (this.radial) {
            const g = this.radial;
            const [cx, cy] = g.center;
            // Geometry-local XY are the SVG coordinates; blend two colors by
            // distance from the gradient center. SVGLoader can flip Y, so abs() it.
            const coords = vec2(positionGeometry.x, abs(positionGeometry.y));
            const dist = distance(coords, vec2(cx, cy)).div(g.radius);
            const stop = clamp(smoothstep(g.innerStop, 1.0, dist), 0.0, 1.0);
            return mix(color(new THREE.Color(g.inner)), color(new THREE.Color(g.outer)), stop);
        }

        if (this.angular) {
            const g = this.angular;
            const [cx, cy] = g.center;
            // Undo SVGLoader's Y flip so the sweep matches SVG orientation, take
            // the angle around the center, and normalize it to [0,1) from `from`.
            const coords = vec2(positionGeometry.x, positionGeometry.y.mul(-1));
            const d = coords.sub(vec2(cx, cy));
            const t = fract(atan(d.y, d.x).sub(g.from).div(Math.PI * 2));

            // Piecewise-linear ramp across the parallel (colors, stops) arrays.
            let ramp = vec3(color(new THREE.Color(g.colors[0])));
            for (let i = 1; i < g.colors.length; i++) {
                const seg = clamp(t.sub(g.stops[i - 1]!).div(g.stops[i]! - g.stops[i - 1]!), 0.0, 1.0);
                ramp = mix(ramp, color(new THREE.Color(g.colors[i])), seg);
            }
            return ramp;
        }

        return undefined;
    }

    /** Terminal: build, stage in the scene, and register for animation. */
    addToScene(scene: THREE.Scene, objects: THREE.Object3D[], scale = 1.0): THREE.Group {
        const wrapper = this.build();
        stageObject(scene, objects, wrapper, scale);
        return wrapper;
    }
}
