// Adapted from nispa/stickman-video (MIT, (c) 2026 nispa): https://github.com/nispa/stickman-video
// See THIRD_PARTY.md. Kept: palette, easing, camera shake, impact burst, dust, speed lines, cursor.
// Changed: fonts are the Reel's own (Hindi-capable Poppins), and the effects fit a 1080x1920 stage.
import React from "react";
import { Easing, interpolate, random } from "remotion";

export const FONT = { hindi: "Poppins, 'Noto Sans Devanagari', sans-serif" };

export const COL = {
  paper: "#fafaf7",
  ink: "#1a1a1a",
  orange: "#f7941d",
  blue: "#2b7de9",
  green: "#2fa84f",
  red: "#e5322d",
  yellow: "#f2c12e",
  purple: "#8e44ad",
  grey: "#8a8a8a",
  gold: "#f2b705",
};

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

export const ease = (f: number, a: number, b: number, from = 0, to = 1, e = Easing.bezier(0.2, 0.9, 0.25, 1)) =>
  interpolate(f, [a, b], [from, to], { ...clamp, easing: e });

// camera shake: decays after each hit
// impact kick: flips sign every frame and dies out over 7 frames (reads as a hit, not an earthquake)
export const kickAt = (f: number, hits: number[], gain = 12) =>
  hits.reduce((a, t0) => {
    const n = f - t0;
    return n >= 0 && n < 7 ? a + gain * (n % 2 ? -1 : 1) * (1 - n / 7) ** 1.5 : a;
  }, 0);

export const shakeAt = (f: number, hits: number[], power = 18, len = 12) => {
  let x = 0,
    y = 0,
    r = 0;
  for (const h of hits) {
    const d = f - h;
    if (d >= 0 && d < len) {
      const k = (1 - d / len) ** 2 * power;
      x += (random(`sx${h}-${d}`) - 0.5) * 2 * k;
      y += (random(`sy${h}-${d}`) - 0.5) * 2 * k;
      r += (random(`sr${h}-${d}`) - 0.5) * k * 0.08;
    }
  }
  return { x, y, r };
};

// comic-style impact starburst
export const Burst: React.FC<{ x: number; y: number; at: number; f: number; color?: string; size?: number; n?: number }> = ({
  x,
  y,
  at,
  f,
  color = COL.ink,
  size = 160,
  n = 14,
}) => {
  const d = f - at;
  if (d < 0 || d > 14) return null;
  const t = d / 14;
  const r0 = size * (0.25 + t * 0.9);
  const r1 = size * (0.45 + t * 1.25);
  return (
    <g opacity={1 - t}>
      {d < 3 && <circle cx={x} cy={y} r={size * 0.55} fill="#fff" stroke={color} strokeWidth={8} />}
      {Array.from({ length: n }).map((_, i) => {
        const a = (i / n) * Math.PI * 2 + random(`b${at}${i}`) * 0.3;
        const k = 0.7 + random(`bl${at}${i}`) * 0.6;
        return (
          <line
            key={i}
            x1={x + Math.cos(a) * r0}
            y1={y + Math.sin(a) * r0}
            x2={x + Math.cos(a) * r1 * k}
            y2={y + Math.sin(a) * r1 * k}
            stroke={color}
            strokeWidth={10 * (1 - t) + 2}
            strokeLinecap="round"
          />
        );
      })}
    </g>
  );
};

// dust puffs when something lands
export const Dust: React.FC<{ x: number; y: number; at: number; f: number; spread?: number }> = ({ x, y, at, f, spread = 160 }) => {
  const d = f - at;
  if (d < 0 || d > 22) return null;
  const t = d / 22;
  return (
    <g opacity={1 - t}>
      {Array.from({ length: 8 }).map((_, i) => {
        const side = i % 2 === 0 ? 1 : -1;
        const k = 0.4 + random(`d${at}${i}`) * 0.8;
        return (
          <circle
            key={i}
            cx={x + side * spread * k * Math.sqrt(t)}
            cy={y - 30 * k * t - 6}
            r={(12 + 22 * k) * (0.6 + t)}
            fill="none"
            stroke="#b9b5aa"
            strokeWidth={6}
          />
        );
      })}
    </g>
  );
};

// horizontal speed lines across the stage band
export const SpeedLines: React.FC<{ f: number; top: number; bottom: number; dir?: number; color?: string }> = ({
  f,
  top,
  bottom,
  dir = -1,
  color = "#d8d4c8",
}) => (
  <g>
    {Array.from({ length: 14 }).map((_, i) => {
      const y = top + random(`sl${i}`) * (bottom - top);
      const len = 120 + random(`sll${i}`) * 320;
      const x = (((random(`slx${i}`) * 1600 + f * 70 * dir) % 1600) + 1600) % 1600 - 260;
      return <line key={i} x1={x} y1={y} x2={x + len} y2={y} stroke={color} strokeWidth={5 + random(`slw${i}`) * 6} strokeLinecap="round" />;
    })}
  </g>
);

// the animator's pencil cursor, used while the hero is drawn in the opening
export const Cursor: React.FC<{ x: number; y: number; scale?: number }> = ({ x, y, scale = 2.4 }) => (
  <g transform={`translate(${x} ${y}) scale(${scale})`}>
    <path d="M0,0 L0,34 L8,26 L14,40 L20,37 L14,24 L25,24 Z" fill="#fff" stroke="#000" strokeWidth={2.4} strokeLinejoin="round" />
  </g>
);
