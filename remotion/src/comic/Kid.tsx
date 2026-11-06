import React from "react";
import { Easing, interpolate, random } from "remotion";
import { onInk } from "./ink";

// The comic Reels' star (reel/comic.py): our own cartoon kid, drawn for the cartoon-meme look of viral Hindi
// Reels. A big round head with huge white eyes that do the acting, thick eyebrows, a small talking mouth, a
// saffron T-shirt (the Seekh Sketch colour), and the upper body only: the kid sits behind a table (rooms.tsx).
// A boy has a spiky tuft of hair; a girl has a ponytail and a bow. The same drawing, with other hair, colours and
// accessories (TOONS), plays the people in the kid's life: मम्मी, पापा, सर, the boss and a friend.
//
// Everything is drawn in stage space (1080x1920). The head is centred at HEAD, the shoulders sit at y 1110 and
// the table top at TABLE (rooms.tsx), so the hands rest on it.

export const HEAD = { x: 540, y: 840, rx: 232, ry: 218 };
export const TABLE = 1360;
let INK = "#1b1b1f";
onInk((plum) => {
  INK = plum ? "#241726" : "#1b1b1f"; // the plum ink A/B test (ink.ts)
});

export type Toon = {
  skin: string; skinDark: string; shirt: string; shirtDark: string;
  hair: "tuft" | "ponytail" | "bun" | "side_part" | "bald" | "slick" | "messy";
  hairColor?: string; glasses?: boolean; moustache?: boolean; bindi?: boolean; earrings?: boolean;
  tie?: string; dupatta?: string;
};
const SKIN = { skin: "#f7d2ae", skinDark: "#e9b98f" };
const TAN = { skin: "#e8b88c", skinDark: "#cf9a6c" };
// Keys: the kid, then reel/comic.py OTHERS (who can be on screen)
export const TOONS: Record<string, Toon> = {
  kid: { ...SKIN, shirt: "#ffb000", shirtDark: "#e39300", hair: "tuft" },
  girl: { ...SKIN, shirt: "#ffb000", shirtDark: "#e39300", hair: "ponytail" },
  mother: { ...SKIN, shirt: "#d6336c", shirtDark: "#a61e4d", hair: "bun", bindi: true, earrings: true, dupatta: "#ffd43b" },
  father: { ...TAN, shirt: "#4dabf7", shirtDark: "#1c7ed6", hair: "side_part", moustache: true },
  teacher: { ...TAN, shirt: "#c9a26b", shirtDark: "#a07a45", hair: "bald", glasses: true, moustache: true },
  boss: { ...SKIN, shirt: "#e9ecef", shirtDark: "#adb5bd", hair: "slick", glasses: true, tie: "#c92a2a" },
  friend: { ...TAN, shirt: "#40c057", shirtDark: "#2b8a3e", hair: "messy" },
};
const PINK = "#ff8f9e";
const TEAR = "#62b9ff";
const EYE_L = { x: 470, y: 800 };
const EYE_R = { x: 612, y: 800 };
const EYE = { rx: 80, ry: 88 };
const SHOULDER_L = { x: 370, y: 1118 };
const SHOULDER_R = { x: 710, y: 1118 };
const UPPER = 175;
const FORE = 170;

type Pt = { x: number; y: number };
type Hand = "open" | "fist" | "point" | "phone" | "chai";
type ArmPose = { at: Pt; hand?: Hand; dir?: number }; // dir: where a pointing finger points, in degrees (0 = right)

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const mix = (a: Pt, b: Pt, t: number): Pt => ({ x: lerp(a.x, b.x, t), y: lerp(a.y, b.y, t) });

// ---- eyes and faces ---------------------------------------------------------------------------------------
export type Face = "deadpan" | "side_eye" | "smug" | "shock" | "eye_roll" | "angry" | "cry" | "happy" | "nervous" | "sad" | "cheeky";
export type Look = "viewer" | "side" | "screen" | "up" | "down";

// Where the pupils sit inside each eye, by look
const LOOK: Record<Look, Pt> = { viewer: { x: 4, y: 12 }, side: { x: 42, y: 6 }, screen: { x: -42, y: 26 }, up: { x: 6, y: -44 }, down: { x: 0, y: 44 } };

// upper lid (0 open .. 1 shut), lower lid, pupil size, and the eyebrows: [inner y, outer y] offsets per brow
const FACES: Record<Face, { lid: number; low: number; pupil: number; brows: [number, number]; browR?: [number, number] }> = {
  deadpan: { lid: 0.42, low: 0, pupil: 15, brows: [0, 0] },
  side_eye: { lid: 0.5, low: 0.12, pupil: 15, brows: [6, -4] },
  smug: { lid: 0.38, low: 0.14, pupil: 15, brows: [10, 6], browR: [-26, -34] },
  shock: { lid: 0, low: 0, pupil: 8, brows: [-40, -34] },
  eye_roll: { lid: 0.3, low: 0, pupil: 15, brows: [-14, -8] },
  angry: { lid: 0.22, low: 0.1, pupil: 13, brows: [30, -16] },
  cry: { lid: 0.18, low: 0, pupil: 17, brows: [-22, 14] },
  happy: { lid: 0, low: 0.3, pupil: 16, brows: [-12, -12] },
  nervous: { lid: 0.05, low: 0, pupil: 10, brows: [-20, 8] },
  sad: { lid: 0.35, low: 0, pupil: 16, brows: [-22, 12] },
  cheeky: { lid: 0.36, low: 0.2, pupil: 15, brows: [-4, -20], browR: [-30, -40] },
};

