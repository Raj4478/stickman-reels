// Adapted from nispa/stickman-video (MIT, (c) 2026 nispa): https://github.com/nispa/stickman-video
// See THIRD_PARTY.md. Changes: label font, and the default stand pose sits on this Reel's stage.
import React from "react";
import { Easing, interpolate } from "remotion";

// Stick-figure animation engine (snappy, physical, cartoon-action style).
// Angles in degrees. Convention: dir(a) = (sin a, cos a) in screen coordinates,
// so 0 = down, 90 = right, -90 = left, 180 = up.
// Upper limbs are relative to the torso (0 = hanging down); forearms/shins are relative to the upper limb.

export type Pose = {
  x: number; // hip position
  y: number;
  lean: number; // torso lean (>0 leans right)
  head: number; // head tilt
  la1: number; // left upper arm (shoulder)
  la2: number; // left forearm (elbow)
  ra1: number;
  ra2: number;
  ll1: number; // left thigh (hip)
  ll2: number; // left shin (knee)
  rl1: number;
  rl2: number;
  rot: number; // whole-body rotation around the hip (flips, falls)
};

export const STAND: Pose = {
  x: 540,
  y: 1097, // hip on the ground line (stage.ts GROUND) at scale 2.2
  lean: 0,
  head: 0,
  la1: -18,
  la2: 8,
  ra1: 18,
  ra2: -8,
  ll1: -12,
  ll2: 4,
  rl1: 12,
  rl2: -4,
  rot: 0,
};

export const P = {
  stand: {} as Partial<Pose>,
  armsUp: { la1: -160, la2: -10, ra1: 160, ra2: 10 },
  cheer: { la1: -150, la2: -30, ra1: 150, ra2: 30, head: -6 },
  pointR: { ra1: 95, ra2: 0, la1: -15, la2: 10 },
  pointL: { la1: -95, la2: 0, ra1: 15, ra2: -10 },
  shrug: { la1: -55, la2: -100, ra1: 55, ra2: 100, head: 8 },
  think: { ra1: 30, ra2: 145, la1: 25, la2: 80, head: 10 },
  crouch: { y: 790, ll1: -60, ll2: 95, rl1: 50, rl2: 90, lean: 10, la1: -40, la2: -30, ra1: 40, ra2: 30 },
  punchR: { lean: 14, ra1: 92, ra2: 0, la1: -40, la2: -110, ll1: -30, ll2: 10, rl1: 35, rl2: -5 },
  kickR: { lean: -30, rl1: 105, rl2: 0, ll1: -10, ll2: 5, la1: -100, la2: 20, ra1: -20, ra2: -40 },
  carry: { la1: -160, la2: -30, ra1: 160, ra2: 30, lean: 0, ll1: -15, ll2: 15, rl1: 15, rl2: -10 },
  hold: { la1: 50, la2: 60, ra1: 70, ra2: 40 },
  facepalm: { ra1: 160, ra2: 120, head: 20, lean: 5 },
  sit: { y: 800, ll1: 80, ll2: -80, rl1: 95, rl2: -85, lean: -5 },
  handshake: { ra1: 70, ra2: 10, la1: -15, la2: 10 },
  sad: { lean: 12, head: 25, la1: -5, la2: 0, ra1: 5, ra2: 0 },
  shock: { la1: -120, la2: -40, ra1: 120, ra2: 40, head: -10, lean: -8 },
} satisfies Record<string, Partial<Pose>>;

const rad = (d: number) => (d * Math.PI) / 180;
const dir = (a: number) => [Math.sin(rad(a)), Math.cos(rad(a))] as const;

export type Joints = {
  hip: [number, number];
  neck: [number, number];
  headC: [number, number];
  lElbow: [number, number];
  lHand: [number, number];
  rElbow: [number, number];
  rHand: [number, number];
  lKnee: [number, number];
  lFoot: [number, number];
  rKnee: [number, number];
  rFoot: [number, number];
  headR: number;
};

