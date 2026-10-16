// Flat, ink-outlined props in the style of nispa/stickman-video (MIT, see THIRD_PARTY.md); Box and Coin
// are adapted from it, the rest are new for life-lesson stories. All are centred on (0,0): place with <At>.
import React from "react";
import { interpolate, random } from "remotion";
import { COL, FONT } from "./fx";

export const At: React.FC<{ x: number; y: number; s?: number; r?: number; o?: number; children: React.ReactNode }> = ({
  x,
  y,
  s = 1,
  r = 0,
  o = 1,
  children,
}) => (
  <g transform={`translate(${x} ${y}) rotate(${r}) scale(${s})`} opacity={o}>
    {children}
  </g>
);

const K = { stroke: COL.ink, strokeWidth: 6, strokeLinejoin: "round" as const, strokeLinecap: "round" as const };

export const Box: React.FC<{ label?: string; color?: string; w?: number; h?: number }> = ({ label, color = "#d9a066", w = 96, h = 84 }) => (
  <g>
    <rect x={-w / 2} y={-h / 2} width={w} height={h} rx={4} fill={color} {...K} />
    <line x1={-w / 2} y1={-h / 6} x2={w / 2} y2={-h / 6} stroke={COL.ink} strokeWidth={4} />
    {label && (
      <text y={h * 0.3} textAnchor="middle" fontFamily={FONT.hindi} fontWeight={800} fontSize={h * 0.34} fill={COL.ink}>
        {label}
      </text>
    )}
  </g>
);

export const Coin: React.FC<{ f: number; r?: number }> = ({ f, r = 60 }) => (
  <g transform={`scale(${Math.cos(f * 0.12) * 0.25 + 0.75} 1)`}>
    <circle r={r} fill={COL.gold} {...K} />
    <circle r={r * 0.78} fill="none" stroke="rgba(0,0,0,0.25)" strokeWidth={4} />
    <text y={r * 0.33} textAnchor="middle" fontFamily={FONT.hindi} fontWeight={800} fontSize={r * 0.95} fill={COL.ink}>
      ₹
    </text>
  </g>
);

export const Clock: React.FC<{ f: number; r?: number }> = ({ f, r = 70 }) => {
  const m = f * 6; // the minute hand races: time slipping away
  const h = f * 0.5;
  const hand = (a: number, len: number, w: number) => (
    <line x1={0} y1={0} x2={Math.sin((a * Math.PI) / 180) * len} y2={-Math.cos((a * Math.PI) / 180) * len} stroke={COL.ink} strokeWidth={w} strokeLinecap="round" />
  );
  return (
    <g>
      <rect x={-14} y={-r - 22} width={28} height={16} rx={4} fill={COL.ink} />
      <circle r={r} fill="#fff" {...K} strokeWidth={8} />
      {Array.from({ length: 12 }).map((_, i) => {
        const a = (i / 12) * Math.PI * 2;
        return <circle key={i} cx={Math.sin(a) * r * 0.78} cy={-Math.cos(a) * r * 0.78} r={4} fill={COL.ink} />;
      })}
      {hand(h, r * 0.45, 9)}
      {hand(m, r * 0.7, 6)}
      <circle r={7} fill={COL.red} />
    </g>
  );
};

export const Heart: React.FC<{ f: number; s?: number; color?: string }> = ({ f, s = 1, color = COL.red }) => {
  const beat = 1 + Math.max(0, Math.sin(f * 0.35)) * 0.12;
  return (
    <g transform={`scale(${s * beat})`}>
      <path d="M0,40 C-70,-5 -55,-60 -18,-55 C0,-52 0,-35 0,-30 C0,-35 0,-52 18,-55 C55,-60 70,-5 0,40 Z" fill={color} {...K} />
      <path d="M-30,-35 Q-40,-25 -38,-12" stroke="#fff" strokeWidth={7} fill="none" strokeLinecap="round" opacity={0.7} />
    </g>
  );
};