const Eye: React.FC<{ c: Pt; side: -1 | 1; face: Face; look: Pt; blink: number; id: string; f: number; skin: string }> = ({ c, side, face, look, blink, id, f, skin }) => {
  const k = FACES[face];
  const lid = Math.max(k.lid, blink);
  const top = c.y - EYE.ry;
  const lidY = top + EYE.ry * 2 * lid;
  const lowY = c.y + EYE.ry - EYE.ry * 2 * k.low;
  const jitter = face === "nervous" ? Math.sin(f * 1.9 + side) * 3 : 0;
  const px = c.x + look.x + jitter;
  const py = c.y + look.y;
  return (
    <g>
      <clipPath id={id}>
        <ellipse cx={c.x} cy={c.y} rx={EYE.rx} ry={EYE.ry} />
      </clipPath>
      <ellipse cx={c.x} cy={c.y} rx={EYE.rx} ry={EYE.ry} fill="#fff" />
      <g clipPath={`url(#${id})`}>
        {face === "happy" ? (
          // smiling eyes: a happy arc and no pupil
          <path d={`M${c.x - 46},${c.y + 10} Q${c.x},${c.y - 46} ${c.x + 46},${c.y + 10}`} stroke={INK} strokeWidth={13} fill="none" strokeLinecap="round" />
        ) : (
          <>
            <circle cx={px} cy={py} r={k.pupil} fill={INK} />
            <circle cx={px - k.pupil * 0.35} cy={py - k.pupil * 0.4} r={Math.max(3, k.pupil * 0.3)} fill="#fff" />
          </>
        )}
        {lid > 0.01 && <rect x={c.x - EYE.rx - 4} y={top - 6} width={EYE.rx * 2 + 8} height={lidY - top + 6} fill={skin} />}
        {k.low > 0.01 && <rect x={c.x - EYE.rx - 4} y={lowY} width={EYE.rx * 2 + 8} height={EYE.ry * 2} fill={skin} />}
      </g>
      {lid > 0.01 && lid < 0.97 && <path d={`M${c.x - EYE.rx + 6},${lidY} L${c.x + EYE.rx - 6},${lidY}`} stroke={INK} strokeWidth={9} strokeLinecap="round" />}
      {lid >= 0.97 && <path d={`M${c.x - EYE.rx + 10},${c.y + 6} Q${c.x},${c.y + 22} ${c.x + EYE.rx - 10},${c.y + 6}`} stroke={INK} strokeWidth={9} fill="none" strokeLinecap="round" />}
      {k.low > 0.01 && face !== "happy" && <path d={`M${c.x - EYE.rx + 12},${lowY} L${c.x + EYE.rx - 12},${lowY}`} stroke={INK} strokeWidth={7} strokeLinecap="round" />}
      <ellipse cx={c.x} cy={c.y} rx={EYE.rx} ry={EYE.ry} fill="none" stroke={INK} strokeWidth={8} />
    </g>
  );
};

// Thick eyebrows: they carry half of every expression
const Brow: React.FC<{ c: Pt; side: -1 | 1; inner: number; outer: number; raise: number }> = ({ c, side, inner, outer, raise }) => {
  const y = c.y - EYE.ry - 34 - raise;
  const ix = c.x - side * 40; // towards the middle of the face
  const ox = c.x + side * 52;
  return <path d={`M${ix},${y + inner} Q${(ix + ox) / 2},${y - 16 + (inner + outer) / 2} ${ox},${y + outer}`} stroke={INK} strokeWidth={24} fill="none" strokeLinecap="round" />;
};

// width and height factors per mouth shape (reel/voice.py visemes)
const SHAPES: Record<string, [number, number]> = { A: [1, 1], O: [0.62, 1.12], E: [1.35, 0.55], M: [0.9, 0.08] };

