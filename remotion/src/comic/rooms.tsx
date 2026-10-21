import React from "react";
import { FONT } from "../engine/fx";
import { TABLE } from "./Kid";

// The one room of a comic Reel (reel/comic.py ROOMS), in flat cartoon colours with soft outlines. `back` is the
// wall and furniture behind the kid (slightly blurred by ComicReel, for depth); `table` is what the kid sits
// behind, drawn over the body and under the arms. Tall things keep to the sides: the head fills the middle.

export type Room = { back: React.ReactNode; table: React.ReactNode };

const O = { stroke: "#2a2320", strokeWidth: 6, strokeLinejoin: "round" as const, strokeLinecap: "round" as const };
const L = -80, R = 1160;
const TOP = TABLE - 30; // back edge of the table top
const FRONT = TABLE + 52; // front edge

const Wall: React.FC<{ color: string; floor: string; base?: number }> = ({ color, floor, base = 1180 }) => (
  <>
    <rect x={L} y={-80} width={R - L} height={base + 80} fill={color} />
    <rect x={L} y={base} width={R - L} height={1920 - base} fill={floor} />
    <rect x={L} y={base - 24} width={R - L} height={24} fill="rgba(0,0,0,.12)" />
  </>
);

const Top: React.FC<{ color: string; front: string }> = ({ color, front }) => (
  <>
    <rect x={L} y={FRONT} width={R - L} height={1920 - FRONT} fill={front} {...O} />
    <path d={`M${L},${TOP} L${R},${TOP} L${R},${FRONT} L${L},${FRONT} Z`} fill={color} {...O} />
    <path d={`M${L},${FRONT + 14} L${R},${FRONT + 14}`} stroke="rgba(0,0,0,.18)" strokeWidth={10} />
  </>
);

const Curtain: React.FC<{ x: number; y: number; h: number; flip?: boolean; color: string }> = ({ x, y, h, flip, color }) => {
  const s = flip ? -1 : 1;
  return (
    <g>
      <path d={`M${x},${y} L${x + 90 * s},${y} Q${x + 60 * s},${y + h * 0.5} ${x + 100 * s},${y + h} L${x},${y + h} Z`} fill={color} {...O} strokeWidth={5} />
      {[0.2, 0.45, 0.7].map((t, i) => (
        <circle key={i} cx={x + 40 * s} cy={y + h * t} r={9} fill="#f08a4b" opacity={0.7} />
      ))}
    </g>
  );
};

const Clock: React.FC<{ x: number; y: number; r: number; f: number }> = ({ x, y, r, f }) => (
  <g>
    <circle cx={x} cy={y} r={r} fill="#fff" {...O} />
    <path d={`M${x},${y} L${x},${y - r * 0.55}`} {...O} strokeWidth={7} />
    <path d={`M${x},${y} L${x + Math.sin(f * 0.1) * r * 0.75},${y - Math.cos(f * 0.1) * r * 0.75}`} stroke="#e5322d" strokeWidth={5} strokeLinecap="round" />
  </g>
);

const Plant: React.FC<{ x: number; y: number }> = ({ x, y }) => (
  <g>
    {[-50, -20, 10, 40].map((a, i) => (
      <path key={i} d={`M${x},${y} Q${x + a * 1.6},${y - 120} ${x + a * 2.4},${y - 210 + i * 18}`} stroke="#3f8f4a" strokeWidth={22} fill="none" strokeLinecap="round" />
    ))}
    <path d={`M${x - 70},${y} L${x + 70},${y} L${x + 52},${y + 110} L${x - 52},${y + 110} Z`} fill="#c8643b" {...O} />
  </g>
);

