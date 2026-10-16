import React from "react";
import { Easing, interpolate } from "remotion";
import { Burst, COL, Dust, FONT, SpeedLines, ease } from "./engine/fx";
import { At, Book, Box, Bulb, Clock, Coin, Heart, Mountain, Phone, Plant, RainCloud, Stairs, Stool, Thought, Trophy } from "./engine/props";
import { Accessory, Joints, Key, P, Pose, SMOOTH, STAND, addPose, idle, runCycle, walkCycle } from "./engine/stick";

// The stage: a 1080x1920 world, ground line at GROUND, the hero at scale S with the hip at HIP.
export const W = 1080;
export const H = 1920;
export const GROUND = 1300;
export const S = 2.2;
export const HIP = STAND.y;
export const CX = STAND.x;
export const hipFor = (scale: number) => GROUND - 92.5 * scale;

export type Face = "eyes" | "happy" | "sad" | "angry";
export type Sfx = [number, string, number?]; // [frame in the beat, sfx/<name>.wav, volume]

// Who the other person is: colour, accessory, size and the Hindi label shown above the head
export type Cast = { color: string; accessory: Accessory; label: string; scale: number };
export const CAST: Record<string, Cast> = {
  friend: { color: COL.blue, accessory: "none", label: "दोस्त", scale: S },
  mother: { color: COL.purple, accessory: "scarf", label: "माँ", scale: S * 0.95 },
  father: { color: COL.green, accessory: "glasses", label: "पापा", scale: S },
  boss: { color: "#555b66", accessory: "tie", label: "बॉस", scale: S * 1.05 },
  partner: { color: COL.red, accessory: "none", label: "पार्टनर", scale: S * 0.97 },
  child: { color: COL.orange, accessory: "cap", label: "बच्चा", scale: S * 0.62 },
  stranger: { color: COL.grey, accessory: "none", label: "अजनबी", scale: S },
};
export const HERO = { color: COL.ink, accessory: "cap" as Accessory };

export type Figure = {
  keys: Key[];
  mod?: (t: number, p: Pose) => Pose;
  face: Face;
  facing?: number | ((t: number) => number);
  hold?: (j: Joints) => React.ReactNode; // drawn with the figure, positioned from its joints
  base?: Partial<Pose>;
};
export type Act = Figure & {
  under?: React.ReactNode; // world drawings behind the figures (stairs, bed, desk, speed lines)
  over?: React.ReactNode; // effects in front (bursts, dust, confetti)
  hits: number[]; // camera shake and punch-in frames
  sfx: Sfx[];
  second?: Figure; // the other person in a two-person action
  propAt?: { x: number } | null; // where the beat's prop goes (null: no room for one)
  watcherAt?: number | null; // x where a watching cast member may stand (null: no room)
};

const ARMS = { la1: -18, la2: 8, ra1: 18, ra2: -8, head: 0 }; // arms back at rest
const LEGS = { ll1: -12, ll2: 4, rl1: 12, rl2: -4 };
const SIT_Y = HIP + 40 * S;
const SIT = { y: SIT_Y, ll1: 80, ll2: -80, rl1: 95, rl2: -85, lean: -5 };
const CROUCH = { y: HIP + 30 * S, ll1: -60, ll2: 95, rl1: 50, rl2: 90, lean: 10, la1: -40, la2: -30, ra1: 40, ra2: 30 };
const LIE = (x: number, scale = S) => ({ rot: 86, y: GROUND - 14 * scale, x, la1: -170, la2: 0, ra1: 170, ra2: 0, ll1: -5, ll2: 0, rl1: 5, rl2: 0, lean: 0 });
const SHOUT = { lean: 14, head: -10, ra1: 100, ra2: -20, la1: -40, la2: -110 };
const breathe = (seed = 0) => (t: number, p: Pose) => addPose(p, idle(t, seed));
const mid = (j: Joints) => [(j.lHand[0] + j.rHand[0]) / 2, (j.lHand[1] + j.rHand[1]) / 2] as const;
const linear = (t: number) => t;
const walkTo = (t: number, until: number, p: Pose, speed = 0.3) => (t < until ? addPose(p, walkCycle(t, speed)) : addPose(p, idle(t)));