const Mouth: React.FC<{ face: Face; open: number; f: number; shape?: string }> = ({ face, open, f, shape = "A" }) => {
  const x = 548;
  const y = 978;
  if (shape === "M" && open > 0.06) {
    // lips pressed together for म / ब / प
    return <path d={`M${x - 30},${y + 2} Q${x},${y + 8} ${x + 30},${y + 2}`} stroke={INK} strokeWidth={9} fill="none" strokeLinecap="round" />;
  }
  if (open > 0.06) {
    // talking: a small dark mouth with a tongue, its shape from the word (A, O, E), its size from the loudness
    const [kw, kh] = SHAPES[shape] ?? SHAPES.A;
    const w = (26 + open * 22) * kw;
    const h = (10 + open * 34) * kh;
    return (
      <g>
        <path d={`M${x - w},${y - 4} Q${x},${y - 12} ${x + w},${y - 4} Q${x + w * 0.8},${y + h} ${x},${y + h} Q${x - w * 0.8},${y + h} ${x - w},${y - 4} Z`} fill="#5a1d24" stroke={INK} strokeWidth={6} strokeLinejoin="round" />
        {open > 0.3 && <ellipse cx={x + 2} cy={y + h * 0.7} rx={w * 0.45} ry={h * 0.22} fill={PINK} />}
      </g>
    );
  }
  const line = { stroke: INK, strokeWidth: 8, fill: "none", strokeLinecap: "round" as const };
  switch (face) {
    case "happy":
      return <path d={`M${x - 52},${y - 14} Q${x},${y + 42} ${x + 52},${y - 14} Z`} fill="#5a1d24" stroke={INK} strokeWidth={7} strokeLinejoin="round" />;
    case "smug":
      return <path d={`M${x - 34},${y + 4} Q${x + 4},${y + 14} ${x + 40},${y - 16}`} {...line} />;
    case "cheeky":
      // a wide, lopsided naughty grin with teeth
      return (
        <g>
          <path d={`M${x - 58},${y - 18} Q${x - 4},${y + 46} ${x + 62},${y - 30} Q${x + 10},${y - 4} ${x - 58},${y - 18} Z`} fill="#5a1d24" stroke={INK} strokeWidth={7} strokeLinejoin="round" />
          <path d={`M${x - 46},${y - 12} Q${x + 6},${y + 2} ${x + 52},${y - 24} L${x + 48},${y - 12} Q${x + 4},${y + 12} ${x - 42},${y - 2} Z`} fill="#fff" />
        </g>
      );
    case "shock":
      return <ellipse cx={x} cy={y + 8} rx={18} ry={26} fill="#5a1d24" stroke={INK} strokeWidth={6} />;
    case "angry":
      return (
        <g>
          <rect x={x - 40} y={y - 10} width={80} height={30} rx={12} fill="#fff" stroke={INK} strokeWidth={7} />
          <path d={`M${x - 38},${y + 5} L${x + 38},${y + 5}`} stroke={INK} strokeWidth={4} />
        </g>
      );
    case "cry": {
      const wob = Math.sin(f * 0.9) * 5;
      return <path d={`M${x - 42},${y + 20} Q${x},${y - 30 + wob} ${x + 42},${y + 20} Z`} fill="#5a1d24" stroke={INK} strokeWidth={7} strokeLinejoin="round" />;
    }
    case "nervous":
      return <path d={`M${x - 40},${y + 2} q10,-12 20,0 t20,0 t20,0 t20,0`} {...line} />;
    case "sad":
      return <path d={`M${x - 30},${y + 14} Q${x},${y - 8} ${x + 30},${y + 14}`} {...line} />;
    case "eye_roll":
      return <path d={`M${x - 26},${y + 4} L${x + 26},${y}`} {...line} />;
    default:
      // deadpan, side eye: a short flat line, a little off centre
      return <path d={`M${x - 22},${y + 2} L${x + 26},${y + 2}`} {...line} />;
  }
};

const HAIR = "#2a1b17";
// the hair cap that covers the top of the head
const cap = (x: number, y: number) => `M${x - 214},${y - 70} Q${x - 170},${y - 250} ${x},${y - 236} Q${x + 170},${y - 250} ${x + 214},${y - 70} Q${x + 130},${y - 160} ${x},${y - 152} Q${x - 130},${y - 160} ${x - 214},${y - 70} Z`;

const HairBack: React.FC<{ t: Toon }> = ({ t }) => {
  const top = HEAD.y - HEAD.ry;
  const fill = t.hairColor ?? HAIR;
  if (t.hair === "ponytail") {
    return <path d={`M${HEAD.x + 170},${top + 90} Q${HEAD.x + 330},${top + 40} ${HEAD.x + 300},${top + 260} Q${HEAD.x + 270},${top + 200} ${HEAD.x + 200},${top + 170} Z`} fill={fill} stroke={INK} strokeWidth={8} strokeLinejoin="round" />;
  }
  if (t.hair === "bun") return <circle cx={HEAD.x} cy={top - 18} r={78} fill={fill} stroke={INK} strokeWidth={8} />;
  return null;
};