// `computer`: the bedroom desk shows the computer only when the line is about it (typing, looking at the screen)
export const room = (name: string | undefined, f: number, computer = true): Room => {
  switch (name) {
    case "gym":
      return {
        back: (
          <g>
            <Wall color="#dfe3ea" floor="#5c6370" />
            <rect x={120} y={340} width={840} height={520} rx={8} fill="#cfe3f5" {...O} />
            <path d="M200,360 L300,840 M760,360 L860,840" stroke="#fff" strokeWidth={18} opacity={0.5} />
            <text x={250} y={450} textAnchor="middle" fontFamily={FONT.hindi} fontWeight={800} fontSize={64} fill="#e03131">GYM</text>
            {[0, 1].map((r) => (
              <g key={r}>
                <rect x={-40} y={940 + r * 120} width={250} height={16} fill="#495057" />
                <rect x={870} y={940 + r * 120} width={250} height={16} fill="#495057" />
                {[0, 1, 2].map((i) => (
                  <g key={i}>
                    <rect x={-20 + i * 80} y={900 + r * 120} width={22} height={50} rx={6} fill="#212529" />
                    <rect x={890 + i * 80} y={900 + r * 120} width={22} height={50} rx={6} fill="#212529" />
                  </g>
                ))}
              </g>
            ))}
          </g>
        ),
        table: (
          <g>
            <Top color="#343a40" front="#212529" />
            <path d={`M140,${TOP + 22} L330,${TOP + 22}`} stroke="#adb5bd" strokeWidth={14} strokeLinecap="round" />
            <rect x={110} y={TOP - 10} width={44} height={64} rx={10} fill="#495057" {...O} strokeWidth={4} />
            <rect x={316} y={TOP - 10} width={44} height={64} rx={10} fill="#495057" {...O} strokeWidth={4} />
            <path d={`M830,${TOP - 80} L900,${TOP - 80} L890,${TOP + 30} L840,${TOP + 30} Z`} fill="#4dabf7" {...O} strokeWidth={5} />
            <rect x={826} y={TOP - 104} width={78} height={28} rx={8} fill="#1c7ed6" {...O} strokeWidth={4} />
          </g>
        ),
      };
    case "street":
      return {
        back: (
          <g>
            <rect x={L} y={-80} width={R - L} height={1300} fill="#a5d8ff" />
            {[["#ffd8a8", -60, 380], ["#ffc9c9", 250, 300], ["#d3f9d8", 560, 360], ["#e5dbff", 860, 320]].map(([c, x, y]) => (
              <g key={String(x)}>
                <rect x={Number(x)} y={Number(y)} width={300} height={1200 - Number(y)} fill={String(c)} {...O} />
                <rect x={Number(x) + 40} y={Number(y) + 60} width={90} height={110} fill="#fff" {...O} strokeWidth={5} />
                <rect x={Number(x) + 170} y={Number(y) + 60} width={90} height={110} fill="#fff" {...O} strokeWidth={5} />
              </g>
            ))}
            <rect x={L} y={1100} width={R - L} height={820} fill="#868e96" />
            <path d={`M${L},1180 L${R},1180`} stroke="#fff" strokeWidth={10} strokeDasharray="60 50" />
          </g>
        ),
        table: (
          <g>
            <Top color="#c8813f" front="#9c5d24" />
            <text x={540} y={FRONT + 140} textAnchor="middle" fontFamily={FONT.hindi} fontWeight={800} fontSize={86} fill="#fff3bf">चाय</text>
            <path d={`M150,${TOP - 70} Q150,${TOP - 120} 230,${TOP - 120} Q310,${TOP - 120} 310,${TOP - 70} L300,${TOP + 20} L160,${TOP + 20} Z`} fill="#adb5bd" {...O} strokeWidth={5} />
            <path d={`M310,${TOP - 60} q50,0 60,-40`} {...O} strokeWidth={8} fill="none" />
            {[780, 860, 940].map((x) => <path key={x} d={`M${x - 26},${TOP - 50} L${x + 26},${TOP - 50} L${x + 20},${TOP + 20} L${x - 20},${TOP + 20} Z`} fill="rgba(255,236,200,.9)" {...O} strokeWidth={4} />)}
          </g>
        ),
      };
    case "classroom":
      return {
        back: (
          <g>
            <Wall color="#e3ead6" floor="#b8966f" />
            <rect x={30} y={300} width={1020} height={500} rx={10} fill="#8a5a33" {...O} />
            <rect x={56} y={326} width={968} height={448} fill="#2f5240" />
            <text x={110} y={470} fill="rgba(255,255,255,.75)" fontFamily={FONT.hindi} fontWeight={700} fontSize={64}>2 + 2 = 5 ?</text>
            <text x={760} y={470} fill="rgba(255,255,255,.7)" fontFamily={FONT.hindi} fontWeight={700} fontSize={64}>A B C</text>
            <path d="M120,560 q40,-30 80,0 t80,0 M760,560 l180,0" stroke="rgba(255,255,255,.55)" strokeWidth={8} fill="none" strokeLinecap="round" />
            <rect x={460} y={800} width={160} height={22} fill="#7a4e2c" />
          </g>
        ),
        table: (
          <g>
            <Top color="#cf9a5e" front="#a9743f" />
            {[200, 420, 640, 860].map((x) => <path key={x} d={`M${x},${FRONT + 40} L${x},1920`} stroke="rgba(0,0,0,.15)" strokeWidth={8} />)}
            <path d={`M330,${TOP + 6} L750,${TOP + 6} L770,${TOP + 50} L310,${TOP + 50} Z`} fill="#fff" {...O} strokeWidth={4} />
            <path d={`M540,${TOP + 6} L540,${TOP + 50}`} {...O} strokeWidth={4} />
            <path d={`M800,${TOP + 26} L960,${TOP + 10}`} stroke="#f2c12e" strokeWidth={16} strokeLinecap="round" />
          </g>
        ),
      };
    case "kitchen":
      return {
        back: (
          <g>
            <Wall color="#ddeef3" floor="#c9b49a" />
            {Array.from({ length: 13 }).map((_, i) => <path key={`v${i}`} d={`M${L + i * 100},300 L${L + i * 100},1180`} stroke="#c3dbe3" strokeWidth={4} />)}
            {Array.from({ length: 9 }).map((_, i) => <path key={`h${i}`} d={`M${L},${300 + i * 100} L${R},${300 + i * 100}`} stroke="#c3dbe3" strokeWidth={4} />)}
            <rect x={20} y={600} width={280} height={22} fill="#9b6a43" {...O} strokeWidth={4} />
            {[["#e5322d", 40], ["#f2c12e", 130], ["#2fa84f", 220]].map(([c, x]) => (
              <g key={String(x)}>
                <rect x={Number(x)} y={500} width={64} height={100} rx={10} fill={String(c)} {...O} strokeWidth={4} />
                <rect x={Number(x) - 4} y={488} width={72} height={20} rx={4} fill="#7b7f88" {...O} strokeWidth={4} />
              </g>
            ))}
            <path d="M780,300 L1060,300 L1100,520 L740,520 Z" fill="#a9b0ba" {...O} />
            <rect x={780} y={1040} width={300} height={140} fill="#6f757e" {...O} />
            <circle cx={860} cy={1040} r={14} fill="#2b2d36" />
            <circle cx={1000} cy={1040} r={14} fill="#2b2d36" />
          </g>
        ),
        table: (
          <g>
            <Top color="#e3a868" front="#b77a43" />
            <ellipse cx={540} cy={TOP + 30} rx={150} ry={30} fill="#d4d9de" {...O} strokeWidth={5} />
            <ellipse cx={540} cy={TOP + 26} rx={96} ry={16} fill="#e7b56d" />
            <path d={`M820,${TOP - 60} L890,${TOP - 60} L880,${TOP + 30} L830,${TOP + 30} Z`} fill="rgba(180,220,255,.8)" {...O} strokeWidth={5} />
          </g>
        ),
      };
    case "office":
      return {
        back: (
          <g>
            <Wall color="#d8dee8" floor="#9aa3b0" />
            <rect x={760} y={360} width={310} height={500} fill="#cfe9ff" {...O} />
            {Array.from({ length: 12 }).map((_, i) => <path key={i} d={`M760,${380 + i * 40} L1070,${380 + i * 40}`} stroke="#eef3f8" strokeWidth={18} />)}
            <Clock x={180} y={470} r={74} f={f} />
            <Plant x={130} y={1080} />
          </g>
        ),
        table: (
          <g>
            <Top color="#eef0f4" front="#c3c8d0" />
            <path d={`M40,${TOP} L80,1110 L330,1130 L310,${TOP} Z`} fill="#8b929c" {...O} />
            <circle cx={192} cy={1220} r={22} fill="#dfe4ea" />
            <rect x={820} y={TOP - 70} width={80} height={86} rx={12} fill="#fff" {...O} strokeWidth={5} />
            <path d={`M900,${TOP - 50} q30,10 0,40`} {...O} strokeWidth={5} fill="none" />
          </g>
        ),
      };
    case "living_room":
      return {
        back: (
          <g>
            <Wall color="#f1dfc4" floor="#b98b62" />
            <rect x={20} y={540} width={280} height={190} rx={10} fill="#1f2229" {...O} />
            <rect x={36} y={556} width={248} height={158} fill="#3a7bd5" opacity={0.85} />
            <Clock x={900} y={470} r={70} f={f} />
            <rect x={380} y={330} width={320} height={210} fill="#fff6e4" {...O} />
            <path d="M400,520 L500,420 L580,490 L620,450 L680,520 Z" fill="#7fb77e" />
            <path d="M90,1000 Q90,920 200,920 L880,920 Q990,920 990,1000 L990,1250 L90,1250 Z" fill="#a8473c" {...O} />
            <path d="M130,1000 L130,1250 M950,1000 L950,1250" stroke="#8c3a31" strokeWidth={14} />
          </g>
        ),
        table: (
          <g>
            <Top color="#93603a" front="#744a2b" />
            <rect x={160} y={TOP + 4} width={130} height={34} rx={14} fill="#2b2d36" {...O} strokeWidth={4} />
            <circle cx={260} cy={TOP + 21} r={7} fill="#e5322d" />
            <path d={`M840,${TOP - 54} L910,${TOP - 54} L900,${TOP + 20} L850,${TOP + 20} Z`} fill="#fff" {...O} strokeWidth={5} />
            <ellipse cx={875} cy={TOP - 54} rx={35} ry={9} fill="#b5703a" />
          </g>
        ),
      };
    case "bedroom":
    default:
      return {
        back: (
          <g>
            <Wall color="#ead3c2" floor="#c49c74" />
            <rect x={-40} y={300} width={170} height={900} fill="#a8754a" {...O} />
            <circle cx={100} cy={760} r={12} fill="#f2c12e" {...O} strokeWidth={4} />
            <rect x={160} y={420} width={150} height={210} fill="#2f3b5c" {...O} />
            <circle cx={235} cy={500} r={46} fill="#f7941d" />
            <path d="M205,600 L235,470 L265,600 Z" fill="#fff" opacity={0.9} />
            <rect x={790} y={420} width={260} height={360} fill="#bfe3ff" {...O} />
            <path d="M920,420 L920,780 M790,600 L1050,600" {...O} strokeWidth={5} />
            <Curtain x={790} y={400} h={420} color="#fbe3c4" />
            <Curtain x={1050} y={400} h={420} flip color="#fbe3c4" />
            <rect x={1000} y={900} width={160} height={300} fill="#8a5a36" {...O} />
            <path d="M760,1020 L1160,1020 L1160,1200 L740,1200 Z" fill="#5a78bd" {...O} />
            <path d="M770,1060 L1150,1060 M760,1120 L1150,1120" stroke="#4a66a6" strokeWidth={10} />
            <rect x={820} y={960} width={170} height={70} rx={30} fill="#f6efe3" {...O} />
          </g>
        ),
        table: (
          <g>
            <Top color="#cc915a" front="#a86f3e" />
            <rect x={200} y={FRONT + 70} width={300} height={140} rx={8} fill="none" stroke="rgba(0,0,0,.2)" strokeWidth={8} />
            {computer ? (
              <g>
                <path d={`M30,1070 L300,1100 L300,1300 L30,1310 Z`} fill="#62666e" {...O} />
                <path d={`M300,1100 L330,1108 L330,1292 L300,1300 Z`} fill="#7c818a" {...O} strokeWidth={4} />
                <rect x={140} y={1300} width={60} height={TOP - 1300} fill="#55595f" />
                <path d={`M360,${TOP + 8} L730,${TOP + 8} L760,${TOP + 48} L330,${TOP + 48} Z`} fill="#3a3d44" {...O} strokeWidth={4} />
                {Array.from({ length: 3 }).map((_, r) => Array.from({ length: 12 }).map((_, c) => (
                  <rect key={`${r}-${c}`} x={350 + c * 32 + r * 6} y={TOP + 14 + r * 11} width={24} height={7} rx={2} fill="#6e737c" />
                )))}
                <ellipse cx={830} cy={TOP + 26} rx={34} ry={20} fill="#3a3d44" {...O} strokeWidth={4} />
              </g>
            ) : (
              <g>
                {/* a study desk: a lamp, books and a phone */}
                <path d={`M90,${TOP} L150,${TOP - 10} L130,1180 L80,1120`} stroke="#495057" strokeWidth={14} fill="none" strokeLinecap="round" />
                <path d="M40,1130 L140,1080 L170,1170 Z" fill="#fcc419" {...O} strokeWidth={5} />
                <rect x={180} y={TOP - 40} width={170} height={36} fill="#4dabf7" {...O} strokeWidth={4} />
                <rect x={196} y={TOP - 74} width={150} height={34} fill="#ff8787" {...O} strokeWidth={4} />
                <rect x={800} y={TOP + 6} width={110} height={44} rx={10} fill="#2b2d36" {...O} strokeWidth={4} />
              </g>
            )}
          </g>
        ),
      };
  }
};
