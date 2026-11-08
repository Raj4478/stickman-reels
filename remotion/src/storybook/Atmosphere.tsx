import React from "react";
import { AbsoluteFill, random } from "remotion";

// Moving atmosphere over a living painting (reel/storybook.py FX): embers and flickering lamp glow, marigold petals,
// dust in a light beam, rain, drifting mist and twinkling sparkles. Everything is seeded per line and a function of
// the frame, so every render of a Reel is the same.

const W = 1080;
const H = 1920;
const r = (seed: string) => random(seed);

const Embers: React.FC<{ f: number; seed: string }> = ({ f, seed }) => (
  <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>
    <defs>
      <radialGradient id={`${seed}-ember`}>
        <stop offset="0" stopColor="#fff3b0" />
        <stop offset="0.4" stopColor="#ffb347" stopOpacity={0.9} />
        <stop offset="1" stopColor="#ff7a00" stopOpacity={0} />
      </radialGradient>
    </defs>
    {Array.from({ length: 26 }, (_, k) => {
      const life = 90 + r(`${seed}e${k}l`) * 90;
      const age = (f + r(`${seed}e${k}t`) * life) % life;
      const x = r(`${seed}e${k}x`) * W + Math.sin((f + k * 13) * 0.05) * 30;
      const y = H * (0.55 + r(`${seed}e${k}y`) * 0.45) - age * (2.2 + r(`${seed}e${k}v`) * 2);
      const size = 4 + r(`${seed}e${k}s`) * 8;
      const o = Math.sin((age / life) * Math.PI) * (0.6 + 0.4 * Math.sin(f * 0.6 + k));
      return <circle key={k} cx={x} cy={y} r={size * 2.4} fill={`url(#${seed}-ember)`} opacity={o} />;
    })}
  </svg>
);

const PETAL = "M0,-14 C9,-12 12,-2 0,14 C-12,-2 -9,-12 0,-14 Z";
const Petals: React.FC<{ f: number; seed: string }> = ({ f, seed }) => (
  <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>
    {Array.from({ length: 22 }, (_, k) => {
      const speed = 2.2 + r(`${seed}p${k}v`) * 2.4;
      const y = ((r(`${seed}p${k}y`) * (H + 200) + f * speed) % (H + 200)) - 100;
      const x = r(`${seed}p${k}x`) * W + Math.sin((f + k * 20) * 0.04) * 60;
      const turn = (f * (2 + r(`${seed}p${k}r`) * 4) + k * 40) % 360;
      const color = ["#ff9f1c", "#ffbf00", "#ff6b35", "#ffd23f"][k % 4];
      const s = 0.8 + r(`${seed}p${k}s`) * 0.9;
      return <path key={k} d={PETAL} fill={color} opacity={0.9} transform={`translate(${x} ${y}) rotate(${turn}) scale(${s} ${s * (0.6 + 0.4 * Math.abs(Math.sin((f + k) * 0.1)))})`} />;
    })}
  </svg>
);

const Dust: React.FC<{ f: number; seed: string }> = ({ f, seed }) => (
  <svg width={W} height={H} style={{ position: "absolute", inset: 0, mixBlendMode: "screen" }}>
    <polygon points={`${W * 0.15},0 ${W * 0.45},0 ${W * 0.95},${H} ${W * 0.35},${H}`} fill="#fff1c2" opacity={0.07 + 0.02 * Math.sin(f * 0.05)} />
    {Array.from({ length: 40 }, (_, k) => {
      const x = (r(`${seed}d${k}x`) * W + f * (0.3 + r(`${seed}d${k}v`) * 0.6) + Math.sin((f + k * 9) * 0.03) * 20) % W;
      const y = (r(`${seed}d${k}y`) * H - f * (0.2 + r(`${seed}d${k}u`) * 0.4) + H) % H;
      return <circle key={k} cx={x} cy={y} r={1.5 + r(`${seed}d${k}s`) * 3} fill="#fff8dc" opacity={0.25 + 0.45 * Math.abs(Math.sin(f * 0.07 + k))} />;
    })}
  </svg>
);

const Rain: React.FC<{ f: number; seed: string }> = ({ f, seed }) => (
  <AbsoluteFill style={{ background: "rgba(20,30,50,.12)" }}>
    <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>
      {Array.from({ length: 90 }, (_, k) => {
        const speed = 38 + r(`${seed}r${k}v`) * 24;
        const y = ((r(`${seed}r${k}y`) * (H + 300) + f * speed) % (H + 300)) - 150;
        const x = (r(`${seed}r${k}x`) * (W + 200) - y * 0.12) % (W + 200);
        return <line key={k} x1={x} y1={y} x2={x - 9} y2={y + 70} stroke="#dbe9ff" strokeWidth={2.4} strokeLinecap="round" opacity={0.35 + r(`${seed}r${k}o`) * 0.3} />;
      })}
    </svg>
  </AbsoluteFill>
);

const Smoke: React.FC<{ f: number; seed: string }> = ({ f, seed }) => (
  <AbsoluteFill style={{ filter: "blur(28px)" }}>
    <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>
      {Array.from({ length: 9 }, (_, k) => {
        const x = ((r(`${seed}m${k}x`) * (W + 600) + f * (0.6 + r(`${seed}m${k}v`))) % (W + 600)) - 300;
        const y = H * (0.45 + r(`${seed}m${k}y`) * 0.5) + Math.sin((f + k * 30) * 0.02) * 30;
        return <ellipse key={k} cx={x} cy={y} rx={260 + r(`${seed}m${k}w`) * 220} ry={90 + r(`${seed}m${k}h`) * 70} fill="#f3eee6" opacity={0.16} />;
      })}
    </svg>
  </AbsoluteFill>
);

const STAR = "M0,-18 L4,-4 L18,0 L4,4 L0,18 L-4,4 L-18,0 L-4,-4 Z";
const Sparkles: React.FC<{ f: number; seed: string }> = ({ f, seed }) => (
  <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>
    {Array.from({ length: 18 }, (_, k) => {
      const period = 40 + r(`${seed}s${k}p`) * 40;
      const phase = ((f + r(`${seed}s${k}t`) * period) % period) / period;
      const o = Math.sin(phase * Math.PI);
      const x = 80 + r(`${seed}s${k}x`) * (W - 160);
      const y = 420 + r(`${seed}s${k}y`) * 900;
      const s = (0.5 + r(`${seed}s${k}s`) * 1.1) * o;
      return <path key={k} d={STAR} fill="#fffbe6" opacity={o * 0.9} transform={`translate(${x} ${y}) rotate(${f * 1.5}) scale(${s})`} />;
    })}
  </svg>
);

// The glow a line's light gives the painting (a gentle flicker for embers, nothing otherwise)
export const glowOf = (fx: string | undefined, f: number, seed: string) =>
  fx === "embers" ? 0.05 * Math.sin(f * 0.31) + 0.03 * Math.sin(f * 0.87 + r(seed) * 6) : 0;

export const Atmosphere: React.FC<{ fx?: string; f: number; seed: string }> = ({ fx, f, seed }) => {
  switch (fx) {
    case "embers":
      return <Embers f={f} seed={seed} />;
    case "petals":
      return <Petals f={f} seed={seed} />;
    case "dust":
      return <Dust f={f} seed={seed} />;
    case "rain":
      return <Rain f={f} seed={seed} />;
    case "smoke":
      return <Smoke f={f} seed={seed} />;
    case "sparkles":
      return <Sparkles f={f} seed={seed} />;
    default:
      return null;
  }
};