const HairFront: React.FC<{ t: Toon }> = ({ t }) => {
  const top = HEAD.y - HEAD.ry;
  const fill = t.hairColor ?? HAIR;
  const o = { fill, stroke: INK, strokeWidth: 8, strokeLinejoin: "round" as const };
  switch (t.hair) {
    case "ponytail":
      return (
        <g>
          <path d={`M${HEAD.x - 196},${HEAD.y - 120} Q${HEAD.x - 120},${HEAD.y - 250} ${HEAD.x + 10},${HEAD.y - 222} Q${HEAD.x + 150},${HEAD.y - 240} ${HEAD.x + 206},${HEAD.y - 110} Q${HEAD.x + 110},${HEAD.y - 168} ${HEAD.x + 20},${HEAD.y - 150} Q${HEAD.x - 100},${HEAD.y - 176} ${HEAD.x - 196},${HEAD.y - 120} Z`} {...o} />
          <path d={`M${HEAD.x + 120},${top + 2} l-46,-40 l6,70 Z M${HEAD.x + 120},${top + 2} l50,-34 l-4,70 Z`} fill="#ff4f7b" stroke={INK} strokeWidth={8} strokeLinejoin="round" />
          <circle cx={HEAD.x + 120} cy={top + 4} r={14} fill="#ff4f7b" stroke={INK} strokeWidth={8} />
        </g>
      );
    case "bun":
      return <path d={cap(HEAD.x, HEAD.y)} {...o} />;
    case "side_part":
      return (
        <g>
          <path d={cap(HEAD.x, HEAD.y)} {...o} />
          <path d={`M${HEAD.x - 70},${HEAD.y - 232} Q${HEAD.x - 60},${HEAD.y - 190} ${HEAD.x - 90},${HEAD.y - 150}`} stroke={SKIN.skin} strokeWidth={10} fill="none" strokeLinecap="round" />
        </g>
      );
    case "bald":
      // a shiny top with tufts over the ears
      return (
        <g>
          <path d={`M${HEAD.x - 228},${HEAD.y - 10} Q${HEAD.x - 250},${HEAD.y - 110} ${HEAD.x - 190},${HEAD.y - 140} Q${HEAD.x - 200},${HEAD.y - 70} ${HEAD.x - 214},${HEAD.y - 4} Z`} {...o} />
          <path d={`M${HEAD.x + 228},${HEAD.y - 10} Q${HEAD.x + 250},${HEAD.y - 110} ${HEAD.x + 190},${HEAD.y - 140} Q${HEAD.x + 200},${HEAD.y - 70} ${HEAD.x + 214},${HEAD.y - 4} Z`} {...o} />
          <path d={`M${HEAD.x - 90},${HEAD.y - 180} Q${HEAD.x - 40},${HEAD.y - 205} ${HEAD.x + 10},${HEAD.y - 196}`} stroke="#fff" strokeWidth={14} fill="none" strokeLinecap="round" opacity={0.6} />
        </g>
      );
    case "slick":
      return (
        <g>
          <path d={cap(HEAD.x, HEAD.y)} {...o} />
          <path d={`M${HEAD.x - 150},${HEAD.y - 170} Q${HEAD.x},${HEAD.y - 250} ${HEAD.x + 170},${HEAD.y - 160}`} stroke="#5c4a42" strokeWidth={8} fill="none" strokeLinecap="round" />
        </g>
      );
    case "messy":
      return (
        <path d={`M${HEAD.x - 214},${HEAD.y - 70} L${HEAD.x - 230},${HEAD.y - 170} L${HEAD.x - 160},${HEAD.y - 150} L${HEAD.x - 150},${HEAD.y - 250} L${HEAD.x - 70},${HEAD.y - 196} L${HEAD.x - 20},${HEAD.y - 280} L${HEAD.x + 40},${HEAD.y - 200} L${HEAD.x + 120},${HEAD.y - 262} L${HEAD.x + 140},${HEAD.y - 170} L${HEAD.x + 236},${HEAD.y - 176} L${HEAD.x + 214},${HEAD.y - 70} Q${HEAD.x + 120},${HEAD.y - 150} ${HEAD.x},${HEAD.y - 146} Q${HEAD.x - 120},${HEAD.y - 150} ${HEAD.x - 214},${HEAD.y - 70} Z`} {...o} />
      );
    default:
      // the kid's spiky tuft on top
      return (
        <path d={`M${HEAD.x - 90},${top + 20} L${HEAD.x - 70},${top - 46} L${HEAD.x - 30},${top + 6} L${HEAD.x},${top - 64} L${HEAD.x + 34},${top + 6} L${HEAD.x + 82},${top - 40} L${HEAD.x + 96},${top + 22} Q${HEAD.x},${top - 6} ${HEAD.x - 90},${top + 20} Z`}
          fill={INK} stroke={INK} strokeWidth={6} strokeLinejoin="round" />
      );
  }
};

// Glasses, a moustache and a bindi, over the face
const FaceExtras: React.FC<{ t: Toon }> = ({ t }) => (
  <g>
    {t.glasses && (
      <g fill="none" stroke={INK} strokeWidth={12}>
        <ellipse cx={EYE_L.x} cy={EYE_L.y} rx={EYE.rx + 14} ry={EYE.ry + 12} />
        <ellipse cx={EYE_R.x} cy={EYE_R.y} rx={EYE.rx + 14} ry={EYE.ry + 12} />
        <path d={`M${EYE_L.x - EYE.rx - 14},${EYE_L.y - 10} L${HEAD.x - HEAD.rx + 6},${EYE_L.y - 24} M${EYE_R.x + EYE.rx + 14},${EYE_R.y - 10} L${HEAD.x + HEAD.rx - 6},${EYE_R.y - 24}`} />
      </g>
    )}
    {t.moustache && (
      <path d={`M${HEAD.x + 8},${HEAD.y + 104} Q${HEAD.x - 50},${HEAD.y + 88} ${HEAD.x - 82},${HEAD.y + 122} Q${HEAD.x - 30},${HEAD.y + 118} ${HEAD.x + 8},${HEAD.y + 124} Q${HEAD.x + 46},${HEAD.y + 118} ${HEAD.x + 98},${HEAD.y + 122} Q${HEAD.x + 66},${HEAD.y + 88} ${HEAD.x + 8},${HEAD.y + 104} Z`}
        fill={t.hairColor ?? HAIR} stroke={INK} strokeWidth={6} strokeLinejoin="round" />
    )}
    {t.bindi && <circle cx={HEAD.x + 4} cy={EYE_L.y - EYE.ry - 66} r={14} fill="#e03131" stroke={INK} strokeWidth={4} />}
  </g>
);