export const solve = (p: Pose, s = 1, facing = 1): Joints => {
  const T = 78 * s,
    UA = 40 * s,
    FA = 38 * s,
    TH = 48 * s,
    SH = 46 * s,
    R = 30 * s; // a big cartoon head, so the face reads on a phone
  // every offset is relative to the hip, then rotated by rot and mirrored by facing
  const body = -p.lean;
  const up = dir(180 - p.lean);
  const neck = [up[0] * T, up[1] * T];
  const hd = dir(180 - p.lean + p.head);
  const headC = [neck[0] + hd[0] * (R + 3), neck[1] + hd[1] * (R + 3)];
  const limb = (o: number[], a1: number, a2: number, L1: number, L2: number, ref = body) => {
    const d1 = dir(ref + a1);
    const e = [o[0] + d1[0] * L1, o[1] + d1[1] * L1];
    const d2 = dir(ref + a1 + a2);
    return [e, [e[0] + d2[0] * L2, e[1] + d2[1] * L2]];
  };
  const sh = [neck[0] * 0.92, neck[1] * 0.92];
  const [lE, lH] = limb(sh, p.la1, p.la2, UA, FA);
  const [rE, rH] = limb(sh, p.ra1, p.ra2, UA, FA);
  // legs use the vertical reference, not the torso's
  const [lK, lF] = limb([0, 0], p.ll1, p.ll2, TH, SH, 0);
  const [rK, rF] = limb([0, 0], p.rl1, p.rl2, TH, SH, 0);
  const c = Math.cos(rad(p.rot)),
    sn = Math.sin(rad(p.rot));
  const tr = (v: number[]): [number, number] => {
    const x = v[0] * c - v[1] * sn;
    const y = v[0] * sn + v[1] * c;
    return [p.x + x * facing, p.y + y];
  };
  return {
    hip: [p.x, p.y],
    neck: tr(neck),
    headC: tr(headC),
    lElbow: tr(lE),
    lHand: tr(lH),
    rElbow: tr(rE),
    rHand: tr(rH),
    lKnee: tr(lK),
    lFoot: tr(lF),
    rKnee: tr(rK),
    rFoot: tr(rF),
    headR: R,
  };
};

export type Accessory = "tie" | "scarf" | "tophat" | "crown" | "cap" | "glasses" | "dad" | "ponytail" | "none";
// Expressions (added for Stickman Reels). The look follows popular Hindi stickman Reels: a big white head with
// a dark outline, cartoon eyes with pupils and a shine, eyebrows that carry the emotion, a black open mouth.
export type FaceName =
  | "none" | "eyes" | "angry" | "sad" | "happy" | "surprised" | "love" | "cry" | "big_smile" | "sleepy" | "blush"
  | "shy" | "smug" | "nervous";

const pts = (...a: [number, number][]) => a.map((v) => v.join(",")).join(" ");

export const INK = "#151515";
export const HEAD = "#ffffff";
const TONGUE = "#ff7a8a";
const CHEEK = "#ff9aa8";