export const Trophy: React.FC<{ f: number }> = ({ f }) => {
  const shine = (f % 40) / 40;
  return (
    <g>
      <path d="M-55,-80 L55,-80 L45,-10 Q0,30 -45,-10 Z" fill={COL.gold} {...K} />
      <path d="M-55,-65 Q-95,-60 -80,-25 Q-70,-8 -45,-15" fill="none" {...K} />
      <path d="M55,-65 Q95,-60 80,-25 Q70,-8 45,-15" fill="none" {...K} />
      <rect x={-10} y={10} width={20} height={34} fill={COL.gold} {...K} />
      <rect x={-45} y={44} width={90} height={26} rx={4} fill={COL.ink} />
      <line x1={-40 + shine * 70} y1={-72} x2={-48 + shine * 70} y2={-30} stroke="#fff6c8" strokeWidth={8} strokeLinecap="round" opacity={1 - shine} />
    </g>
  );
};

export const RainCloud: React.FC<{ f: number }> = ({ f }) => (
  <g>
    {Array.from({ length: 7 }).map((_, i) => {
      const x = -60 + i * 20;
      const y = ((f * 9 + random(`rain${i}`) * 120) % 120) + 40;
      return <line key={i} x1={x} y1={y} x2={x - 6} y2={y + 22} stroke={COL.blue} strokeWidth={5} strokeLinecap="round" opacity={0.8} />;
    })}
    <path d="M-80,30 Q-110,30 -105,0 Q-100,-30 -65,-25 Q-55,-60 -15,-55 Q20,-75 45,-40 Q90,-45 90,-5 Q105,30 70,30 Z" fill="#9aa3ad" {...K} />
  </g>
);

export const Plant: React.FC<{ grow: number }> = ({ grow }) => {
  const g = Math.max(0, Math.min(1, grow));
  const stem = 30 + 110 * g;
  return (
    <g>
      <path d={`M0,0 Q${-10 * g},${-stem / 2} 0,${-stem}`} stroke={COL.green} strokeWidth={9} fill="none" strokeLinecap="round" />
      {g > 0.3 && <ellipse cx={-26} cy={-stem * 0.55} rx={26 * g} ry={12 * g} transform={`rotate(-30 -26 ${-stem * 0.55})`} fill={COL.green} {...K} strokeWidth={4} />}
      {g > 0.55 && <ellipse cx={26} cy={-stem * 0.75} rx={26 * g} ry={12 * g} transform={`rotate(30 26 ${-stem * 0.75})`} fill={COL.green} {...K} strokeWidth={4} />}
      {g > 0.85 && <circle cx={0} cy={-stem - 14} r={16} fill={COL.yellow} {...K} strokeWidth={4} />}
      <path d="M-48,0 L48,0 L36,62 L-36,62 Z" fill="#c8663b" {...K} />
      <rect x={-54} y={-8} width={108} height={18} rx={4} fill="#a9522e" {...K} />
    </g>
  );
};

export const Mountain: React.FC<{ f: number }> = ({ f }) => (
  <g>
    <polygon points="-170,0 -20,-300 40,-210 90,-260 190,0" fill="#c9c4b5" {...K} />
    <polygon points="-20,-300 -62,-216 -34,-230 -12,-206 12,-248" fill="#fff" {...K} strokeWidth={4} />
    <line x1={-20} y1={-300} x2={-20} y2={-380} stroke={COL.ink} strokeWidth={6} strokeLinecap="round" />
    <path d={`M-20,-380 Q${10 + Math.sin(f * 0.3) * 6},${-372} 34,-362 L-20,-344 Z`} fill={COL.red} {...K} strokeWidth={4} />
  </g>
);

export const Phone: React.FC<{ f: number }> = ({ f }) => (
  <g>
    <rect x={-24} y={-42} width={48} height={84} rx={9} fill={COL.ink} />
    <rect x={-18} y={-34} width={36} height={66} rx={4} fill="#7fd0ff" />
    {[0, 1, 2].map((i) => {
      const y = ((i * 22 - f * 3) % 66 + 66) % 66 - 30;
      return <rect key={i} x={-13} y={y} width={26} height={12} rx={3} fill="#fff" opacity={0.85} />;
    })}
  </g>
);