// ---- arms and gestures ------------------------------------------------------------------------------------
export type Gesture = "type" | "talk" | "shrug" | "facepalm" | "point_self" | "point_viewer" | "arms_crossed" | "slam" | "phone" | "chai" | "think" | "scratch_head" | "dance" | "panic";

const REST_L: Pt = { x: 440, y: TABLE - 12 };
const REST_R: Pt = { x: 640, y: TABLE - 12 };

// Where each hand goes for a gesture at frame f (the gesture starts at f = 0), and what it holds
export const gesture = (name: string, f: number): { l: ArmPose; r: ArmPose; hits: number[] } => {
  // anticipation: 3 frames moving 18% the other way, then the travel with a slight overshoot
  const go = (b: number) => interpolate(f, [0, 3, b + 3, b + 6], [0, -0.18, 1.06, 1], { ...clamp, easing: Easing.inOut(Easing.quad) });
  const wave = Math.sin(f * 0.22);
  switch (name) {
    case "type": {
      const tap = (k: number) => (Math.floor(f / 3 + k) % 3 === 0 ? -10 : 0);
      return { l: { at: { x: REST_L.x + 10, y: REST_L.y + tap(0) }, hand: "fist" }, r: { at: { x: REST_R.x - 10, y: REST_R.y + tap(1) }, hand: "fist" }, hits: [] };
    }
    case "shrug":
      return { l: { at: mix(REST_L, { x: 250, y: 1060 + wave * 6 }, go(7)), hand: "open" }, r: { at: mix(REST_R, { x: 830, y: 1060 - wave * 6 }, go(7)), hand: "open" }, hits: [] };
    case "facepalm":
      return { l: { at: REST_L, hand: "fist" }, r: { at: mix(REST_R, { x: 590 + Math.sin(f * 0.15) * 6, y: 800 }, go(8)), hand: "open" }, hits: [] };
    case "point_self":
      return { l: { at: REST_L, hand: "fist" }, r: { at: mix(REST_R, { x: 615, y: 1150 + Math.sin(f * 0.3) * 10 }, go(7)), hand: "point", dir: 195 }, hits: [] };
    case "point_viewer":
      return { l: { at: REST_L, hand: "fist" }, r: { at: mix(REST_R, { x: 760, y: 1150 + Math.sin(f * 0.25) * 8 }, go(7)), hand: "point", dir: -70 }, hits: [] };
    case "arms_crossed":
      return { l: { at: mix(REST_L, { x: 640, y: 1215 }, go(8)), hand: "fist" }, r: { at: mix(REST_R, { x: 440, y: 1235 }, go(8)), hand: "fist" }, hits: [] };
    case "slam": {
      // fists up, then down on the table (the hit shakes the frame and plays a thud)
      const up = interpolate(f, [0, 7, 11, 14], [0, 1, 1, 0], clamp);
      return { l: { at: mix(REST_L, { x: 400, y: 1120 }, up), hand: "fist" }, r: { at: mix(REST_R, { x: 680, y: 1120 }, up), hand: "fist" }, hits: [14] };
    }
    case "phone":
      return { l: { at: REST_L, hand: "fist" }, r: { at: mix(REST_R, { x: 650, y: 1160 }, go(8)), hand: "phone" }, hits: [] };
    case "chai": {
      // the cup goes up to the mouth and back, a slow sip
      const sip = (Math.sin(f * 0.09 - 1.4) + 1) / 2;
      return { l: { at: REST_L, hand: "fist" }, r: { at: mix({ x: 680, y: TABLE - 30 }, { x: 630, y: 1010 }, sip), hand: "chai" }, hits: [] };
    }
    case "think":
      return { l: { at: { x: 470, y: 1215 }, hand: "fist" }, r: { at: mix(REST_R, { x: 605, y: 1040 }, go(8)), hand: "fist" }, hits: [] };
    case "scratch_head":
      return { l: { at: REST_L, hand: "fist" }, r: { at: mix(REST_R, { x: 735 + Math.sin(f * 1.1) * 14, y: 650 + Math.cos(f * 1.1) * 10 }, go(9)), hand: "open" }, hits: [] };
    case "dance": {
      // a silly victory dance: arms up and waving in turn
      const beat = Math.sin(f * 0.42);
      return {
        l: { at: mix(REST_L, { x: 270 - beat * 30, y: 930 + beat * 90 }, go(6)), hand: "open" },
        r: { at: mix(REST_R, { x: 810 - beat * 30, y: 930 - beat * 90 }, go(6)), hand: "open" },
        hits: [],
      };
    }
    case "panic": {
      // "no no no!": both hands flap beside the head
      const flap = Math.sin(f * 1.3) * 34;
      return { l: { at: mix(REST_L, { x: 260, y: 960 + flap }, go(5)), hand: "open" }, r: { at: mix(REST_R, { x: 820, y: 960 - flap }, go(5)), hand: "open" }, hits: [] };
    }
    default: // talk: one hand on the table, the other explains
      return { l: { at: REST_L, hand: "fist" }, r: { at: mix(REST_R, { x: 800 + wave * 20, y: 1170 + Math.cos(f * 0.17) * 22 }, go(7)), hand: "open" }, hits: [] };
  }
};

