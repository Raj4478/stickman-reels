import { Easing, interpolate } from "remotion";

// The camera director: every beat is filmed with a named shot (picked by the director pass in reel/script.py).
// A camera looks at a world point (x, y) placed at the screen ANCHOR, zoomed by z, rolled by r degrees and
// tilted in 3D by tilt degrees (low/high angle). Each shot animates from `from` to `to` across the beat.

export type Cam = { x: number; y: number; z: number; r: number; tilt: number };
export const ANCHOR = { x: 540, y: 1060 };

// world points the shots frame (the hero stands at x 540, hip at 1097, head at about 866)
const BODY = { x: 540, y: 1060 };
const FACE = { x: 540, y: 880 };
const FEET = { x: 540, y: 1220 };

const cam = (p: { x: number; y: number }, z: number, r = 0, tilt = 0): Cam => ({ ...p, z, r, tilt });

export const SHOTS: Record<string, { from: Cam; to: Cam; ease?: (t: number) => number }> = {
  wide: { from: cam({ x: 540, y: 1000 }, 0.82), to: cam({ x: 540, y: 1000 }, 0.86) },
  medium: { from: cam(BODY, 1.0), to: cam(BODY, 1.05) },
  close: { from: cam({ x: 540, y: 930 }, 1.6), to: cam({ x: 540, y: 925 }, 1.68) },
  extreme_close: { from: cam(FACE, 2.3), to: cam(FACE, 2.5) },
  low_angle: { from: cam(FEET, 1.15, 0, 16), to: cam(FEET, 1.22, 0, 18) },
  high_angle: { from: cam({ x: 540, y: 1000 }, 0.95, 0, -16), to: cam({ x: 540, y: 1010 }, 0.9, 0, -18) },
  dutch: { from: cam(BODY, 1.15, -9), to: cam(BODY, 1.2, -11) },
  push_in: { from: cam(BODY, 1.0), to: cam(FACE, 1.9), ease: Easing.inOut(Easing.cubic) },
  pull_out: { from: cam(FACE, 1.9), to: cam({ x: 540, y: 1000 }, 0.85), ease: Easing.inOut(Easing.cubic) },
  pan: { from: cam({ x: 400, y: 1040 }, 1.1), to: cam({ x: 690, y: 1040 }, 1.1), ease: (t) => t },
  two_shot: { from: cam({ x: 540, y: 1040 }, 0.92), to: cam({ x: 540, y: 1030 }, 0.97) },
};

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

// handheld drift: tiny continuous motion so no shot ever feels frozen
const drift = (f: number) => ({ x: Math.sin(f * 0.031) * 5 + Math.sin(f * 0.077) * 2, y: Math.cos(f * 0.027) * 4, r: Math.sin(f * 0.019) * 0.35 });

export const cameraAt = (shot: string, f: number, dur: number, hits: number[] = []): Cam => {
  const s = SHOTS[shot] ?? SHOTS.medium;
  const t = (s.ease ?? Easing.inOut(Easing.quad))(interpolate(f, [0, Math.max(1, dur)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  const d = drift(f);
  // impact punch-in: the camera jumps closer on a hit and settles back
  const punch = hits.reduce((acc, h) => (f >= h && f < h + 10 ? acc + 0.07 * (1 - (f - h) / 10) ** 2 : acc), 0);
  return {
    x: lerp(s.from.x, s.to.x, t) + d.x,
    y: lerp(s.from.y, s.to.y, t) + d.y,
    z: lerp(s.from.z, s.to.z, t) * (1 + punch),
    r: lerp(s.from.r, s.to.r, t) + d.r,
    tilt: lerp(s.from.tilt, s.to.tilt, t),
  };
};

// CSS transform for one layer. depth < 1 moves less (far background), so layers separate as the camera moves.
export const layerTransform = (c: Cam, depth = 1, shake = { x: 0, y: 0, r: 0 }) => {
  const z = 1 + (c.z - 1) * depth;
  const x = ANCHOR.x + (c.x - ANCHOR.x) * depth;
  const y = ANCHOR.y + (c.y - ANCHOR.y) * depth;
  return `translate(${shake.x}px, ${shake.y}px) translate(${ANCHOR.x}px, ${ANCHOR.y}px) rotate(${c.r * depth + shake.r}deg) scale(${z}) translate(${-x}px, ${-y}px)`;
};

// 3D tilt for low/high angles, applied once to the whole stage
export const tiltTransform = (c: Cam) => (Math.abs(c.tilt) < 0.1 ? "none" : `perspective(1500px) rotateX(${c.tilt}deg)`);

// How the beat enters: whip pan, zoom, flash or a plain cut. Returns offsets for the first frames.
export const entrance = (kind: string | undefined, f: number) => {
  const k = interpolate(f, [0, 9], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  switch (kind) {
    case "whip":
      return { x: k * 900, z: 1, blur: k * 26, flash: 0 };
    case "zoom":
      return { x: 0, z: 1 + k * 1.4, blur: k * 14, flash: 0 };
    case "flash":
      return { x: 0, z: 1 + k * 0.15, blur: 0, flash: interpolate(f, [0, 7], [1, 0], { extrapolateRight: "clamp" }) };
    default:
      return { x: 0, z: 1, blur: 0, flash: 0 };
  }
};