// The face, drawn in head space (x towards where the figure faces, y down, head radius 30 * s).
// Features sit a little forward of centre, a three-quarter view, so the figure still "looks" somewhere.
const Face: React.FC<{ face: FaceName; s: number; mouth: number; blink?: boolean }> = ({ face, s, mouth, blink }) => {
  const u = (v: number) => v * s;
  const line = { stroke: INK, strokeWidth: u(2.6), strokeLinecap: "round" as const, strokeLinejoin: "round" as const, fill: "none" };
  const EYES = [-5, 12];
  const EY = -4;
  const shut = (x: number, up = true) => (
    <path key={x} d={`M${u(x - 6)},${u(EY)} Q${u(x)},${u(up ? EY - 6 : EY + 5)} ${u(x + 6)},${u(EY)}`} {...line} />
  );
  const eye = (x: number) => {
    if (face === "big_smile" || face === "blush") return shut(x);
    if (face === "cry") return shut(x, false);
    if (face === "sleepy" || blink) return <path key={x} d={`M${u(x - 6)},${u(EY + 1)} L${u(x + 6)},${u(EY + 1)}`} {...line} />;
    const wide = face === "surprised" || face === "nervous";
    const cute = face === "shy";
    const rx = cute ? 9 : wide ? 9 : 8;
    const ry = cute ? 10.5 : wide ? 11 : 9.5;
    const look = face === "sad" ? [1, 3] : face === "smug" ? [3, 1] : [2, 1.5];
    const shake = face === "nervous" ? Math.sin(x * 3.1 + mouth * 9) * 0.8 : 0;
    const pupil = cute ? 6.4 : wide ? 3 : 4.6;
    return (
      <g key={x}>
        <ellipse cx={u(x)} cy={u(EY)} rx={u(rx)} ry={u(ry)} fill="#fff" stroke={INK} strokeWidth={u(2.2)} />
        {face === "love" ? (
          <path transform={`translate(${u(x + 1)} ${u(EY + 4)}) scale(${s * 0.11})`} d="M0,40 C-70,-5 -55,-60 -18,-55 C0,-52 0,-35 0,-30 C0,-35 0,-52 18,-55 C55,-60 70,-5 0,40 Z" fill="#e8344e" />
        ) : (
          <>
            <circle cx={u(x + look[0] + shake)} cy={u(EY + look[1])} r={u(pupil)} fill={INK} />
            <circle cx={u(x + look[0] - pupil * 0.35)} cy={u(EY + look[1] - pupil * 0.4)} r={u(Math.max(1.3, pupil * 0.32))} fill="#fff" />
            {cute && <circle cx={u(x + look[0] + 2)} cy={u(EY + look[1] + 2.4)} r={u(1)} fill="#fff" />}
          </>
        )}
        {(face === "smug" || face === "sad") && (
          // heavy upper lid: half-closed, bored or low
          <path d={`M${u(x - rx - 1)},${u(EY + (face === "smug" ? 0 : -3))} L${u(x + rx + 1)},${u(EY + (face === "smug" ? 0 : -3))} L${u(x + rx + 1)},${u(EY - ry - 2)} L${u(x - rx - 1)},${u(EY - ry - 2)} Z`}
            fill={HEAD} stroke="none" />
        )}
        {(face === "smug" || face === "sad") && <path d={`M${u(x - rx)},${u(EY + (face === "smug" ? 0 : -3))} L${u(x + rx)},${u(EY + (face === "smug" ? 0 : -3))}`} {...line} />}
      </g>
    );
  };
  const brow = (x: number, side: number) => {
    // side -1: the eye further back, +1: the front eye; "inner" ends point to the middle of the face
    const inner = x + side * -6;
    const outer = x + side * 7;
    if (face === "angry") return <path key={x} d={`M${u(outer)},${u(-18)} L${u(inner)},${u(-12)}`} {...line} strokeWidth={u(3.4)} />;
    if (face === "sad" || face === "cry" || face === "nervous") return <path key={x} d={`M${u(outer)},${u(-13)} L${u(inner)},${u(-18)}`} {...line} />;
    if (face === "surprised") return <path key={x} d={`M${u(x - 7)},${u(-19)} Q${u(x)},${u(-24)} ${u(x + 7)},${u(-19)}`} {...line} />;
    if (face === "smug") return side > 0 ? <path key={x} d={`M${u(x - 7)},${u(-17)} Q${u(x)},${u(-22)} ${u(x + 7)},${u(-17)}`} {...line} /> : <path key={x} d={`M${u(x - 7)},${u(-12)} L${u(x + 7)},${u(-12)}`} {...line} />;
    return null;
  };
  const MX = 4;
  const MY = 13;
  const talking = mouth > 0.05;
  const bigMouth = (open: number) => (
    <g>
      <path d={`M${u(MX - 4 - open * 3)},${u(MY - 1)} Q${u(MX)},${u(MY - 3)} ${u(MX + 4 + open * 3)},${u(MY - 1)} Q${u(MX + 3 + open * 2)},${u(MY + 2 + open * 7)} ${u(MX)},${u(MY + 2 + open * 7)} Q${u(MX - 3 - open * 2)},${u(MY + 2 + open * 7)} ${u(MX - 4 - open * 3)},${u(MY - 1)} Z`} fill={INK} />
      {open > 0.35 && <ellipse cx={u(MX + 0.5)} cy={u(MY + 1 + open * 5.5)} rx={u(1.4 + open * 2)} ry={u(0.8 + open * 1.2)} fill={TONGUE} />}
    </g>
  );
  let lips: React.ReactNode = <path d={`M${u(MX - 4)},${u(MY)} Q${u(MX)},${u(MY + 3)} ${u(MX + 4)},${u(MY)}`} {...line} />;
  if (talking) lips = bigMouth(Math.min(1, mouth));
  else if (face === "big_smile" || face === "love") lips = bigMouth(0.8);
  else if (face === "happy" || face === "blush" || face === "shy") lips = <path d={`M${u(MX - 6)},${u(MY - 1)} Q${u(MX)},${u(MY + 6)} ${u(MX + 6)},${u(MY - 1)}`} {...line} />;
  else if (face === "sad") lips = <path d={`M${u(MX - 5)},${u(MY + 3)} Q${u(MX)},${u(MY - 2)} ${u(MX + 5)},${u(MY + 3)}`} {...line} />;
  else if (face === "cry") lips = <path d={`M${u(MX - 6)},${u(MY + 6)} Q${u(MX)},${u(MY - 3)} ${u(MX + 6)},${u(MY + 6)} Z`} fill={INK} />;
  else if (face === "surprised") lips = <ellipse cx={u(MX)} cy={u(MY + 2)} rx={u(3.2)} ry={u(4.4)} fill={INK} />;
  else if (face === "angry") lips = (
    <g>
      <rect x={u(MX - 7)} y={u(MY - 2)} width={u(14)} height={u(6)} rx={u(2.5)} fill={INK} />
      <path d={`M${u(MX - 6)},${u(MY + 1)} L${u(MX + 6)},${u(MY + 1)}`} stroke="#fff" strokeWidth={u(1.2)} />
    </g>
  );
  else if (face === "smug") lips = <path d={`M${u(MX - 4)},${u(MY + 1)} Q${u(MX + 2)},${u(MY + 2)} ${u(MX + 6)},${u(MY - 2)}`} {...line} />;
  else if (face === "nervous") lips = <path d={`M${u(MX - 6)},${u(MY + 1)} q${u(1.5)},${u(-2)} ${u(3)},0 t${u(3)},0 t${u(3)},0 t${u(3)},0`} {...line} />;
  else if (face === "sleepy") lips = <ellipse cx={u(MX)} cy={u(MY + 1)} rx={u(2)} ry={u(1.6)} fill={INK} />;
  return (
    <>
      {(face === "blush" || face === "shy" || face === "love") && (
        <>
          <ellipse cx={u(-11)} cy={u(7)} rx={u(4.5)} ry={u(2.6)} fill={CHEEK} opacity={0.8} />
          <ellipse cx={u(19)} cy={u(7)} rx={u(4.5)} ry={u(2.6)} fill={CHEEK} opacity={0.8} />
        </>
      )}
      {EYES.map(eye)}
      {brow(EYES[0], -1)}
      {brow(EYES[1], 1)}
      {face === "cry" && (
        <>
          <path d={`M${u(-5)},${u(0)} L${u(-6)},${u(20)}`} stroke="#5fb8ff" strokeWidth={u(3.2)} strokeLinecap="round" />
          <path d={`M${u(12)},${u(0)} L${u(13)},${u(18)}`} stroke="#5fb8ff" strokeWidth={u(3.2)} strokeLinecap="round" />
        </>
      )}
      {face === "nervous" && <path d={`M${u(24)},${u(-16)} q${u(-3)},${u(6)} 0,${u(8)} q${u(3)},${u(-2)} 0,${u(-8)} Z`} fill="#5fb8ff" stroke={INK} strokeWidth={u(1)} />}
      {lips}
    </>
  );
};