const Mark: React.FC<{ text: string; t: number; color?: string; size?: number }> = ({ text, t, color = COL.red, size = 140 }) =>
  t <= 0 ? null : (
    <text textAnchor="middle" fontFamily={FONT.hindi} fontWeight={800} fontSize={size * Math.min(1, t * 1.3)} fill={color} stroke="#fff" strokeWidth={10} paintOrder="stroke">
      {text}
    </text>
  );

// jagged shout bubble with scribbled swearing
const Shout: React.FC<{ t: number; text?: string; flip?: boolean }> = ({ t, text = "#@!", flip }) => {
  if (t <= 0) return null;
  const pts = Array.from({ length: 16 }).map((_, i) => {
    const a = (i / 16) * Math.PI * 2;
    const r = i % 2 ? 70 : 100;
    return `${Math.cos(a) * r * 1.35},${Math.sin(a) * r}`;
  });
  return (
    <g transform={`scale(${(flip ? -1 : 1) * t} ${t})`}>
      <polygon points={pts.join(" ")} fill="#fff" stroke={COL.red} strokeWidth={8} strokeLinejoin="round" />
      <text y={22} textAnchor="middle" fontFamily={FONT.hindi} fontWeight={800} fontSize={62} fill={COL.red} transform={flip ? "scale(-1 1)" : undefined}>
        {text}
      </text>
    </g>
  );
};

const Steam: React.FC<{ f: number; x: number; y: number }> = ({ f, x, y }) => (
  <g>
    {[0, 1, 2].map((i) => {
      const d = (f * 1.4 + i * 22) % 66;
      return <circle key={i} cx={x + (i - 1) * 50 + Math.sin(d * 0.2) * 10} cy={y - d * 2.2} r={14 + d * 0.5} fill="#d9d9d9" opacity={1 - d / 66} />;
    })}
  </g>
);

const Tears: React.FC<{ f: number; x: number; y: number }> = ({ f, x, y }) => (
  <g>
    {[0, 1, 2, 3].map((i) => {
      const d = (f * 2 + i * 13) % 52;
      const side = i % 2 ? 1 : -1;
      return <path key={i} d={`M${x + side * 18},${y + d * 3} q-8,14 0,20 q8,-6 0,-20 Z`} fill={COL.blue} opacity={1 - d / 52} />;
    })}
  </g>
);

