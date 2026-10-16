import React from "react";
import { interpolate, interpolateColors, random } from "remotion";
import { COL } from "./engine/fx";
import { GROUND } from "./actions";

// Where a beat happens, drawn in two layers: `far` (walls, sky, skyline) moves least with the camera and
// `mid` (furniture, lamp posts, trees) a little more, so camera moves read as depth. Drawings run past the
// frame edges (x -420..1500) so pans and wide shots never show an edge. `dark` places switch the caption to
// white. Everything stays below the caption area's line of sight: tall items keep to the sides.

export type Place = { far: React.ReactNode; mid: React.ReactNode; floor: string; dark?: boolean; glow?: boolean };

const K = { stroke: COL.ink, strokeWidth: 6, strokeLinejoin: "round" as const, strokeLinecap: "round" as const };
const L = -420, R = 1500;

const Floor: React.FC<{ color: string }> = ({ color }) => <rect x={L} y={GROUND} width={R - L} height={900} fill={color} />;

const Window: React.FC<{ x: number; y: number; w: number; h: number; sky?: string }> = ({ x, y, w, h, sky = "#bfe3ff" }) => (
  <g>
    <rect x={x} y={y} width={w} height={h} fill={sky} {...K} />
    <line x1={x + w / 2} y1={y} x2={x + w / 2} y2={y + h} {...K} />
    <line x1={x} y1={y + h / 2} x2={x + w} y2={y + h / 2} {...K} />
    <path d={`M${x - 20},${y - 14} Q${x + 10},${y + h / 2} ${x - 4},${y + h + 20} L${x - 34},${y + h + 20} L${x - 34},${y - 14} Z`} fill="#d9534f" {...K} strokeWidth={4} />
    <path d={`M${x + w + 20},${y - 14} Q${x + w - 10},${y + h / 2} ${x + w + 4},${y + h + 20} L${x + w + 34},${y + h + 20} L${x + w + 34},${y - 14} Z`} fill="#d9534f" {...K} strokeWidth={4} />
  </g>
);

const Rain: React.FC<{ f: number; heavy?: boolean }> = ({ f, heavy }) => (
  <g opacity={0.7}>
    {Array.from({ length: heavy ? 90 : 60 }).map((_, i) => {
      const x = L + random(`rx${i}`) * (R - L);
      const y = ((random(`ry${i}`) * 1500 + f * 46) % 1500) + 60;
      return <line key={i} x1={x} y1={y} x2={x - 14} y2={y + 46} stroke="#9fc3e6" strokeWidth={4} strokeLinecap="round" />;
    })}
  </g>
);

const Skyline: React.FC<{ color: string; lit: number }> = ({ color, lit }) => (
  <g>
    {Array.from({ length: 11 }).map((_, i) => {
      const x = L + i * 180;
      const h = 220 + random(`sk${i}`) * 240;
      return (
        <g key={i}>
          <rect x={x} y={GROUND - h} width={160} height={h} fill={color} />
          {Array.from({ length: Math.floor(h / 70) }).map((_, r) => (
            <rect key={r} x={x + 30 + (r % 2) * 60} y={GROUND - h + 30 + r * 70} width={34} height={30} fill="#ffe7a3" opacity={lit * (random(`lw${i}${r}`) > 0.35 ? 1 : 0.2)} />
          ))}
        </g>
      );
    })}
  </g>
);