export const Figure: React.FC<{
  pose: Pose;
  color: string;
  scale?: number;
  facing?: number;
  accessory?: Accessory;
  opacity?: number;
  face?: FaceName;
  mouth?: number; // 0..1: talking, from the narration loudness (replaces the drawn mouth while > 0)
  blink?: boolean;
  label?: string;
  labelColor?: string;
  draw?: number; // 0..1: the figure is progressively "drawn" (pencil stroke)
  children?: (j: Joints) => React.ReactNode;
  behind?: (j: Joints) => React.ReactNode;
}> = ({ pose, color, scale = 1, facing = 1, accessory = "none", opacity = 1, face = "none", mouth = 0, blink, label, labelColor, draw = 1, children, behind }) => {
  const j = solve(pose, scale, facing);
  const w = 12 * scale;
  const st = {
    stroke: color,
    strokeWidth: w,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    fill: "none",
  };
  const R = j.headR;
  const [hx, hy] = j.headC;
  // stroke progress per part: head, torso, arms, legs
  const seg = (a: number, b: number) => Math.max(0, Math.min(1, (draw - a) / (b - a)));
  const dash = (t: number) =>
    draw >= 1 ? {} : { pathLength: 1, strokeDasharray: `${t} 2`, opacity: t > 0 ? 1 : 0 };
  const dHead = seg(0, 0.3),
    dTorso = seg(0.3, 0.45),
    dArms = seg(0.45, 0.72),
    dLegs = seg(0.72, 1);
  // head "up" direction, used to orient accessories
  const ux = (hx - j.neck[0]) / (R + 3);
  const uy = (hy - j.neck[1]) / (R + 3);
  const ang = (Math.atan2(uy, ux) * 180) / Math.PI + 90;
  return (
    <g opacity={opacity}>
      {behind?.(j)}
      <polyline points={pts(j.lFoot, j.lKnee, j.hip, j.rKnee, j.rFoot)} {...st} {...dash(dLegs)} />
      <polyline points={pts(j.lHand, j.lElbow, j.neck, j.rElbow, j.rHand)} {...st} {...dash(dArms)} />
      <line x1={j.neck[0]} y1={j.neck[1]} x2={j.hip[0]} y2={j.hip[1]} {...st} {...dash(dTorso)} />
      {accessory === "tie" && (
        <polygon
          points={pts(
            [j.neck[0] * 0.85 + j.hip[0] * 0.15 - 6 * scale, j.neck[1] * 0.85 + j.hip[1] * 0.15],
            [j.neck[0] * 0.85 + j.hip[0] * 0.15 + 6 * scale, j.neck[1] * 0.85 + j.hip[1] * 0.15],
            [j.neck[0] * 0.45 + j.hip[0] * 0.55, j.neck[1] * 0.45 + j.hip[1] * 0.55],
          )}
          fill="#d6263b"
          stroke="#1a1a1a"
          strokeWidth={2.5 * scale}
          strokeLinejoin="round"
        />
      )}
      {/* the head: white with an outline in the figure's colour */}
      {draw >= 1 ? (
        <circle cx={hx} cy={hy} r={R} fill={HEAD} stroke={color} strokeWidth={w * 0.36} />
      ) : (
        <circle cx={hx} cy={hy} r={R} {...st} strokeWidth={w * 0.36} fill={dHead >= 1 ? HEAD : "none"} {...dash(dHead)} />
      )}
      <g transform={`translate(${hx} ${hy}) rotate(${ang}) scale(${facing} 1)`}>
        {face !== "none" && draw >= 1 && <Face face={face} s={scale} mouth={mouth} blink={blink} />}
        {accessory === "scarf" && (
          <>
            {/* headscarf: cap on the head plus cloth falling behind the neck */}
            <path
              d={`M${R + 3 * scale},${-9 * scale} Q${R + 3 * scale},${-R - 7 * scale} 0,${-R - 7 * scale} Q${-R - 4 * scale},${-R - 7 * scale} ${-R - 5 * scale},${-2 * scale} L${-R - 12 * scale},${R + 24 * scale} L${-R + 8 * scale},${R + 16 * scale} L${-R + 6 * scale},${-9 * scale} Z`}
              fill="#ffffff"
              stroke="#1a1a1a"
              strokeWidth={3 * scale}
              strokeLinejoin="round"
            />
            <rect x={-R - 3 * scale} y={-R * 0.62} width={2 * R + 6 * scale} height={6 * scale} rx={3 * scale} fill="#1a1a1a" />
          </>
        )}
        {accessory === "tophat" && (
          <>
            <rect x={-R - 8 * scale} y={-R - 2 * scale} width={2 * R + 16 * scale} height={7 * scale} rx={3 * scale} fill="#1a1a1a" />
            <rect x={-R + 2 * scale} y={-R - 34 * scale} width={2 * R - 4 * scale} height={34 * scale} rx={3 * scale} fill="#1a1a1a" />
            <rect x={-R + 2 * scale} y={-R - 10 * scale} width={2 * R - 4 * scale} height={6 * scale} fill="#d6263b" />
          </>
        )}
        {accessory === "crown" && (
          <polygon
            points={`${-R},${-R + 6 * scale} ${-R},${-R - 18 * scale} ${-R / 2},${-R - 6 * scale} 0,${-R - 22 * scale} ${R / 2},${-R - 6 * scale} ${R},${-R - 18 * scale} ${R},${-R + 6 * scale}`}
            fill="#f2c12e"
            stroke="#1a1a1a"
            strokeWidth={3 * scale}
            strokeLinejoin="round"
          />
        )}
        {accessory === "cap" && (
          <>
            {/* sits above the eyebrows, so the eyes stay visible */}
            <path d={`M${-R + 2 * scale},${-17 * scale} Q0,${-R - 14 * scale} ${R - 2 * scale},${-17 * scale} Z`} fill="#1a1a1a" />
            <rect x={0} y={-21 * scale} width={R + 14 * scale} height={5 * scale} rx={2.5 * scale} fill="#1a1a1a" />
          </>
        )}
        {(accessory === "glasses" || accessory === "dad") && face !== "none" && (
          <g stroke={INK} strokeWidth={2.2 * scale} fill="none">
            <rect x={-14 * scale} y={-12 * scale} width={18 * scale} height={14 * scale} rx={4 * scale} />
            <rect x={3 * scale} y={-12 * scale} width={18 * scale} height={14 * scale} rx={4 * scale} />
            <path d={`M${21 * scale},${-8 * scale} L${R},${-10 * scale}`} />
          </g>
        )}
        {accessory === "ponytail" && (
          // a girl hero: hair over the top of the head, a ponytail behind and a small bow
          <>
            <path d={`M${-R - 2 * scale},${2 * scale} Q${-R - 4 * scale},${-R - 4 * scale} ${4 * scale},${-R - 3 * scale} Q${R * 0.7},${-R} ${R * 0.55},${-R * 0.5} Q${0},${-R * 0.75} ${-R * 0.55},${-R * 0.3} Q${-R * 0.75},${-6 * scale} ${-R - 2 * scale},${2 * scale} Z`} fill={INK} />
            <path d={`M${-R * 0.75},${-R * 0.55} Q${-R - 26 * scale},${-R * 0.2} ${-R - 14 * scale},${R + 8 * scale} Q${-R - 4 * scale},${R * 0.2} ${-R * 0.55},${-R * 0.35} Z`} fill={INK} />
            <path d={`M${-R * 0.85},${-R * 0.72} l${-9 * scale},${-8 * scale} l${2 * scale},${14 * scale} Z M${-R * 0.85},${-R * 0.72} l${10 * scale},${-9 * scale} l${-1 * scale},${14 * scale} Z`} fill="#e5322d" stroke={INK} strokeWidth={1.5 * scale} strokeLinejoin="round" />
          </>
        )}
        {accessory === "dad" && face !== "none" && (
          // a big moustache, drawn over the top lip
          <path d={`M${-6 * scale},${9 * scale} Q${-4 * scale},${3 * scale} ${4 * scale},${5 * scale} Q${12 * scale},${3 * scale} ${14 * scale},${9 * scale} Q${4 * scale},${7 * scale} ${-6 * scale},${9 * scale} Z`} fill={INK} />
        )}
      </g>
      {label && (
        <text
          x={hx}
          y={hy - R - (accessory === "tophat" ? 52 : accessory === "scarf" || accessory === "crown" ? 36 : 16) * scale}
          textAnchor="middle"
          fontFamily="Poppins"
          fontWeight={800}
          fontSize={30 * scale}
          letterSpacing={0}
          fill={labelColor ?? color}
          stroke="#fafaf7"
          strokeWidth={6}
          paintOrder="stroke"
        >
          {label}
        </text>
      )}
      {children?.(j)}
    </g>
  );
};

