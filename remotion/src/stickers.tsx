import React from "react";
import { interpolate } from "remotion";
import { COL } from "./engine/fx";

// Small icons that punch up a beat (picked by the director pass): drawn here, so no emoji font is needed.
const K = { stroke: COL.ink, strokeWidth: 5, strokeLinejoin: "round" as const, strokeLinecap: "round" as const };

const SHAPES: Record<string, React.ReactNode> = {
  fire: (
    <g>
      <path d="M50,8 C64,30 82,40 80,64 C78,84 64,94 50,94 C34,94 20,82 20,64 C20,48 32,40 36,26 C42,36 44,42 48,44 C50,30 50,20 50,8 Z" fill="#ff6a2b" {...K} />
      <path d="M50,52 C58,62 64,68 62,78 C60,86 54,90 50,90 C44,90 38,84 38,76 C38,68 46,64 50,52 Z" fill="#ffd23f" />
    </g>
  ),
  star: <polygon points="50,6 62,36 94,38 69,58 78,90 50,72 22,90 31,58 6,38 38,36" fill={COL.yellow} {...K} />,
  check: (
    <g>
      <circle cx={50} cy={50} r={42} fill={COL.green} {...K} />
      <path d="M30,52 L44,66 L72,36" fill="none" stroke="#fff" strokeWidth={11} strokeLinecap="round" strokeLinejoin="round" />
    </g>
  ),
  cross: (
    <g>
      <circle cx={50} cy={50} r={42} fill={COL.red} {...K} />
      <path d="M34,34 L66,66 M66,34 L34,66" stroke="#fff" strokeWidth={11} strokeLinecap="round" />
    </g>
  ),
  lightning: <polygon points="58,4 18,56 46,56 38,96 82,40 54,40" fill={COL.yellow} {...K} />,
  money: (
    <g>
      <rect x={8} y={24} width={84} height={52} rx={8} fill="#cfe8c8" stroke="#3a8f3e" strokeWidth={6} />
      <circle cx={50} cy={50} r={16} fill="#3a8f3e" />
      <text x={50} y={58} textAnchor="middle" fontFamily="Poppins" fontWeight={800} fontSize={24} fill="#cfe8c8">₹</text>
    </g>
  ),
  heart: <path d="M50,88 C10,60 6,34 22,22 C34,13 46,20 50,30 C54,20 66,13 78,22 C94,34 90,60 50,88 Z" fill={COL.red} {...K} />,
  warning: (
    <g>
      <polygon points="50,8 94,88 6,88" fill={COL.yellow} {...K} />
      <rect x={45} y={36} width={10} height={28} rx={4} fill={COL.ink} />
      <circle cx={50} cy={74} r={6} fill={COL.ink} />
    </g>
  ),
  hundred: (
    <g>
      <text x={50} y={62} textAnchor="middle" fontFamily="Poppins" fontWeight={800} fontSize={46} fill={COL.red} fontStyle="italic">100</text>
      <path d="M14,72 Q50,80 86,70 M18,82 Q50,90 84,80" fill="none" stroke={COL.red} strokeWidth={6} strokeLinecap="round" />
    </g>
  ),
  question: (
    <g>
      <circle cx={50} cy={50} r={42} fill={COL.blue} {...K} />
      <text x={50} y={70} textAnchor="middle" fontFamily="Poppins" fontWeight={800} fontSize={58} fill="#fff">?</text>
    </g>
  ),
};

export const STICKERS = Object.keys(SHAPES);

export const Sticker: React.FC<{ name: string; f: number; size?: number }> = ({ name, f, size = 140 }) => {
  const shape = SHAPES[name];
  if (!shape || f < 0) return null;
  const s = interpolate(f, [0, 6, 10, 14], [0, 1.25, 0.92, 1], { extrapolateRight: "clamp" });
  const wobble = Math.sin(f * 0.18) * 8;
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" style={{ transform: `scale(${s}) rotate(${12 + wobble}deg)`, overflow: "visible",
      filter: "drop-shadow(4px 5px 0 rgba(0,0,0,.25))" }}>
      {shape}
    </svg>
  );
};