// Two-bone arm: the elbow bends outward and down, like a person resting their arms
const solveArm = (sh: Pt, target: Pt, side: -1 | 1) => {
  const dx = target.x - sh.x;
  const dy = target.y - sh.y;
  const d = Math.min(UPPER + FORE - 2, Math.max(Math.abs(UPPER - FORE) + 2, Math.hypot(dx, dy)));
  const base = Math.atan2(dy, dx);
  const a = Math.acos((UPPER * UPPER + d * d - FORE * FORE) / (2 * UPPER * d));
  const candidates = [base + a, base - a].map((ang) => ({ x: sh.x + UPPER * Math.cos(ang), y: sh.y + UPPER * Math.sin(ang) }));
  const score = (e: Pt) => side * (e.x - 540) + 0.6 * e.y;
  const elbow = score(candidates[0]) >= score(candidates[1]) ? candidates[0] : candidates[1];
  const hand = { x: sh.x + d * Math.cos(base), y: sh.y + d * Math.sin(base) };
  return { elbow, hand };
};

const Arm: React.FC<{ sh: Pt; pose: ArmPose; side: -1 | 1; t: Toon }> = ({ sh, pose, side, t }) => {
  const { elbow, hand } = solveArm(sh, pose.at, side);
  const path = `M${sh.x},${sh.y} L${elbow.x},${elbow.y} L${hand.x},${hand.y}`;
  const sleeve = mix(sh, elbow, 0.45);
  const fingerDir = ((pose.dir ?? (side < 0 ? 200 : -20)) * Math.PI) / 180;
  return (
    <g>
      <path d={path} stroke={INK} strokeWidth={66} fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <path d={path} stroke={t.skin} strokeWidth={52} fill="none" strokeLinecap="round" strokeLinejoin="round" />
      {/* the short sleeve */}
      <path d={`M${sh.x},${sh.y} L${sleeve.x},${sleeve.y}`} stroke={INK} strokeWidth={92} strokeLinecap="round" />
      <path d={`M${sh.x},${sh.y} L${sleeve.x},${sleeve.y}`} stroke={t.shirt} strokeWidth={78} strokeLinecap="round" />
      {pose.hand === "point" && (
        <g>
          <path d={`M${hand.x},${hand.y} l${Math.cos(fingerDir) * 58},${Math.sin(fingerDir) * 58}`} stroke={INK} strokeWidth={30} strokeLinecap="round" />
          <path d={`M${hand.x},${hand.y} l${Math.cos(fingerDir) * 58},${Math.sin(fingerDir) * 58}`} stroke={t.skin} strokeWidth={18} strokeLinecap="round" />
        </g>
      )}
      {hand.y > TABLE - 60 && <ellipse cx={hand.x + 10} cy={TABLE + 8} rx={48} ry={13} fill="rgba(0,0,0,.18)" />}
      <circle cx={hand.x} cy={hand.y} r={pose.hand === "open" ? 42 : 37} fill={t.skin} stroke={INK} strokeWidth={8} />
      {pose.hand === "open" && <path d={`M${hand.x - 20},${hand.y - 30} l-8,-22 M${hand.x},${hand.y - 36} l0,-24 M${hand.x + 20},${hand.y - 30} l8,-22`} stroke={INK} strokeWidth={8} strokeLinecap="round" />}
      {pose.hand === "phone" && (
        <g>
          <rect x={hand.x - 44} y={hand.y - 120} width={88} height={150} rx={16} fill="#2b2d36" stroke={INK} strokeWidth={8} />
          <rect x={hand.x - 32} y={hand.y - 106} width={64} height={110} rx={8} fill="#8fd3ff" />
          <circle cx={hand.x + 28} cy={hand.y + 4} r={22} fill={t.skin} stroke={INK} strokeWidth={7} />
        </g>
      )}
      {pose.hand === "chai" && (
        <g>
          <path d={`M${hand.x - 40},${hand.y - 64} L${hand.x + 40},${hand.y - 64} L${hand.x + 30},${hand.y + 10} L${hand.x - 30},${hand.y + 10} Z`} fill="#fff" stroke={INK} strokeWidth={8} strokeLinejoin="round" />
          <ellipse cx={hand.x} cy={hand.y - 64} rx={40} ry={10} fill="#b5703a" stroke={INK} strokeWidth={6} />
          <circle cx={hand.x - 30} cy={hand.y - 14} r={24} fill={t.skin} stroke={INK} strokeWidth={7} />
        </g>
      )}
    </g>
  );
};