// ---------- pose animation -----------

export type Key = { f: number; p: Partial<Pose>; e?: (t: number) => number };

export const SNAP = Easing.bezier(0.2, 0.9, 0.25, 1.15); // snap with slight overshoot
export const SMOOTH = Easing.bezier(0.45, 0, 0.55, 1);
export const HOLD = () => 0;

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

// keys are cumulative: each key inherits unspecified values from the previous one
export const poseAt = (f: number, keys: Key[], base: Pose = STAND): Pose => {
  const full: Pose[] = [];
  let acc = { ...base };
  for (const k of keys) {
    acc = { ...acc, ...k.p };
    full.push(acc);
  }
  if (keys.length === 0) return base;
  if (f <= keys[0].f) return full[0];
  for (let i = 1; i < keys.length; i++) {
    if (f <= keys[i].f) {
      const a = keys[i - 1].f;
      const b = keys[i].f;
      const t = (keys[i].e ?? SNAP)(interpolate(f, [a, b], [0, 1]));
      const A = full[i - 1];
      const B = full[i];
      const out = {} as Pose;
      (Object.keys(A) as (keyof Pose)[]).forEach((n) => {
        out[n] = lerp(A[n], B[n], t);
      });
      return out;
    }
  }
  return full[full.length - 1];
};

