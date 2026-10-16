import React from "react";
import { Easing } from "remotion";
import { Burst, COL, Dust, FONT, SpeedLines, ease } from "./engine/fx";
import { At, Book, Box, Bulb, Clock, Coin, Heart, Mountain, Phone, Plant, RainCloud, Stairs, Stool, Thought, Trophy } from "./engine/props";
import { Joints, Key, P, Pose, SMOOTH, STAND, addPose, idle, runCycle, walkCycle } from "./engine/stick";

// The stage: a 1080x1920 world, ground line at GROUND, the hero at scale S with the hip at HIP.
export const W = 1080;
export const H = 1920;
export const GROUND = 1300;
export const S = 2.2;
export const HIP = STAND.y;
export const CX = STAND.x;

export type Face = "eyes" | "happy" | "sad" | "angry";
type Figure = {
  keys: Key[];
  mod?: (t: number, p: Pose) => Pose;
  face: Face;
  facing?: number;
  color?: string;
  hold?: (j: Joints) => React.ReactNode; // drawn with the figure, positioned from its joints
};
export type Act = Figure & {
  under?: React.ReactNode; // world drawings behind the figure (stairs, stool, speed lines)
  over?: React.ReactNode; // effects in front (bursts, dust, confetti)
  hits: number[]; // camera shake frames
  second?: Figure; // a friend
  propAt?: { x: number } | null; // where the beat's prop goes (null: no room for one)
};

const ARMS = { la1: -18, la2: 8, ra1: 18, ra2: -8, head: 0 }; // arms back at rest
const LEGS = { ll1: -12, ll2: 4, rl1: 12, rl2: -4 };
const SIT_Y = HIP + 40 * S;
const SIT = { y: SIT_Y, ll1: 80, ll2: -80, rl1: 95, rl2: -85, lean: -5 };
const CROUCH = { y: HIP + 30 * S, ll1: -60, ll2: 95, rl1: 50, rl2: 90, lean: 10, la1: -40, la2: -30, ra1: 40, ra2: 30 };
const breathe = (seed = 0) => (t: number, p: Pose) => addPose(p, idle(t, seed));
const mid = (j: Joints) => [(j.lHand[0] + j.rHand[0]) / 2, (j.lHand[1] + j.rHand[1]) / 2] as const;

const Mark: React.FC<{ text: string; t: number; color?: string }> = ({ text, t, color = COL.red }) =>
  t <= 0 ? null : (
    <text textAnchor="middle" fontFamily={FONT.hindi} fontWeight={800} fontSize={140 * Math.min(1, t * 1.3)} fill={color} stroke="#fff" strokeWidth={10} paintOrder="stroke">
      {text}
    </text>
  );

const Confetti: React.FC<{ f: number; from: number }> = ({ f, from }) => {
  const d = f - from;
  if (d < 0 || d > 70) return null;
  const colors = [COL.red, COL.yellow, COL.blue, COL.green, COL.orange, COL.purple];
  return (
    <g opacity={d > 55 ? (70 - d) / 15 : 1}>
      {Array.from({ length: 34 }).map((_, i) => {
        const x = 80 + ((i * 137) % 920) + Math.sin(d * 0.15 + i) * 20;
        const y = 560 + d * (9 + (i % 5) * 2) - ((i * 53) % 140);
        return <rect key={i} x={x} y={y} width={18} height={10} rx={2} fill={colors[i % colors.length]} transform={`rotate(${d * 12 + i * 40} ${x + 9} ${y + 5})`} />;
      })}
    </g>
  );
};