const Zzz: React.FC<{ f: number; x: number; y: number }> = ({ f, x, y }) => (
  <g>
    {[0, 1, 2].map((i) => {
      const d = (f + i * 18) % 54;
      return (
        <text key={i} x={x + d * 1.4} y={y - d * 2.4} fontFamily={FONT.hindi} fontWeight={800} fontSize={40 + i * 12} fill={COL.blue} opacity={1 - d / 54}>
          Z
        </text>
      );
    })}
  </g>
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

const Bed: React.FC<{ x: number; top: number }> = ({ x, top }) => (
  <g>
    <rect x={x - 300} y={top} width={600} height={GROUND - top} rx={10} fill="#b07a4f" stroke={COL.ink} strokeWidth={6} />
    <rect x={x - 300} y={top - 26} width={600} height={34} rx={14} fill="#f4f1ea" stroke={COL.ink} strokeWidth={5} />
    <rect x={x - 290} y={top - 64} width={130} height={46} rx={20} fill="#fff" stroke={COL.ink} strokeWidth={5} />
    <rect x={x - 330} y={top - 160} width={40} height={GROUND - top + 160} rx={8} fill="#8a5a3b" stroke={COL.ink} strokeWidth={6} />
  </g>
);

const Desk: React.FC<{ x: number; f: number }> = ({ x, f }) => {
  const top = GROUND - 170;
  return (
    <g>
      <rect x={x} y={top} width={330} height={22} fill="#8a6a4f" stroke={COL.ink} strokeWidth={6} />
      <line x1={x + 20} y1={top + 22} x2={x + 20} y2={GROUND} stroke={COL.ink} strokeWidth={10} />
      <line x1={x + 310} y1={top + 22} x2={x + 310} y2={GROUND} stroke={COL.ink} strokeWidth={10} />
      <polygon points={`${x + 60},${top} ${x + 200},${top} ${x + 226},${top - 110} ${x + 86},${top - 110}`} fill="#3a3f4b" stroke={COL.ink} strokeWidth={5} />
      <polygon points={`${x + 74},${top - 10} ${x + 190},${top - 10} ${x + 212},${top - 100} ${x + 96},${top - 100}`} fill="#8fd3ff" opacity={0.7 + Math.sin(f * 0.3) * 0.15} />
      <line x1={x + 280} y1={top} x2={x + 280} y2={top - 150} stroke={COL.ink} strokeWidth={7} />
      <path d={`M${x + 280},${top - 150} L${x + 230},${top - 170} L${x + 250},${top - 120} Z`} fill={COL.yellow} stroke={COL.ink} strokeWidth={5} />
      <polygon points={`${x + 240},${top - 140} ${x + 120},${top} ${x + 290},${top}`} fill="#fff3b0" opacity={0.35} />
      <rect x={x + 250} y={top - 46} width={30} height={46} rx={5} fill="#fff" stroke={COL.ink} strokeWidth={4} />
    </g>
  );
};

const two = (other: Cast | undefined) => other ?? CAST.friend;

export const act = (action: string, f: number, dur: number, other?: Cast): Act => {
  switch (action) {
    case "walk_in": {
      const w = Math.min(Math.round(dur * 0.55), 50);
      return {
        keys: [{ f: 0, p: { x: -170 } }, { f: w, p: { x: CX }, e: linear }, { f: w + 8, p: { ra1: 150, ra2: -20 } }],
        mod: (t, p) => (t < w ? addPose(p, walkCycle(t, 0.3)) : addPose(p, { ...idle(t), ra2: t > w + 8 ? Math.sin(t * 0.45) * 28 : 0 })),
        face: f > w ? "happy" : "eyes",
        hits: [],
        sfx: [[w + 6, "pop", 0.5]],
        propAt: { x: 880 },
        watcherAt: 880,
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
        sfx: [[10, "pop", 0.6]],
        propAt: { x: 170 },
        watcherAt: 160,
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
        sfx: [[at, "ding", 0.8]],
        propAt: { x: 880 },
        watcherAt: 880,
      };
    }
    case "sad":
      return {
        keys: [{ f: 0, p: {} }, { f: 14, p: P.sad, e: SMOOTH }],
        mod: (t, p) => addPose(p, { ...idle(t), lean: Math.sin(t * 0.05) * 2 }),
        face: "sad",
        hits: [],
        sfx: [[4, "sad", 0.45]],
        propAt: { x: 880 },
        watcherAt: 880,
      };
    case "cry": {
      const sitY = GROUND - 14 * S;
      return {
        keys: [{ f: 0, p: {} }, { f: 10, p: { y: sitY, ll1: 125, ll2: -150, rl1: 135, rl2: -150, lean: 25, head: 30, la1: 120, la2: 40, ra1: 130, ra2: 40 }, e: SMOOTH }],
        mod: (t, p) => (t > 12 ? addPose(p, { y: Math.sin(t * 0.9) * 3, head: Math.sin(t * 0.9) * 2 }) : p),
        face: "sad",
        hold: (j) => (f > 12 ? <Tears f={f} x={j.headC[0] + 10} y={j.headC[1] + 6} /> : null),
        hits: [],
        sfx: [[6, "sad", 0.5]],
        propAt: { x: 880 },
        watcherAt: 860,
      };
    }
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
        sfx: [[5, "swoosh_up", 0.5], [16, "tada", 0.8]],
        propAt: { x: 870 },
        watcherAt: 180,
      };
    case "point":
      return {
        keys: [{ f: 0, p: {} }, { f: 6, p: { ra1: 140, ra2: -5, la1: -20, la2: 10, head: -12 } }],
        mod: (t, p) => addPose(p, { ...idle(t), ra1: Math.sin(t * 0.3) * 4 }),
        face: "happy",
        hits: [],
        sfx: [[6, "pop", 0.5]],
        propAt: { x: 190 },
        watcherAt: 190,
      };
    case "shrug": {
      const keys: Key[] = [{ f: 0, p: {} }];
      for (let k = 6; k < dur; k += 32) keys.push({ f: k, p: P.shrug }, { f: k + 16, p: ARMS });
      return { keys, mod: breathe(), face: "eyes", hits: [], sfx: [[6, "pop", 0.4]], propAt: { x: 880 }, watcherAt: 880 };
    }
    case "facepalm":
      return {
        keys: [{ f: 0, p: {} }, { f: 8, p: P.facepalm }],
        mod: (t, p) => (t > 12 ? addPose(p, { head: Math.sin(t * 0.45) * 6 }) : p),
        face: "sad",
        hits: [8],
        sfx: [[8, "thud", 0.35]],
        propAt: { x: 880 },
        watcherAt: 880,
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
        sfx: [[3, "whoosh", 0.6], [5, "thud", 0.6]],
        propAt: { x: 860 },
        watcherAt: 870,
      };
    case "angry":
      return {
        keys: [
          { f: 0, p: {} },
          { f: 5, p: { lean: 10, la1: -60, la2: -100, ra1: 60, ra2: 100, ll1: -24, rl1: 26, y: HIP + 8 } },
          { f: 12, p: { lean: -6, head: -12, la1: -45, la2: -125, ra1: 45, ra2: 125, y: HIP } },
        ],
        mod: (t, p) => (t > 12 ? addPose(p, { x: Math.sin(t * 1.6) * 4, head: Math.sin(t * 0.9) * 4 }) : p),
        face: "angry",
        hold: (j) => (
          <>
            {f > 8 && <Steam f={f} x={j.headC[0]} y={j.headC[1] - 70} />}
            <At x={j.headC[0] + 230} y={j.headC[1] - 120} r={-6}>
              <Shout t={ease(f, 12, 18)} />
            </At>
          </>
        ),
        over: <Dust x={CX} y={GROUND} at={5} f={f} />,
        hits: [5, 12],
        sfx: [[5, "thud", 0.5], [12, "angry", 0.6]],
        propAt: { x: 170 },
        watcherAt: 170,
      };
    case "run":
      return {
        keys: [{ f: 0, p: {} }],
        mod: (t, p) => addPose(p, { ...runCycle(t, 0.5), y: -Math.abs(Math.sin(t * 0.5)) * 10 * S }),
        face: "angry",
        under: <SpeedLines f={f} top={GROUND - 560} bottom={GROUND - 30} />,
        hits: [],
        sfx: [[0, "whoosh", 0.6]],
        propAt: { x: 880 },
        watcherAt: null,
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
        sfx: [[6, "pop", 0.4]],
        propAt: { x: 200 },
        watcherAt: 190,
      };
    case "sleep_alarm": {
      const top = GROUND - 120;
      const ring = Math.max(12, Math.round(dur * 0.3));
      const up = Math.max(ring + 14, Math.round(dur * 0.55));
      const bedX = CX - 40;
      const lying = { ...LIE(CX + 60), rot: -90, y: top - 30, la1: -20, ra1: 20 };
      return {
        keys: [
          { f: 0, p: lying },
          { f: up, p: lying },
          { f: up + 8, p: { rot: 0, x: CX + 120, y: top - 10, ll1: 80, ll2: -80, rl1: 95, rl2: -85, lean: -5, ...ARMS }, e: SMOOTH },
          { f: up + 18, p: P.armsUp },
        ],
        mod: (t, p) => (t > up + 18 ? addPose(p, { la1: Math.sin(t * 0.25) * 8, ra1: -Math.sin(t * 0.25) * 8 }) : t < ring ? addPose(p, { y: Math.sin(t * 0.15) * 3 }) : p),
        face: f < up ? "sad" : "happy",
        under: <Bed x={bedX} top={top} />,
        hold: (j) => (f < ring ? <Zzz f={f} x={j.headC[0] + 30} y={j.headC[1] - 50} /> : null),
        over: (
          <>
            <At x={900} y={GROUND - 260 + (f > ring && f < up ? Math.sin(f * 2.5) * 6 : 0)} s={1.1} r={f > ring && f < up ? Math.sin(f * 3) * 10 : 0}>
              <Clock f={f} r={58} />
            </At>
            {f > ring && f < up && <At x={900} y={GROUND - 380}><Mark text="!!" t={1} size={90} /></At>}
          </>
        ),
        hits: [ring, up],
        sfx: [[ring, "alarm", 0.55], [up, "swoosh_up", 0.5]],
        propAt: null,
        watcherAt: null,
      };
    }
    case "workout":
      return {
        keys: [{ f: 0, p: {} }, { f: 6, p: { la1: 80, la2: -10, ra1: 95, ra2: -10 } }],
        mod: (t, p) => {
          const k = t < 6 ? 0 : (1 - Math.cos((t - 6) * 0.26)) / 2;
          return addPose(p, { y: 66 * k, ll1: -48 * k, ll2: 91 * k, rl1: 38 * k, rl2: 94 * k, lean: 10 * k });
        },
        face: "angry",
        hold: (j) => {
          const [x, y] = mid(j);
          const reps = Math.max(0, Math.floor((f - 6) / 24));
          return (
            <>
              <g transform={`translate(${x} ${y})`}>
                <rect x={-70} y={-9} width={140} height={18} rx={6} fill="#555" />
                <rect x={-92} y={-34} width={26} height={68} rx={6} fill={COL.ink} />
                <rect x={66} y={-34} width={26} height={68} rx={6} fill={COL.ink} />
              </g>
              {reps > 0 && (
                <At x={j.headC[0]} y={j.headC[1] - 120}>
                  <Mark text={String(reps)} t={ease((f - 6) % 24, 0, 6)} color={COL.green} size={90} />
                </At>
              )}
              <path d={`M${j.headC[0] - 50},${j.headC[1] - 10 + ((f * 3) % 40)} q-6,12 0,16 q6,-4 0,-16 Z`} fill={COL.blue} opacity={0.8} />
            </>
          );
        },
        hits: [],
        sfx: [[18, "pop", 0.35], [42, "pop", 0.35], [66, "pop", 0.35]],
        propAt: { x: 880 },
        watcherAt: 880,
      };
    case "work_late":
      return {
        keys: [{ f: 0, p: { ...SIT, x: CX - 130, la1: 60, la2: -5, ra1: 75, ra2: -15, head: -6 } }],
        mod: (t, p) => addPose(p, { la2: Math.sin(t * 1.3) * 8, ra2: Math.cos(t * 1.1) * 8, head: Math.sin(t * 0.05) * 4 }),
        face: "eyes",
        under: (
          <>
            <At x={CX - 140} y={SIT_Y + 18}>
              <Stool />
            </At>
            <Desk x={CX + 10} f={f} />
          </>
        ),
        hits: [],
        sfx: [[0, "tick", 0.35]],
        propAt: { x: 140 },
        watcherAt: null,
      };
    case "count_money": {
      const every = 12;
      const coins = Math.max(0, Math.min(9, Math.floor((f - 6) / every)));
      return {
        keys: [{ f: 0, p: {} }, { f: 6, p: { ra1: 60, ra2: 30, head: 12 } }],
        mod: (t, p) => addPose(p, { ra1: t > 6 ? Math.sin(((t - 6) / every) * Math.PI * 2) * 18 : 0 }),
        face: "happy",
        under: (
          <At x={CX + 210} y={GROUND - 60}>
            <Box w={150} h={120} color="#c98b52" />
          </At>
        ),
        over: (
          <g>
            {Array.from({ length: coins }).map((_, i) => (
              <ellipse key={i} cx={CX + 210 + (i % 2) * 6} cy={GROUND - 130 - i * 16} rx={46} ry={14} fill={COL.gold} stroke={COL.ink} strokeWidth={4} />
            ))}
            <At x={CX + 210} y={GROUND - 300 - coins * 16}>
              <Mark text="₹" t={coins > 0 ? 1 : 0} color={COL.gold} size={80} />
            </At>
          </g>
        ),
        hits: [],
        sfx: Array.from({ length: 6 }).map((_, i) => [6 + every * (i + 1), "pop", 0.3] as Sfx),
        propAt: { x: 170 },
        watcherAt: 170,
      };
    }
    case "fall_getup": {
      const trip = Math.max(10, Math.round(dur * 0.22));
      const rise = Math.max(trip + 14, Math.round(dur * 0.5));
      return {
        keys: [
          { f: 0, p: { x: CX - 160 } },
          { f: trip, p: { x: CX - 20, lean: 20 }, e: linear },
          { f: trip + 6, p: LIE(CX - 60), e: Easing.in(Easing.quad) },
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
        sfx: [[trip + 6, "thud", 0.8], [rise + 8, "swoosh_up", 0.5]],
        propAt: { x: 900 },
        watcherAt: null,
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
        hits: [8],
        sfx: [[8, "thud", 0.45]],
        propAt: { x: 900 },
        watcherAt: 880,
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
        sfx: [...Array.from({ length: n }).map((_, i) => [6 + (i + 1) * step - 2, "pop", 0.35] as Sfx), [top + 6, "ding", 0.6]],
        propAt: { x: 930 },
        watcherAt: null,
      };
    }
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
        sfx: [[6, "pop", 0.35]],
        propAt: { x: 200 },
        watcherAt: 190,
      };
    case "walk_away": {
      const w = Math.max(16, Math.round(dur * 0.45));
      return {
        keys: [{ f: 0, p: {} }, { f: w, p: { x: CX + 280 }, e: linear }, { f: w + 8, p: { head: 10, ra1: 40, ra2: 20 } }],
        mod: (t, p) => walkTo(t, w, p, 0.28),
        facing: (t) => (t < w + 4 ? 1 : -1),
        face: f < w ? "eyes" : "sad",
        hits: [],
        sfx: [[w + 4, "whoosh", 0.35]],
        propAt: { x: 180 },
        watcherAt: 170,
      };
    }
    case "handshake": {
      const o = two(other);
      const w = Math.min(Math.round(dur * 0.45), 40);
      const walk = (from: number, to: number, hip: number): Key[] => [
        { f: 0, p: { x: from, y: hip } },
        { f: w, p: { x: to }, e: linear },
        { f: w + 6, p: P.handshake },
      ];
      const steps = (t: number, p: Pose) => (t < w ? addPose(p, walkCycle(t, 0.3)) : addPose(p, { ...idle(t), ra2: t > w + 6 && t < w + 30 ? Math.sin(t * 0.8) * 10 : 0 }));
      return {
        keys: walk(-170, 380, HIP),
        mod: steps,
        face: "happy",
        second: { keys: walk(W + 170, 700, hipFor(o.scale)), mod: steps, face: "happy", facing: -1 },
        over: (
          <>
            <Burst x={CX} y={HIP - 150} at={w + 6} f={f} size={110} color={COL.orange} />
            <At x={CX} y={HIP - 330 - ease(f, w + 8, w + 30) * 30} o={ease(f, w + 8, w + 16)}>
              <Heart f={f} s={1.2} />
            </At>
          </>
        ),
        hits: [w + 6],
        sfx: [[w + 6, "pop", 0.7], [w + 10, "ding", 0.4]],
        propAt: null,
        watcherAt: null,
      };
    }
    case "argue": {
      const o = two(other);
      const keys: Key[] = [{ f: 0, p: { x: 390 } }];
      const theirs: Key[] = [{ f: 0, p: { x: 700, y: hipFor(o.scale) } }];
      const turns: number[] = [];
      for (let k = 4, i = 0; k < dur - 6; k += 20, i++) {
        turns.push(k);
        (i % 2 ? theirs : keys).push({ f: k, p: SHOUT }, { f: k + 14, p: { ...ARMS, lean: 0 } });
      }
      const loud = (mine: boolean) => turns.some((k, i) => (i % 2 === (mine ? 0 : 1)) && f >= k && f < k + 16);
      return {
        keys,
        mod: (t, p) => addPose(p, { x: Math.sin(t * 1.4) * 2 }),
        face: "angry",
        hold: (j) => (loud(true) ? <At x={j.headC[0] + 60} y={j.headC[1] - 200} r={-8}><Shout t={1} text="!!" /></At> : null),
        second: {
          keys: theirs,
          mod: (t, p) => addPose(p, { x: Math.sin(t * 1.3) * 2 }),
          face: "angry",
          facing: -1,
          hold: (j) => (loud(false) ? <At x={j.headC[0] - 60} y={j.headC[1] - 200} r={8}><Shout t={1} text="#@!" flip /></At> : null),
        },
        hits: turns,
        sfx: turns.map((k) => [k, "angry", 0.45] as Sfx),
        propAt: null,
        watcherAt: null,
      };
    }
    case "hug": {
      const o = two(other);
      const w = Math.min(Math.round(dur * 0.4), 34);
      const hug = { ra1: 95, ra2: 75, la1: 70, la2: 90, head: 8, lean: 6 };
      return {
        keys: [{ f: 0, p: { x: 280 } }, { f: w, p: { x: 470 }, e: linear }, { f: w + 6, p: hug }],
        mod: (t, p) => (t < w ? addPose(p, walkCycle(t, 0.3)) : addPose(p, { y: Math.sin(t * 0.2) * 2 })),
        face: "happy",
        second: {
          keys: [{ f: 0, p: { x: 800, y: hipFor(o.scale) } }, { f: w, p: { x: 600 }, e: linear }, { f: w + 6, p: hug }],
          mod: (t, p) => (t < w ? addPose(p, walkCycle(t, 0.3)) : p),
          face: "happy",
          facing: -1,
        },
        over: (
          <>
            {[0, 1, 2].map((i) => (
              <At key={i} x={CX - 60 + i * 60} y={HIP - 380 - ((f - w - i * 8) * 3)} o={f > w + i * 8 ? Math.max(0, 1 - (f - w - i * 8) / 40) : 0}>
                <Heart f={f} s={0.5} />
              </At>
            ))}
          </>
        ),
        hits: [w + 6],
        sfx: [[w + 6, "pop", 0.6], [w + 10, "heartbeat", 0.5]],
        propAt: null,
        watcherAt: null,
      };
    }
    case "help_up": {
      const o = two(other);
      const at = Math.max(16, Math.round(dur * 0.4));
      const lyingX = CX + 30;
      return {
        keys: [{ f: 0, p: { x: CX - 190 } }, { f: 8, p: { lean: 18, ra1: 110, ra2: -10 } }, { f: at, p: {} }, { f: at + 12, p: { lean: -10, ra1: 80 } }, { f: at + 24, p: { ...ARMS, lean: 0 } }],
        mod: breathe(),
        face: f < at ? "eyes" : "happy",
        second: {
          keys: [
            { f: 0, p: { ...LIE(lyingX, o.scale), rot: -86, la1: -170, ra1: 170 } },
            { f: at, p: { ...LIE(lyingX, o.scale), rot: -86, la1: -100, ra1: 120 } },
            { f: at + 12, p: { ...CROUCH, y: hipFor(o.scale) + 30 * o.scale, rot: 0, x: CX + 120 }, e: SMOOTH },
            { f: at + 24, p: { y: hipFor(o.scale), lean: 0, ...LEGS, ...ARMS } },
          ],
          face: f < at + 12 ? "sad" : "happy",
          facing: -1,
          mod: (t, p) => (t > at + 24 ? addPose(p, idle(t, 2)) : p),
        },
        over: <Burst x={CX - 10} y={HIP - 120} at={at + 12} f={f} size={110} color={COL.orange} />,
        hits: [at + 12],
        sfx: [[at, "swoosh_up", 0.5], [at + 14, "ding", 0.5]],
        propAt: null,
        watcherAt: null,
      };
    }
    default:
      return act("point", f, dur, other);
  }
};

// A cast member who watches a one-person beat from the side and reacts to its mood
export const watcher = (x: number, mood: string | undefined): Figure => ({
  keys: [{ f: 0, p: { x } }, { f: 10, p: mood === "sad" ? P.sad : mood === "happy" ? { ...P.cheer, la1: -120, ra1: 120 } : mood === "tense" ? P.shock : P.think }],
  mod: breathe(3),
  face: mood === "sad" ? "sad" : mood === "happy" ? "happy" : mood === "tense" ? "eyes" : "eyes",
  facing: x > CX ? -1 : 1,
});

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

export const interpolateClamp = (f: number, a: number[], b: number[]) => interpolate(f, a, b, { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
