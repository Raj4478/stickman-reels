// The 2.5D engine (REEL_ENGINE=three): a toon-shaded three.js room and a real perspective camera behind the
// SVG kid, after Mr Omi's "2D characters in a 3D world" (github.com/mromidev/claude-animated-shorts, MIT; ideas
// re-implemented, see THIRD_PARTY.md). Everything is a function of the frame: no frame callbacks, timers or unseeded random numbers.
import * as THREE from "three";
import { Easing, interpolate } from "remotion";
import type { Segment } from "../StickReel";

// World units are metres. The SVG kid layer (1080x1920 stage pixels) stands at z = 0, facing +z, with stage pixel
// (540, 960) at world (0, 1.2, 0) and U metres per stage pixel: the kid's head (464 px wide) is about 0.7 m.
export type V3 = [number, number, number];
export type Cam3 = { pos: V3; look: V3; fov: number; roll: number };
export const W = 1080;
export const H = 1920;
export const U = 0.0015;
export const stageToWorld = (px: number, py: number): V3 => [(px - 540) * U, 1.2 + (960 - py) * U, 0];

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
// Look points and distances match the SVG engine's framings (ComicReel.tsx MEDIUM, CLOSE, XCLOSE): the kid's
// scale on screen is (H / 2) * U / (d * tan(fov / 2)) for a camera d metres away, so a level medium shot at 3.8 m with
// a 38 degree lens shows the kid at ~1.1x, like the SVG medium, with the title strip clear above the head.
const MID = stageToWorld(540, 950);
const FACE = stageToWorld(540, 905);
const EYES = stageToWorld(540, 830);
const c3 = (pos: V3, look: V3, fov = 36, roll = 0): Cam3 => ({ pos, look, fov, roll });

// Every shot creeps from `from` to `to` across its length (Mr Omi: holds always creep in)
export const SHOTS3: Record<string, { from: Cam3; to: Cam3 }> = {
  wide: { from: c3([0, MID[1], 4.2], MID, 40), to: c3([0, MID[1], 3.95], MID, 40) },
  medium: { from: c3([0, MID[1], 3.9], MID, 38), to: c3([0, MID[1], 3.65], MID, 38) },
  close: { from: c3([0.1, FACE[1], 2.95], FACE), to: c3([0.1, FACE[1], 2.75], FACE) },
  xclose: { from: c3([0, EYES[1], 2.25], EYES, 34), to: c3([0, EYES[1], 2.1], EYES, 34) },
  three_q_l: { from: c3([-1.65, FACE[1], 2.4], FACE), to: c3([-1.5, FACE[1], 2.25], FACE) },
  three_q_r: { from: c3([1.65, FACE[1], 2.4], FACE), to: c3([1.5, FACE[1], 2.25], FACE) },
  low_hero: { from: c3([0, 0.75, 3.0], FACE, 40), to: c3([0, 0.7, 2.8], FACE, 40) }, // smug, proud, dance: looks big
  high_pity: { from: c3([0, 2.4, 3.3], MID, 38), to: c3([0, 2.5, 3.45], MID, 38) }, // sad, cry: looks small
  dutch: { from: c3([0.3, FACE[1], 2.9], FACE, 36, -7), to: c3([0.3, FACE[1], 2.75], FACE, 36, -9) }, // panic, angry
};

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const mixCam = (a: Cam3, b: Cam3, t: number): Cam3 => ({
  pos: a.pos.map((v, k) => lerp(v, b.pos[k], t)) as V3,
  look: a.look.map((v, k) => lerp(v, b.look[k], t)) as V3,
  fov: lerp(a.fov, b.fov, t),
  roll: lerp(a.roll, b.roll, t),
});
export const glide = (u: number) => {
  const x = Math.min(1, Math.max(0, u));
  return x * x * x * (x * (6 * x - 15) + 10); // smootherstep: Mr Omi's camera ease
};

// "Vertigo" dolly zoom for a shock: the lens widens while the camera moves in, so the kid keeps its size and the
// room stretches behind it. d = h / (2 tan(fov / 2)) keeps h metres in frame.
export const dollyZoom = (t: number, fov0 = 28, fov1 = 62, h = 1.8): Cam3 => {
  // h = 1.8 m in frame keeps the kid at about the SVG close-up size (1920 px * U / 1.8 m = 1.6x)
  const fov = lerp(fov0, fov1, t);
  const d = h / (2 * Math.tan(THREE.MathUtils.degToRad(fov / 2)));
  return c3([0, FACE[1], d], FACE, fov);
};