export const act = (action: string, f: number, dur: number): Act => {
  switch (action) {
    case "walk_in": {
      const w = Math.min(Math.round(dur * 0.55), 50);
      return {
        keys: [{ f: 0, p: { x: -170 } }, { f: w, p: { x: CX }, e: (t) => t }, { f: w + 8, p: { ra1: 150, ra2: -20 } }],
        mod: (t, p) => (t < w ? addPose(p, walkCycle(t, 0.3)) : addPose(p, { ...idle(t), ra2: t > w + 8 ? Math.sin(t * 0.45) * 28 : 0 })),
        face: f > w ? "happy" : "eyes",
        hits: [],
        propAt: { x: 880 },
      };
    }
    case "think":
      return {
        keys: [{ f: 0, p: {} }, { f: 8, p: P.think }],
        mod: (t, p) => addPose(p, { ...idle(t), head: Math.sin(t * 0.08) * 5 }),
        face: "eyes",
        hold: (j) => (
          <At x={j.headC[0] + 170} y={j.headC[1] - 190}>
            <Thought t={ease(f, 10, 20)} text="?" f={f} />
          </At>
        ),
        hits: [],
        propAt: { x: 170 },
      };
    case "idea": {
      const at = Math.max(14, Math.round(dur * 0.4));
      return {
        keys: [{ f: 0, p: {} }, { f: 8, p: P.think }, { f: at, p: P.think }, { f: at + 5, p: { ra1: 165, ra2: -10, la1: -30, la2: 10, head: -8 } }],
        mod: breathe(),
        face: f < at ? "eyes" : "happy",
        hold: (j) => (
          <At x={j.headC[0]} y={j.headC[1] - 200}>
            <Bulb t={ease(f, at, at + 10)} f={f} />
          </At>
        ),
        over: <Burst x={CX} y={HIP - 520} at={at} f={f} color={COL.yellow} size={150} />,
        hits: [at],
        propAt: { x: 880 },
      };
    }
    case "sad":
      return {
        keys: [{ f: 0, p: {} }, { f: 14, p: P.sad, e: SMOOTH }],
        mod: (t, p) => addPose(p, { ...idle(t), lean: Math.sin(t * 0.05) * 2 }),
        face: "sad",
        hits: [],
        propAt: { x: 880 },
      };
    case "cheer":
      return {
        keys: [
          { f: 0, p: {} },
          { f: 5, p: CROUCH },
          { f: 11, p: { ...P.cheer, y: HIP - 70 * S, lean: 0, ll1: -20, ll2: 40, rl1: 20, rl2: 40 } },
          { f: 18, p: { y: HIP, ...LEGS }, e: Easing.in(Easing.quad) },
        ],
        mod: (t, p) => (t > 22 ? addPose(p, { la1: Math.sin(t * 0.3) * 12, ra1: -Math.sin(t * 0.3) * 12, y: -Math.abs(Math.sin(t * 0.3)) * 10 }) : p),
        face: "happy",
        over: (
          <>
            <Dust x={CX} y={GROUND} at={18} f={f} />
            <Confetti f={f} from={12} />
          </>
        ),
        hits: [18],
        propAt: { x: 870 },
      };
    case "point":
      return {
        keys: [{ f: 0, p: {} }, { f: 6, p: { ra1: 140, ra2: -5, la1: -20, la2: 10, head: -12 } }],
        mod: (t, p) => addPose(p, { ...idle(t), ra1: Math.sin(t * 0.3) * 4 }),
        face: "happy",
        hits: [],
        propAt: { x: 190 },
      };
    case "shrug": {
      const keys: Key[] = [{ f: 0, p: {} }];
      for (let k = 6; k < dur; k += 32) keys.push({ f: k, p: P.shrug }, { f: k + 16, p: ARMS });
      return { keys, mod: breathe(), face: "eyes", hits: [], propAt: { x: 880 } };
    }
    case "facepalm":
      return {
        keys: [{ f: 0, p: {} }, { f: 8, p: P.facepalm }],
        mod: (t, p) => (t > 12 ? addPose(p, { head: Math.sin(t * 0.45) * 6 }) : p),
        face: "sad",
        hits: [8],
        propAt: { x: 880 },
      };
    case "shock":
      return {
        keys: [
          { f: 0, p: {} },
          { f: 5, p: { ...P.shock, x: CX - 50 * S, y: HIP - 40 * S } },
          { f: 11, p: { y: HIP }, e: Easing.in(Easing.quad) },
        ],
        mod: (t, p) => (t > 14 ? addPose(p, { x: Math.sin(t * 2.1) * 3 }) : p),
        face: "eyes",
        hold: (j) => (
          <At x={j.headC[0] + 90} y={j.headC[1] - 90} r={12}>
            <Mark text="!" t={ease(f, 5, 12)} />
          </At>
        ),
        over: <Burst x={CX - 50 * S} y={HIP - 330} at={5} f={f} size={170} />,
        hits: [5],
        propAt: { x: 860 },
      };
    case "run":
      return {
        keys: [{ f: 0, p: {} }],
        mod: (t, p) => addPose(p, { ...runCycle(t, 0.5), y: -Math.abs(Math.sin(t * 0.5)) * 10 * S }),
        face: "angry",
        under: <SpeedLines f={f} top={GROUND - 560} bottom={GROUND - 30} />,
        hits: [],
        propAt: { x: 880 },
      };
    case "scroll_phone":
      return {
        keys: [{ f: 0, p: SIT }, { f: 6, p: { ...SIT, la1: 50, la2: 60, ra1: 70, ra2: 40, head: -18 } }],
        mod: breathe(),
        face: "eyes",
        under: (
          <At x={CX - 10} y={SIT_Y + 18}>
            <Stool />
          </At>
        ),
        hold: (j) => {
          const [x, y] = mid(j);
          return (
            <At x={x + 4} y={y - 36} s={S * 0.8} r={-12}>
              <Phone f={f} />
            </At>
          );
        },
        hits: [],
        propAt: { x: 200 },
      };
    case "read":
      return {
        keys: [{ f: 0, p: SIT }, { f: 6, p: { ...SIT, la1: 50, la2: 60, ra1: 70, ra2: 40, head: -14 } }],
        mod: breathe(),
        face: "happy",
        under: (
          <At x={CX - 10} y={SIT_Y + 18}>
            <Stool />
          </At>
        ),
        hold: (j) => {
          const [x, y] = mid(j);
          return (
            <>
              <At x={x + 6} y={y - 30} s={S * 0.75} r={-8}>
                <Book f={f} />
              </At>
              {[0, 1, 2].map((i) => {
                const d = (f + i * 20) % 60;
                return (
                  <At key={i} x={j.headC[0] - 60 + i * 60} y={j.headC[1] - 90 - d * 2} o={d < 45 ? 1 - d / 45 : 0}>
                    <text textAnchor="middle" fontFamily={FONT.hindi} fontWeight={800} fontSize={54} fill={COL.green}>+</text>
                  </At>
                );
              })}
            </>
          );
        },
        hits: [],
        propAt: { x: 200 },
      };
    case "fall_getup": {
      const trip = Math.max(10, Math.round(dur * 0.22));
      const rise = Math.max(trip + 14, Math.round(dur * 0.5));
      return {
        keys: [
          { f: 0, p: { x: CX - 160 } },
          { f: trip, p: { x: CX - 20, lean: 20 }, e: (t) => t },
          { f: trip + 6, p: { rot: 86, y: GROUND - 14 * S, x: CX - 60, la1: -170, la2: 0, ra1: 170, ra2: 0, ll1: -5, ll2: 0, rl1: 5, rl2: 0, lean: 0 }, e: Easing.in(Easing.quad) },
          { f: rise, p: {} },
          { f: rise + 10, p: { ...CROUCH, rot: 0, x: CX }, e: SMOOTH },
          { f: rise + 22, p: { y: HIP, lean: 0, ...LEGS, ...ARMS } },
          { f: rise + 30, p: { ra1: 150, ra2: 40, la1: -18 } },
        ],
        mod: (t, p) => (t < trip ? addPose(p, walkCycle(t, 0.3)) : t > rise + 30 ? addPose(p, idle(t)) : p),
        face: f < trip ? "eyes" : f < rise ? "sad" : f < rise + 28 ? "angry" : "happy",
        over: (
          <>
            <Dust x={CX + 80} y={GROUND} at={trip + 6} f={f} spread={220} />
            <Burst x={CX + 200} y={GROUND - 60} at={trip + 6} f={f} size={120} />
          </>
        ),
        hits: [trip + 6],
        propAt: { x: 900 },
      };
    }
    case "carry_burden":
      return {
        keys: [{ f: 0, p: {} }, { f: 8, p: { ...P.carry, ll1: -18, ll2: 25, rl1: 18, rl2: -20 } }],
        mod: (t, p) => addPose(p, { lean: Math.sin(t * 0.15) * 6, y: Math.sin(t * 0.3) * 3 * S }),
        face: "sad",
        hold: (j) => {
          const [x, y] = mid(j);
          const r = Math.sin(f * 0.15) * 6;
          return (
            <At x={x} y={y - 70} r={r}>
              <Box w={200} h={110} color="#c98b52" />
              <At x={10} y={-92} r={-4}>
                <Box w={140} h={80} color="#d9a066" />
              </At>
            </At>
          );
        },
        hits: [],
        propAt: { x: 900 },
      };
    case "climb": {
      const n = 4,
        sw = 110,
        sh = 60,
        x0 = 290;
      const step = Math.max(10, Math.floor((dur * 0.75) / n));
      const keys: Key[] = [{ f: 0, p: { x: x0 - 100 } }];
      for (let i = 1; i <= n; i++) keys.push({ f: 6 + i * step, p: { x: x0 + (i - 0.5) * sw, y: HIP - i * sh }, e: SMOOTH });
      const top = 6 + n * step;
      keys.push({ f: top + 6, p: P.armsUp });
      return {
        keys,
        mod: (t, p) => (t < top ? addPose(p, walkCycle(t, 0.32)) : addPose(p, idle(t))),
        face: f < top ? "eyes" : "happy",
        under: (
          <At x={x0} y={GROUND}>
            <Stairs n={n} w={sw} h={sh} />
          </At>
        ),
        hits: [],
        propAt: { x: 930 },
      };
    }
    case "handshake": {
      const w = Math.min(Math.round(dur * 0.45), 40);
      const walk = (from: number, to: number): Key[] => [
        { f: 0, p: { x: from } },
        { f: w, p: { x: to }, e: (t) => t },
        { f: w + 6, p: P.handshake },
      ];
      const steps = (t: number, p: Pose) => (t < w ? addPose(p, walkCycle(t, 0.3)) : addPose(p, { ...idle(t), ra2: t > w + 6 && t < w + 30 ? Math.sin(t * 0.8) * 10 : 0 }));
      return {
        keys: walk(-170, 380),
        mod: steps,
        face: "happy",
        second: { keys: walk(W + 170, 700), mod: steps, face: "happy", facing: -1, color: COL.blue },
        over: (
          <>
            <Burst x={CX} y={HIP - 150} at={w + 6} f={f} size={110} color={COL.orange} />
            <At x={CX} y={HIP - 330 - ease(f, w + 8, w + 30) * 30} o={ease(f, w + 8, w + 16)}>
              <Heart f={f} s={1.2} />
            </At>
          </>
        ),
        hits: [w + 6],
        propAt: null,
      };
    }
    default:
      return act("point", f, dur);
  }
};