export const place = (name: string | undefined, f: number, dur = 120): Place => {
  switch (name) {
    case "home":
      return {
        floor: "#d8b98f",
        far: (
          <g>
            <rect x={L} y={0} width={R - L} height={GROUND} fill="#f3e3c7" />
            <rect x={L} y={GROUND - 60} width={R - L} height={60} fill="#e2cba5" />
            <Window x={-150} y={760} w={260} h={300} />
            <rect x={860} y={800} width={170} height={130} rx={6} fill="#fff" {...K} />
            <circle cx={945} cy={865} r={34} fill="#f2c12e" />
            <path d="M880,915 L930,860 L980,915 Z" fill={COL.green} />
          </g>
        ),
        mid: (
          <g>
            <Floor color="#d8b98f" />
            <rect x={1120} y={GROUND - 260} width={34} height={260} fill="#8a5a3b" {...K} strokeWidth={5} />
            <path d="M1080,1040 L1194,1040 L1170,980 L1104,980 Z" fill="#fff3b0" {...K} strokeWidth={5} />
          </g>
        ),
      };
    case "office":
      return {
        floor: "#c9ced6",
        far: (
          <g>
            <rect x={L} y={0} width={R - L} height={GROUND} fill="#e6ebf1" />
            {[-260, 1040].map((x) => (
              <g key={x}>
                <rect x={x} y={740} width={260} height={320} fill="#cfe4f7" {...K} />
                {Array.from({ length: 7 }).map((_, i) => (
                  <line key={i} x1={x} y1={760 + i * 44} x2={x + 260} y2={760 + i * 44} stroke="#8aa4bf" strokeWidth={5} />
                ))}
              </g>
            ))}
            <circle cx={880} cy={820} r={56} fill="#fff" {...K} />
            <line x1={880} y1={820} x2={880} y2={784} {...K} />
            <line x1={880} y1={820} x2={880 + Math.sin(f * 0.05) * 30} y2={820 - Math.cos(f * 0.05) * 30} stroke={COL.red} strokeWidth={4} strokeLinecap="round" />
          </g>
        ),
        mid: (
          <g>
            <Floor color="#c9ced6" />
            <rect x={-300} y={GROUND - 150} width={330} height={20} fill="#8a6a4f" {...K} strokeWidth={5} />
            <rect x={-80} y={GROUND - 230} width={110} height={80} rx={6} fill="#333" {...K} strokeWidth={5} />
          </g>
        ),
      };
    case "street":
      return {
        floor: "#9a9a9a",
        far: (
          <g>
            <rect x={L} y={0} width={R - L} height={GROUND} fill="#dff0fb" />
            {Array.from({ length: 11 }).map((_, i) => {
              const x = L + i * 180;
              const h = 260 + random(`bld${i}`) * 260;
              return (
                <g key={i}>
                  <rect x={x} y={GROUND - 70 - h} width={160} height={h} fill={i % 2 ? "#b8c4d6" : "#a7b4c8"} {...K} strokeWidth={4} />
                  {Array.from({ length: Math.floor(h / 70) }).map((_, r) => (
                    <g key={r}>
                      <rect x={x + 26} y={GROUND - 40 - h + r * 70} width={36} height={34} fill="#fff7c2" />
                      <rect x={x + 98} y={GROUND - 40 - h + r * 70} width={36} height={34} fill="#fff7c2" />
                    </g>
                  ))}
                </g>
              );
            })}
            <rect x={L} y={GROUND - 70} width={R - L} height={70} fill="#c4c4c4" />
          </g>
        ),
        mid: (
          <g>
            <Floor color="#8d8d8d" />
            {[-200, 140, 480, 820, 1160].map((x) => (
              <rect key={x} x={x} y={GROUND + 120} width={120} height={18} fill="#f5f5f5" />
            ))}
            <line x1={1010} y1={GROUND} x2={1010} y2={GROUND - 520} {...K} strokeWidth={14} />
            <path d={`M1010,${GROUND - 520} Q1010,${GROUND - 560} 960,${GROUND - 560}`} {...K} strokeWidth={12} fill="none" />
            <ellipse cx={950} cy={GROUND - 545} rx={34} ry={18} fill="#fff3b0" {...K} strokeWidth={5} />
          </g>
        ),
      };
    case "night":
      return {
        dark: true,
        glow: true,
        floor: "#2d3557",
        far: (
          <g>
            <defs>
              <linearGradient id="nightSky" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="#141a33" />
                <stop offset="1" stopColor="#4a5a8c" />
              </linearGradient>
            </defs>
            <rect x={L} y={0} width={R - L} height={GROUND} fill="url(#nightSky)" />
            {Array.from({ length: 40 }).map((_, i) => (
              <circle key={i} cx={L + random(`sx${i}`) * (R - L)} cy={60 + random(`sy${i}`) * 1000} r={2 + random(`sr${i}`) * 3}
                fill="#fff" opacity={0.4 + 0.6 * Math.abs(Math.sin(f * 0.08 + i))} />
            ))}
            <circle cx={880} cy={780} r={70} fill="#fdf3c4" />
            <circle cx={905} cy={765} r={62} fill="#26305a" opacity={0.0} />
          </g>
        ),
        mid: <Floor color="#2d3557" />,
      };
    case "park":
      return {
        floor: "#9ccc65",
        far: (
          <g>
            <rect x={L} y={0} width={R - L} height={GROUND} fill="#e4f4ff" />
            <ellipse cx={540} cy={GROUND} rx={1100} ry={120} fill="#b9df8f" />
            {[-260, -40, 1080, 1300].map((x, i) => (
              <g key={x}>
                <rect x={x - 16} y={GROUND - 260} width={32} height={200} fill="#8a5a3b" {...K} strokeWidth={5} />
                <circle cx={x} cy={GROUND - 300} r={110 + (i % 2) * 20} fill={i % 2 ? "#5fae4f" : "#4f9a43"} {...K} />
              </g>
            ))}
          </g>
        ),
        mid: (
          <g>
            <Floor color="#9ccc65" />
            <rect x={1020} y={GROUND - 90} width={260} height={18} fill="#a0663f" {...K} strokeWidth={5} />
            <line x1={1040} y1={GROUND - 72} x2={1040} y2={GROUND} {...K} strokeWidth={8} />
            <line x1={1260} y1={GROUND - 72} x2={1260} y2={GROUND} {...K} strokeWidth={8} />
          </g>
        ),
      };
    case "classroom":
      return {
        floor: "#cfb995",
        far: (
          <g>
            <rect x={L} y={0} width={R - L} height={GROUND} fill="#f1ead7" />
            <rect x={-330} y={760} width={520} height={300} fill="#2f4f3e" stroke="#7a5230" strokeWidth={16} />
            <path d="M-290,820 q40,-30 80,0 t80,0 M-290,880 L-120,880 M-290,940 L-60,940" stroke="#f5f5f5" strokeWidth={6} fill="none" strokeLinecap="round" />
            <text x={-20} y={850} fontFamily="Poppins" fontWeight={700} fontSize={60} fill="#f5f5f5">A+</text>
            <rect x={900} y={790} width={180} height={230} fill="#fff" {...K} />
            {[0, 1, 2, 3].map((i) => <line key={i} x1={925} y1={840 + i * 44} x2={1055} y2={840 + i * 44} stroke="#9ab" strokeWidth={5} />)}
          </g>
        ),
        mid: <Floor color="#cfb995" />,
      };
    case "kitchen":
      return {
        floor: "#d7c4a3",
        far: (
          <g>
            <rect x={L} y={0} width={R - L} height={GROUND} fill="#fdf1e0" />
            {Array.from({ length: 16 }).map((_, i) => (
              <rect key={i} x={L + i * 120} y={GROUND - 330} width={118} height={78} fill={i % 2 ? "#e9f4f1" : "#d8ece7"} />
            ))}
            {[-300, 1040].map((x) => (
              <g key={x}>
                <rect x={x} y={GROUND - 250} width={300} height={250} fill="#c98b52" {...K} />
                <rect x={x} y={GROUND - 262} width={300} height={18} fill="#8a6a4f" {...K} strokeWidth={4} />
                <line x1={x + 150} y1={GROUND - 240} x2={x + 150} y2={GROUND} {...K} strokeWidth={4} />
              </g>
            ))}
            <rect x={1080} y={GROUND - 300} width={140} height={40} rx={8} fill="#555" {...K} strokeWidth={4} />
            <path d={`M1110,${GROUND - 310} q10,-30 0,-60 M1170,${GROUND - 310} q10,-30 0,-60`} stroke="#ccc" strokeWidth={6} fill="none" opacity={0.6 + Math.sin(f * 0.2) * 0.3} />
            <rect x={-240} y={760} width={220} height={20} fill="#8a6a4f" />
            {[0, 1, 2].map((i) => <rect key={i} x={-230 + i * 70} y={700} width={46} height={60} rx={6} fill={["#e5322d", "#f2c12e", "#2fa84f"][i]} {...K} strokeWidth={4} />)}
          </g>
        ),
        mid: <Floor color="#d7c4a3" />,
      };
    case "bus":
      return {
        floor: "#7b7f86",
        far: (
          <g>
            <rect x={L} y={0} width={R - L} height={GROUND} fill="#f0c94c" />
            <g transform={`translate(${-(f * 14) % 600} 0)`}>
              {Array.from({ length: 6 }).map((_, i) => (
                <g key={i}>
                  <rect x={L + i * 600} y={760} width={520} height={300} rx={20} fill="#cfe8ff" {...K} />
                  <rect x={L + i * 600 + 60} y={900 - random(`bb${i}`) * 60} width={140} height={160 + random(`bb${i}`) * 60} fill="#9fb4cc" />
                  <circle cx={L + i * 600 + 380} cy={880} r={50} fill="#7cc36b" />
                </g>
              ))}
            </g>
            <rect x={L} y={700} width={R - L} height={60} fill="#e2b93a" />
          </g>
        ),
        mid: (
          <g>
            <Floor color="#7b7f86" />
            <line x1={L} y1={640} x2={R} y2={640} {...K} strokeWidth={12} />
            {[-120, 220, 860, 1200].map((x) => <path key={x} d={`M${x},640 l0,60 a24,24 0 1 0 1,0`} fill="none" {...K} strokeWidth={6} />)}
            <rect x={1060} y={GROUND - 170} width={300} height={40} rx={10} fill="#3c6fb6" {...K} strokeWidth={5} />
            <rect x={1300} y={GROUND - 300} width={50} height={170} rx={10} fill="#3c6fb6" {...K} strokeWidth={5} />
          </g>
        ),
      };
    case "hospital":
      return {
        floor: "#d9e3e6",
        far: (
          <g>
            <rect x={L} y={0} width={R - L} height={GROUND} fill="#eef6f7" />
            <rect x={L} y={GROUND - 120} width={R - L} height={120} fill="#cfe2e6" />
            <rect x={860} y={780} width={180} height={180} rx={14} fill="#fff" {...K} />
            <rect x={930} y={810} width={40} height={120} fill={COL.red} />
            <rect x={890} y={850} width={120} height={40} fill={COL.red} />
            <polyline points={`-300,820 -250,820 -230,${780 + Math.sin(f * 0.5) * 6} -210,860 -190,800 -170,820 -100,820`} fill="none" stroke={COL.green} strokeWidth={6} />
            <rect x={-320} y={740} width={240} height={160} rx={10} fill="none" {...K} strokeWidth={5} />
          </g>
        ),
        mid: (
          <g>
            <Floor color="#d9e3e6" />
            <rect x={1080} y={GROUND - 120} width={360} height={60} rx={10} fill="#fff" {...K} strokeWidth={5} />
            <line x1={1110} y1={GROUND - 60} x2={1110} y2={GROUND} {...K} strokeWidth={8} />
            <line x1={1410} y1={GROUND - 60} x2={1410} y2={GROUND} {...K} strokeWidth={8} />
            <line x1={1040} y1={GROUND} x2={1040} y2={GROUND - 420} {...K} strokeWidth={8} />
            <path d={`M1040,${GROUND - 420} l60,0`} {...K} strokeWidth={6} />
            <rect x={1080} y={GROUND - 420} width={40} height={70} rx={10} fill="#bfe3ff" {...K} strokeWidth={4} />
          </g>
        ),
      };
    case "sunset":
      return {
        floor: "#c9875c",
        far: (
          <g>
            <defs>
              <linearGradient id="sunsetSky" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="#ffd59e" />
                <stop offset="0.6" stopColor="#ff9a62" />
                <stop offset="1" stopColor="#e8607a" />
              </linearGradient>
            </defs>
            <rect x={L} y={0} width={R - L} height={GROUND} fill="url(#sunsetSky)" />
            <circle cx={820} cy={GROUND - 120 + Math.min(40, f * 0.3)} r={150} fill="#fff1b8" opacity={0.95} />
            <Skyline color="#8a4f63" lit={0.4} />
          </g>
        ),
        mid: <Floor color="#c9875c" />,
      };
    case "rain":
      return {
        floor: "#5f6670",
        far: (
          <g>
            <rect x={L} y={0} width={R - L} height={GROUND} fill="#b6c2cf" />
            <Skyline color="#7d8896" lit={0.5} />
          </g>
        ),
        mid: (
          <g>
            <Floor color="#5f6670" />
            {Array.from({ length: 8 }).map((_, i) => (
              <ellipse key={i} cx={L + i * 240 + 60} cy={GROUND + 90 + (i % 3) * 60} rx={60 + 20 * Math.sin(f * 0.2 + i)} ry={10} fill="none" stroke="#9fc3e6" strokeWidth={3} opacity={0.6} />
            ))}
            <Rain f={f} heavy />
          </g>
        ),
      };
    case "day_to_night": {
      // the sky darkens across the beat, the sun sets and windows light up: time passing
      const t = interpolate(f, [0, Math.max(10, dur - 10)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
      return {
        dark: t > 0.55,
        glow: t > 0.55,
        floor: interpolateColors(t, [0, 1], ["#9ccc65", "#2d3557"]),
        far: (
          <g>
            <rect x={L} y={0} width={R - L} height={GROUND} fill={interpolateColors(t, [0, 0.5, 1], ["#bfe6ff", "#ff9a62", "#1b2347"])} />
            <circle cx={880} cy={760 + t * 600} r={80} fill="#fff3a6" opacity={1 - t} />
            <circle cx={200} cy={900 - t * 180} r={60} fill="#fdf3c4" opacity={Math.max(0, t * 2 - 1)} />
            <Skyline color={interpolateColors(t, [0, 1], ["#a7b4c8", "#202744"])} lit={Math.max(0, t * 2 - 0.8)} />
          </g>
        ),
        mid: <Floor color={interpolateColors(t, [0, 1], ["#9ccc65", "#2d3557"])} />,
      };
    }
    default:
      return { floor: "transparent", far: null, mid: null };
  }
};

// soft light behind the hero, so the black figure reads on dark places
export const Glow: React.FC<{ x: number; y: number }> = ({ x, y }) => (
  <g>
    <defs>
      <radialGradient id="heroGlow">
        <stop offset="0" stopColor="#fff6d8" stopOpacity={0.85} />
        <stop offset="1" stopColor="#fff6d8" stopOpacity={0} />
      </radialGradient>
    </defs>
    <ellipse cx={x} cy={y} rx={420} ry={460} fill="url(#heroGlow)" />
  </g>
);