// Which shot a line opens on (the same ideas as shotOf in ComicReel.tsx, with real angles)
export const shot3Of = (seg: Segment, i: number): string => {
  const face = seg.face ?? "deadpan";
  if (seg.kind === "hook") return "medium";
  if (seg.kind === "ask") return "medium";
  if (seg.visual === "person") return "medium";
  if (["side_eye", "eye_roll", "cheeky", "sneaky"].includes(face)) return "xclose";
  if (["smug", "proud"].includes(face) || seg.gesture === "dance") return "low_hero";
  if (["sad", "cry"].includes(face)) return "high_pity";
  if (["angry", "panic"].includes(face) || seg.gesture === "panic") return "dutch";
  if (seg.speaker === "other") return "three_q_r";
  return i % 2 ? "close" : "three_q_l";
};

const ANGLES3 = ["close", "three_q_l", "xclose", "wide", "three_q_r", "medium"];
const dist = (c: Cam3) => Math.hypot(c.pos[0] - c.look[0], c.pos[1] - c.look[1], c.pos[2] - c.look[2]);
const yaw = (c: Cam3) => (Math.atan2(c.pos[0] - c.look[0], c.pos[2] - c.look[2]) * 180) / Math.PI;
// Rule C1 in 3D: a cut changes the distance by 40% or swings the camera 20 degrees
const bigChange3 = (a: Cam3, b: Cam3) => Math.max(dist(a) / dist(b), dist(b) / dist(a)) >= 1.4 || Math.abs(yaw(a) - yaw(b)) >= 20;

// The camera of line i at frame f of shot `part` (0 = the line's first shot); `twist` = the punchline's twist frame
export const camAt3 = (seg: Segment, i: number, f: number, dur: number, part = 0, twist = 0): Cam3 => {
  if (seg.kind === "lesson") {
    const t = interpolate(f, [twist, twist + 4], [0, 1], { ...clamp, easing: Easing.out(Easing.back(1.6)) });
    return mixCam(SHOTS3.close.to, SHOTS3.xclose.to, t);
  }
  if (part === 0 && seg.kind === "scene" && seg.face === "shock") return dollyZoom(glide(f / 12));
  let name = shot3Of(seg, i);
  for (let p = 1; p <= part; p++) {
    const prev = SHOTS3[name].to;
    for (let k = 0; k < ANGLES3.length; k++) {
      const next = ANGLES3[(i + p * 2 + k) % ANGLES3.length];
      if (bigChange3(prev, SHOTS3[next].from)) {
        name = next;
        break;
      }
    }
  }
  const s = SHOTS3[name];
  return mixCam(s.from, s.to, glide(f / Math.max(1, dur)));
};

export const makeCamera = (c: Cam3) => {
  const cam = new THREE.PerspectiveCamera(c.fov, W / H, 0.05, 200);
  cam.position.set(...c.pos);
  cam.lookAt(...c.look);
  cam.rotateZ(THREE.MathUtils.degToRad(c.roll));
  cam.updateMatrixWorld();
  cam.updateProjectionMatrix();
  return cam;
};

// Where the SVG kid layer goes on screen, as a billboard anchored at stage point (540, 960): project the anchor
// through the same camera as the room, and scale by the camera's pixels-per-metre at that depth
export const billboard = (c: Cam3) => {
  const cam = makeCamera(c);
  const anchor = new THREE.Vector3(...stageToWorld(540, 960));
  const ndc = anchor.clone().project(cam);
  const depth = -anchor.clone().applyMatrix4(cam.matrixWorldInverse).z; // metres in front of the lens
  const pxPerM = H / 2 / (depth * Math.tan(THREE.MathUtils.degToRad(c.fov / 2)));
  return { x: ((ndc.x + 1) / 2) * W, y: ((1 - ndc.y) / 2) * H, scale: pxPerM * U, roll: -c.roll, depth: dist(c) };
};
export const billboardCss = (b: ReturnType<typeof billboard>) =>
  `translate(${b.x}px, ${b.y}px) rotate(${b.roll}deg) scale(${b.scale}) translate(-540px, -960px)`;