// Blinks every 0.5-2.3 s (Mr Omi's measured range), sometimes a double blink; 4 frames shaped [.5, 1, 1, .5].
// Seeded per character, so every render of a Reel blinks at the same frames.
const BLINK = [0.5, 1, 1, 0.5];
const blinkCache = new Map<string, number[]>();
const blinkStarts = (seed: string): number[] => {
  const hit = blinkCache.get(seed);
  if (hit) return hit;
  const out: number[] = [];
  for (let t = 10; t < 30 * 180; ) { // three minutes of blinks
    out.push(t);
    if (random(`${seed}-double-${t}`) < 0.12) out.push(t + 6);
    t += 15 + Math.floor(random(`${seed}-gap-${t}`) * 55);
  }
  blinkCache.set(seed, out);
  return out;
};
const blinkAt = (seed: string, clock: number, f: number, swap: boolean) => {
  if (swap && f < BLINK.length) return BLINK[f]; // hide the face swap at a cut behind a blink
  const s = blinkStarts(seed).find((t) => clock >= t && clock < t + BLINK.length);
  return s === undefined ? 0 : BLINK[clock - s];
};

// ---- the whole kid ----------------------------------------------------------------------------------------
export const Kid: React.FC<{
  f: number; face: string; look: string; gesture: string; mouth: number; girl?: boolean;
  toon?: string; // who to draw (TOONS): the kid by default
  // frames into the whole Reel, for blinking on a steady rhythm across cuts
  clock: number;
  table?: React.ReactNode; // drawn over the body and under the arms, so the hands rest on it
  swap?: boolean; // the face changed at this line's start: blink over the change
  viseme?: string; // the mouth shape of the word being said (A, O, E, M)
}> = ({ f, face: faceName, look: lookName, gesture: gestureName, mouth, girl, clock, table, toon, swap = false, viseme }) => {
  const who = toon && TOONS[toon] ? toon : girl ? "girl" : "kid";
  const t = TOONS[who];
  const face = (faceName in FACES ? faceName : "deadpan") as Face;
  const look = (lookName in LOOK ? lookName : "viewer") as Look;
  const eyeRoll = face === "eye_roll" ? LOOK.up : null;
  const target = eyeRoll ?? LOOK[look];
  // the eyes settle on their target in the first frames of a line (a quick, comic dart)
  const dart = interpolate(f, [0, 5], [0, 1], { ...clamp, easing: Easing.out(Easing.back(2)) });
  const pupil = mix(LOOK.viewer, target, look === "viewer" && !eyeRoll ? 1 : dart);
  const blink = face === "shock" || face === "happy" ? 0 : blinkAt(who, clock, f, swap);
  const pose = gesture(gestureName, f);
  // talking: the head nods a little with the voice; shock jolts it back
  const bob = mouth * 10 + Math.sin(clock * 0.05) * 3;
  const dancing = gestureName === "dance" ? Math.sin(f * 0.42) : 0;
  const tiltAt = (fr: number, ck: number) => {
    const dance = gestureName === "dance" ? Math.sin(fr * 0.42) : 0;
    const panic = gestureName === "panic" ? Math.sin(fr * 1.3) : 0;
    return dance * 9 + panic * 3 + (face === "smug" || face === "cheeky" ? -5 : face === "sad" ? 4 : face === "side_eye" ? -3 : Math.sin(ck * 0.031) * 1.2);
  };
  const tilt = tiltAt(f, clock);
  const lag = (tilt - tiltAt(f - 3, clock - 3)) * 1.5; // the tuft / ponytail / bun trails the head
  const take = face === "shock" ? interpolate(f, [0, 2, 6], [1, 1.08, 1], clamp) : 1; // a cartoon "take": the head stretches up
  const jolt = face === "shock" ? interpolate(f, [0, 4, 10], [0, -30, -12], clamp) : 0;
  const brow = FACES[face];
  const browR = brow.browR ?? brow.brows;
  const raise = face === "shock" ? interpolate(f, [0, 5], [0, 14], clamp) : face === "cheeky" ? Math.max(0, Math.sin(f * 0.7)) * 16 : 0;
  const breathe = Math.sin(clock * 0.06) * 4;
  return (
    <g>
      {/* body: a saffron T-shirt, cut by the table */}
      <g transform={`translate(0 ${breathe * 0.5})`}>
        <path d={`M300,${TABLE + 40} L312,1170 Q318,1080 420,1062 Q540,1046 660,1062 Q762,1080 768,1170 L780,${TABLE + 40} Z`} fill={t.shirt} stroke={INK} strokeWidth={9} strokeLinejoin="round" />
        <path d={`M470,1058 Q540,1110 610,1058`} fill={t.skin} stroke={INK} strokeWidth={8} />
        <path d={`M390,1200 Q400,1290 386,${TABLE}`} stroke={t.shirtDark} strokeWidth={10} fill="none" strokeLinecap="round" />
        <path d={`M690,1200 Q680,1290 694,${TABLE}`} stroke={t.shirtDark} strokeWidth={10} fill="none" strokeLinecap="round" />
        {t.dupatta && <path d={`M330,1120 Q420,1090 470,1066 L560,1066 Q470,1200 760,${TABLE + 40} L700,${TABLE + 40} Q440,1240 330,1180 Z`} fill={t.dupatta} stroke={INK} strokeWidth={8} strokeLinejoin="round" />}
        {t.tie && <path d={`M520,1080 L560,1080 L548,1110 L580,1300 L540,1340 L500,1300 L532,1110 Z`} fill={t.tie} stroke={INK} strokeWidth={7} strokeLinejoin="round" />}
      </g>
      {/* the head */}
      <g transform={`translate(${dancing * 18} ${bob * 0.4 + jolt + breathe * 0.3 - Math.abs(dancing) * 16}) rotate(${tilt} ${HEAD.x} ${HEAD.y + 200}) translate(0 ${HEAD.y + HEAD.ry}) scale(1 ${take}) translate(0 ${-(HEAD.y + HEAD.ry)})`}>
        <g transform={`rotate(${lag} ${HEAD.x} ${HEAD.y - HEAD.ry})`}><HairBack t={t} /></g>
        <ellipse cx={HEAD.x - HEAD.rx + 6} cy={HEAD.y + 30} rx={36} ry={50} fill={t.skin} stroke={INK} strokeWidth={8} />
        <ellipse cx={HEAD.x + HEAD.rx - 6} cy={HEAD.y + 30} rx={36} ry={50} fill={t.skin} stroke={INK} strokeWidth={8} />
        <path d={`M${HEAD.x - HEAD.rx + 16},${HEAD.y + 22} q14,-12 18,8 M${HEAD.x + HEAD.rx - 16},${HEAD.y + 22} q-14,-12 -18,8`} stroke={t.skinDark} strokeWidth={7} fill="none" strokeLinecap="round" />
        <ellipse cx={HEAD.x} cy={HEAD.y} rx={HEAD.rx} ry={HEAD.ry} fill={t.skin} stroke={INK} strokeWidth={10} />
        {/* a soft crescent of shade away from a top-left key light */}
        <defs>
          <radialGradient id={`${who}-shade`} cx="0.36" cy="0.32" r="0.86">
            <stop offset="0.7" stopColor="#7d5a8c" stopOpacity={0} />
            <stop offset="1" stopColor="#7d5a8c" stopOpacity={0.24} />
          </radialGradient>
        </defs>
        <ellipse cx={HEAD.x} cy={HEAD.y} rx={HEAD.rx - 5} ry={HEAD.ry - 5} fill={`url(#${who}-shade)`} />
        <g transform={`rotate(${lag} ${HEAD.x} ${HEAD.y - HEAD.ry})`}><HairFront t={t} /></g>
        {t.earrings && [HEAD.x - HEAD.rx + 6, HEAD.x + HEAD.rx - 6].map((x) => <circle key={x} cx={x} cy={HEAD.y + 90} r={14} fill="#fcc419" stroke={INK} strokeWidth={5} />)}
        {(face === "happy" || face === "nervous" || face === "smug" || face === "cheeky") && (
          <>
            <ellipse cx={HEAD.x - 150} cy={HEAD.y + 98} rx={34} ry={18} fill={PINK} opacity={0.55} />
            <ellipse cx={HEAD.x + 158} cy={HEAD.y + 98} rx={34} ry={18} fill={PINK} opacity={0.55} />
          </>
        )}
        <Eye c={EYE_L} side={-1} face={face} look={pupil} blink={blink} id={`${who}-eye-l`} f={f} skin={t.skin} />
        <Eye c={EYE_R} side={1} face={face} look={pupil} blink={blink} id={`${who}-eye-r`} f={f} skin={t.skin} />
        <Brow c={EYE_L} side={-1} inner={brow.brows[0]} outer={brow.brows[1]} raise={raise} />
        <Brow c={EYE_R} side={1} inner={browR[0]} outer={browR[1]} raise={raise} />
        <path d={`M${HEAD.x + 8},${HEAD.y + 70} q16,10 2,22`} stroke={t.skinDark} strokeWidth={8} fill="none" strokeLinecap="round" />
        <FaceExtras t={t} />
        <Mouth face={face} open={mouth} f={f} shape={viseme?.trim() || "A"} />
        {face === "cry" && (
          <g opacity={0.9}>
            {[EYE_L, EYE_R].map((e, i) => (
              <path key={i} d={`M${e.x - 10},${e.y + 70} Q${e.x - 22 + Math.sin(f * 0.4 + i) * 6},${e.y + 200} ${e.x - 6},${e.y + 330} L${e.x + 22},${e.y + 330} Q${e.x + 12},${e.y + 200} ${e.x + 18},${e.y + 70} Z`} fill={TEAR} stroke="#2b86d6" strokeWidth={5} />
            ))}
          </g>
        )}
        {face === "nervous" && <path d={`M${HEAD.x + 200},${HEAD.y - 140} q-22,44 0,58 q22,-14 0,-58 Z`} fill={TEAR} stroke={INK} strokeWidth={5} />}
        {face === "angry" && (
          <g stroke="#e5322d" strokeWidth={9} strokeLinecap="round">
            <path d={`M${HEAD.x + 150},${HEAD.y - 190} l24,-24 M${HEAD.x + 170},${HEAD.y - 160} l34,-6 M${HEAD.x + 140},${HEAD.y - 200} l6,-34`} />
          </g>
        )}
      </g>
      {table}
      <Arm sh={SHOULDER_L} pose={pose.l} side={-1} t={t} />
      <Arm sh={SHOULDER_R} pose={pose.r} side={1} t={t} />
    </g>
  );
};

export const hitsOf = (name: string) => gesture(name, 0).hits;
