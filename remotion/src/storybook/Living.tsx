import { useThree } from "@react-three/fiber";
import { ThreeCanvas } from "@remotion/three";
import React, { useEffect, useMemo, useState } from "react";
import { cancelRender, continueRender, delayRender, staticFile } from "remotion";
import * as THREE from "three";

// A "living painting": the picture on a finely divided plane whose vertices are pushed towards the camera by the
// picture's depth map (reel/depth.py: white near, black far), filmed by a slowly drifting perspective camera. Near
// things slide against far things, so a still painting moves like a shot from an animated film. Without a depth map
// the plane stays flat and the camera move works like a Ken Burns. Everything is a function of the frame.

const W = 1080;
const H = 1920;
const PLANE_H = 2;
const PLANE_W = (PLANE_H * 768) / 1344; // the paintings are 768x1344
const FOV = 30;
const FIT = PLANE_H / 2 / Math.tan(THREE.MathUtils.degToRad(FOV / 2)); // the distance at which the plane fills the frame

const glide = (u: number) => {
  const x = Math.min(1, Math.max(0, u));
  return x * x * x * (x * (6 * x - 15) + 10);
};

// Textures are loaded once per file and kept, so a picture is never reloaded on later frames
const cache = new Map<string, THREE.Texture>();
const load = (src: string) =>
  new Promise<THREE.Texture>((resolve, reject) => {
    const hit = cache.get(src);
    if (hit) return resolve(hit);
    new THREE.TextureLoader().load(
      staticFile(src),
      (t) => {
        t.colorSpace = THREE.NoColorSpace; // the shader writes the painting's own sRGB values straight out
        t.minFilter = THREE.LinearFilter;
        t.generateMipmaps = false;
        cache.set(src, t);
        resolve(t);
      },
      undefined,
      () => reject(new Error(`could not load ${src}`)),
    );
  });

const FLAT = (() => {
  const t = new THREE.DataTexture(new Uint8Array([0, 0, 0, 255]), 1, 1);
  t.needsUpdate = true;
  return t;
})();

const useTextures = (src: string, depth?: string) => {
  const ready = cache.has(src) && (!depth || cache.has(depth));
  const [tex, setTex] = useState<[THREE.Texture, THREE.Texture] | null>(() => (ready ? [cache.get(src)!, depth ? cache.get(depth)! : FLAT] : null));
  const [handle] = useState(() => (ready ? null : delayRender(`painting ${src}`)));
  useEffect(() => {
    if (tex) return;
    Promise.all([load(src), depth ? load(depth) : Promise.resolve(FLAT)])
      .then(([m, d]) => setTex([m, d]))
      .catch((e) => cancelRender(e));
  }, [src, depth, tex]);
  useEffect(() => {
    if (tex && handle !== null) continueRender(handle); // only once React has the textures: never a blank frame
  }, [tex, handle]);
  return tex;
};

const VERTEX = `
uniform sampler2D depthMap;
uniform float strength;
varying vec2 vUv;
void main() {
  vUv = uv;
  float d = texture2D(depthMap, uv).r;
  vec3 p = position + vec3(0.0, 0.0, d * strength);
  gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
}`;
const FRAGMENT = `
uniform sampler2D map;
uniform float glow;
varying vec2 vUv;
void main() {
  vec4 c = texture2D(map, vUv);
  gl_FragColor = vec4(c.rgb * (1.0 + glow), 1.0);
}`;

export type Move = "push" | "pull" | "drift_left" | "drift_right" | "rise";
export const MOVES: Move[] = ["push", "drift_right", "pull", "drift_left", "rise"];

// The camera at progress t (0..1) of a move: always inside the plane's overscan, always looking at its centre
const cameraOf = (move: Move, t: number) => {
  const u = glide(t);
  const near = FIT * 0.86;
  const far = FIT * 0.93;
  switch (move) {
    case "push":
      return { x: -0.03 + 0.06 * u, y: 0.02 * u, z: far - (far - near) * u };
    case "pull":
      return { x: 0.03 - 0.06 * u, y: 0.02 - 0.02 * u, z: near + (far - near) * u };
    case "drift_left":
      return { x: 0.07 - 0.14 * u, y: 0, z: near };
    case "drift_right":
      return { x: -0.07 + 0.14 * u, y: 0, z: near };
    default: // rise: from low to level, a little closer
      return { x: 0, y: -0.07 + 0.09 * u, z: near + 0.05 - 0.05 * u };
  }
};

const Rig: React.FC<{ move: Move; t: number }> = ({ move, t }) => {
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  const c = cameraOf(move, t);
  camera.fov = FOV;
  camera.near = 0.1;
  camera.far = 20;
  camera.position.set(c.x, c.y, c.z);
  camera.lookAt(0, 0, 0.12); // a pivot just in front of the painting: far things swing, near things slide
  camera.updateProjectionMatrix();
  camera.updateMatrixWorld();
  return null;
};

const Painting: React.FC<{ map: THREE.Texture; depth: THREE.Texture; strength: number; glow: number }> = ({ map, depth, strength, glow }) => {
  const geometry = useMemo(() => new THREE.PlaneGeometry(PLANE_W, PLANE_H, 160, 280), []);
  const material = useMemo(
    () => new THREE.ShaderMaterial({ uniforms: { map: { value: map }, depthMap: { value: depth }, strength: { value: strength }, glow: { value: 0 } },
      vertexShader: VERTEX, fragmentShader: FRAGMENT }),
    [map, depth, strength],
  );
  material.uniforms.glow.value = glow;
  return <mesh geometry={geometry} material={material} />;
};

// One living painting, `t` = progress of its camera move (0..1); `glow` brightens it a little (flickering light)
export const LivingPicture: React.FC<{ src: string; depth?: string; move: Move; t: number; glow?: number }> = ({ src, depth, move, t, glow = 0 }) => {
  const tex = useTextures(src, depth);
  if (!tex) return null;
  return (
    <ThreeCanvas width={W} height={H} flat linear style={{ position: "absolute", inset: 0 }} camera={{ fov: FOV, near: 0.1, far: 20 }}>
      <color attach="background" args={["#000000"]} />
      <Rig move={move} t={t} />
      <Painting map={tex[0]} depth={tex[1]} strength={depth ? 0.32 : 0} glow={glow} />
    </ThreeCanvas>
  );
};