export const Book: React.FC<{ f: number }> = ({ f }) => {
  const flip = (f % 50) / 50;
  return (
    <g>
      <path d="M0,-38 L-62,-46 L-62,34 L0,42 Z" fill="#fff" {...K} strokeWidth={5} />
      <path d="M0,-38 L62,-46 L62,34 L0,42 Z" fill="#fff" {...K} strokeWidth={5} />
      {[-24, -8, 8].map((y) => (
        <line key={y} x1={-50} y1={y} x2={-12} y2={y + 4} stroke="#bbb" strokeWidth={4} />
      ))}
      {flip < 0.4 && (
        <path d={`M0,-38 L${62 - flip * 300},-46 L${62 - flip * 300},34 L0,42 Z`} fill="#f1efe8" {...K} strokeWidth={4} />
      )}
      <rect x={-70} y={34} width={140} height={14} rx={4} fill={COL.blue} {...K} strokeWidth={4} />
    </g>
  );
};

export const Bulb: React.FC<{ t: number; f: number }> = ({ t, f }) => {
  if (t <= 0) return null;
  const s = interpolate(t, [0, 0.6, 1], [0.2, 1.2, 1]);
  return (
    <g transform={`scale(${s})`}>
      {Array.from({ length: 8 }).map((_, i) => {
        const a = (i / 8) * Math.PI * 2 + f * 0.02;
        return (
          <line key={i} x1={Math.cos(a) * 72} y1={Math.sin(a) * 72 - 10} x2={Math.cos(a) * 100} y2={Math.sin(a) * 100 - 10} stroke={COL.yellow} strokeWidth={9} strokeLinecap="round" />
        );
      })}
      <circle cy={-10} r={52} fill="#ffe46b" {...K} />
      <rect x={-22} y={36} width={44} height={30} rx={6} fill="#9a9a9a" {...K} strokeWidth={5} />
      <path d="M-14,-6 L-4,8 L6,-8 L14,6" stroke="#c98a00" strokeWidth={5} fill="none" strokeLinecap="round" />
    </g>
  );
};

// stairs that rise to the right from (0,0): `n` steps of w x h
export const Stairs: React.FC<{ n: number; w: number; h: number }> = ({ n, w, h }) => (
  <g>
    {Array.from({ length: n }).map((_, i) => (
      <rect key={i} x={i * w} y={-(i + 1) * h} width={(n - i) * w} height={h} fill={i % 2 ? "#e2dccb" : "#d6cfba"} {...K} strokeWidth={5} />
    ))}
  </g>
);

export const Stool: React.FC = () => (
  <g>
    <rect x={-70} y={-14} width={140} height={22} rx={6} fill="#b5763d" {...K} strokeWidth={5} />
    <line x1={-52} y1={8} x2={-62} y2={90} {...K} strokeWidth={9} />
    <line x1={52} y1={8} x2={62} y2={90} {...K} strokeWidth={9} />
  </g>
);

// thought bubble with a symbol inside (e.g. "?")
export const Thought: React.FC<{ t: number; text: string; f: number }> = ({ t, text, f }) => {
  if (t <= 0) return null;
  return (
    <g transform={`translate(0 ${Math.sin(f * 0.12) * 6}) scale(${t})`}>
      <circle cx={-70} cy={110} r={12} fill="#fff" {...K} strokeWidth={5} />
      <circle cx={-45} cy={70} r={20} fill="#fff" {...K} strokeWidth={5} />
      <ellipse cx={0} cy={0} rx={90} ry={66} fill="#fff" {...K} />
      <text y={30} textAnchor="middle" fontFamily={FONT.hindi} fontWeight={800} fontSize={84} fill={COL.ink}>
        {text}
      </text>
    </g>
  );
};