// The beat's prop, standing on the ground (or hanging in the air) at x
export const PropView: React.FC<{ prop: string; x: number; f: number; dur: number; head?: [number, number] }> = ({ prop, x, f, dur, head }) => {
  const o = ease(f, 4, 14);
  const pop = ease(f, 4, 14, 0.4, 1);
  switch (prop) {
    case "clock":
      return <At x={x} y={GROUND - 470} s={1.4 * pop} o={o}><Clock f={f} /></At>;
    case "coin":
      return <At x={x} y={GROUND - 420 + Math.sin(f * 0.12) * 14} s={1.3 * pop} o={o}><Coin f={f} /></At>;
    case "heart":
      return <At x={x} y={GROUND - 450} s={1.3 * pop} o={o}><Heart f={f} /></At>;
    case "trophy":
      return <At x={x} y={GROUND - 92} s={1.3 * pop} o={o}><Trophy f={f} /></At>;
    case "plant":
      return <At x={x} y={GROUND - 80} s={1.3} o={o}><Plant grow={ease(f, 6, Math.max(20, dur * 0.8), 0.15, 1, (t) => t)} /></At>;
    case "mountain":
      return <At x={x} y={GROUND} s={1} o={o}><Mountain f={f} /></At>;
    case "rain_cloud":
      if (!head) return null;
      // above the head, or beside it when the head is high (stairs) so the cloud never covers the caption
      return head[1] - 260 >= 640
        ? <At x={head[0]} y={head[1] - 260} s={1.3 * pop} o={o}><RainCloud f={f} /></At>
        : <At x={Math.min(W - 150, head[0] + 240)} y={head[1] - 110} s={1.1 * pop} o={o}><RainCloud f={f} /></At>;
    default:
      return null;
  }
};