// run cycle, added on top of a pose
export const runCycle = (f: number, speed = 0.45, amp = 1): Partial<Pose> => {
  const s = Math.sin(f * speed);
  const c = Math.cos(f * speed);
  return {
    lean: 14 * amp,
    ll1: -45 * s * amp,
    ll2: (35 + 35 * Math.max(0, -c)) * amp,
    rl1: 45 * s * amp,
    rl2: (35 + 35 * Math.max(0, c)) * amp,
    la1: 50 * s * amp,
    la2: -70 * amp,
    ra1: -50 * s * amp,
    ra2: -70 * amp,
  };
};

export const walkCycle = (f: number, speed = 0.22): Partial<Pose> => {
  const s = Math.sin(f * speed);
  return {
    ll1: -22 * s,
    ll2: 10 + 12 * Math.max(0, s),
    rl1: 22 * s,
    rl2: 10 + 12 * Math.max(0, -s),
    la1: 20 * s - 6,
    la2: -10,
    ra1: -20 * s + 6,
    ra2: 10,
  };
};

// idle "breathing": small continuous motion that keeps characters alive
export const idle = (f: number, seed = 0): Partial<Pose> => ({
  y: Math.sin(f * 0.12 + seed) * 1.6,
  la1: Math.sin(f * 0.1 + seed) * 2,
  ra1: -Math.sin(f * 0.1 + seed) * 2,
});

export const addPose = (p: Pose, d: Partial<Pose>, replace = false): Pose => {
  const o = { ...p };
  (Object.keys(d) as (keyof Pose)[]).forEach((k) => {
    o[k] = replace ? (d[k] as number) : o[k] + (d[k] as number);
  });
  return o;
};

// animated figure with motion trails (smears) when it moves fast
export const Actor: React.FC<{
  f: number;
  keys: Key[];
  color: string;
  base?: Partial<Pose>;
  scale?: number;
  facing?: number | ((f: number) => number);
  accessory?: Accessory;
  face?: FaceName;
  mouth?: number; // 0..1: talking, from the narration loudness (replaces the drawn mouth while > 0)
  label?: string;
  mod?: (f: number, p: Pose) => Pose;
  trails?: boolean;
  opacity?: number;
  draw?: number;
  children?: (j: Joints) => React.ReactNode;
  behind?: (j: Joints) => React.ReactNode;
}> = ({ f, keys, color, base, scale = 1, facing = 1, accessory, face = "eyes", mouth = 0, label, mod, trails = true, opacity = 1, draw, children, behind }) => {
  const b = { ...STAND, ...base };
  const get = (t: number) => {
    const p = poseAt(t, keys, b);
    return mod ? mod(t, p) : p;
  };
  const fc = (t: number) => (typeof facing === "function" ? facing(t) : facing);
  const now = get(f);
  const seed = [...color].reduce((a, c) => a + c.charCodeAt(0), 0);
  const blink = (f + seed) % 97 < 4;
  const ghosts: React.ReactNode[] = [];
  if (trails) {
    [3, 2, 1].forEach((d) => {
      const g = get(f - d);
      const dist = Math.hypot(g.x - now.x, g.y - now.y) + Math.abs(g.rot - now.rot) * 1.5;
      if (dist > 26) {
        ghosts.push(
          <Figure key={d} pose={g} color={color} scale={scale} facing={fc(f - d)} opacity={(0.32 - d * 0.08) * opacity} />,
        );
      }
    });
  }
  return (
    <>
      {ghosts}
      <Figure
        pose={now}
        color={color}
        scale={scale}
        facing={fc(f)}
        accessory={accessory}
        face={face}
        mouth={mouth}
        blink={blink}
        label={label}
        opacity={opacity}
        draw={draw}
        behind={behind}
      >
        {children}
      </Figure>
    </>
  );
};

// hip y so the feet touch the ground (ground line ~852)
export const groundY = (s = 1, ground = 852) => ground - 92.5 * s;
