import React, { useEffect, useState } from "react";
import {
  AbsoluteFill, Audio, Sequence, continueRender, delayRender, interpolate, interpolateColors, staticFile, useCurrentFrame, useVideoConfig,
} from "remotion";
import { Act, CX, GROUND, H, HIP, PropView, S, W, act } from "./actions";
import { COL, Cursor, FONT, ease, shakeAt } from "./engine/fx";
import { Actor, Joints, STAND, solve } from "./engine/stick";

// One Reel: hook (the hero is drawn, the title slams in) -> 4-6 story beats, each acted out by the stick
// figure -> the lesson card -> the question and a follow card. Every segment starts when its line is spoken.

export type Segment = {
  kind: "hook" | "scene" | "lesson" | "ask";
  text: string;
  start: number;
  end: number;
  title?: string;
  caption?: string;
  action?: string;
  prop?: string;
  mood?: string;
};
export type ReelProps = { audio: string | null; lead: number; handle: string; duration: number; segments: Segment[] };

const MOOD: Record<string, { bg: string; accent: string }> = {
  calm: { bg: "#f6f1e6", accent: COL.blue },
  happy: { bg: "#fff1cf", accent: COL.orange },
  sad: { bg: "#e3e8ef", accent: "#5b6b82" },
  tense: { bg: "#fbe3dc", accent: COL.red },
};
const moodOf = (s: Segment) => MOOD[s.kind === "lesson" ? "happy" : s.mood ?? "calm"] ?? MOOD.calm;
const FONTS = [
  { family: "Poppins", file: "fonts/Poppins-Medium.ttf", weight: "500" },
  { family: "Poppins", file: "fonts/Poppins-Bold.ttf", weight: "700" },
  { family: "Poppins", file: "fonts/Poppins-ExtraBold.ttf", weight: "800" },
  { family: "Noto Sans Devanagari", file: "fonts/NotoSansDevanagari.ttf", weight: "100 900" },
];

const useFonts = () => {
  const [handle] = useState(() => delayRender("Loading fonts"));
  useEffect(() => {
    Promise.all(FONTS.map((f) => new FontFace(f.family, `url(${staticFile(f.file)})`, { weight: f.weight }).load()
      .then((face) => (document.fonts as unknown as { add: (f: FontFace) => void }).add(face))))
      .catch(() => undefined) // a missing font falls back to the system font rather than failing the render
      .finally(() => continueRender(handle));
  }, [handle]);
};

// Big words at the top that slam in with a little overshoot (no letter-spacing: it breaks Hindi shaping)
const Slam: React.FC<{ f: number; children: React.ReactNode; size: number; color?: string; bar?: string }> = ({ f, children, size, color = COL.ink, bar }) => {
  const s = interpolate(f, [0, 5, 9, 13], [1.7, 0.94, 1.03, 1], { extrapolateRight: "clamp" });
  return (
    <div style={{ transform: `scale(${s}) rotate(${(1 - ease(f, 0, 10)) * -4}deg)`, opacity: ease(f, 0, 4), textAlign: "center" }}>
      <span style={{
        fontFamily: FONT.hindi, fontWeight: 800, fontSize: size, lineHeight: 1.32, color,
        background: bar ? `linear-gradient(transparent 58%, ${bar} 58%, ${bar} 92%, transparent 92%)` : undefined,
        boxDecorationBreak: "clone", WebkitBoxDecorationBreak: "clone", padding: "0 12px",
      }}>{children}</span>
    </div>
  );
};

const Top: React.FC<{ seg: Segment; f: number }> = ({ seg, f }) => {
  const mood = moodOf(seg);
  let body: React.ReactNode = null;
  if (seg.kind === "hook") body = <Slam f={f - 8} size={118} bar={COL.yellow}>{seg.title}</Slam>;
  if (seg.kind === "scene") body = <Slam f={f - 3} size={seg.caption && seg.caption.length > 18 ? 92 : 108} color={mood.accent}>{seg.caption}</Slam>;
  if (seg.kind === "ask") body = <Slam f={f - 3} size={seg.text.length > 40 ? 64 : 76}>{seg.text}</Slam>;
  if (seg.kind === "lesson") {
    const s = interpolate(f - 2, [0, 6, 10, 14], [0.3, 1.06, 0.98, 1], { extrapolateRight: "clamp" });
    body = (
      <div style={{ transform: `scale(${s}) rotate(-1.5deg)`, opacity: ease(f, 2, 8), background: "#fff", border: `8px solid ${COL.ink}`,
        borderRadius: 28, boxShadow: `14px 14px 0 ${COL.ink}`, padding: "54px 44px 40px", position: "relative", textAlign: "center" }}>
        <div style={{ position: "absolute", top: -40, left: "50%", transform: "translateX(-50%)", background: COL.orange, color: "#fff",
          fontFamily: FONT.hindi, fontWeight: 800, fontSize: 44, padding: "4px 34px", borderRadius: 40, border: `6px solid ${COL.ink}` }}>सीख</div>
        <div style={{ fontFamily: FONT.hindi, fontWeight: 800, fontSize: seg.text.length > 40 ? 64 : 76, lineHeight: 1.32, color: COL.ink }}>{seg.text}</div>
      </div>
    );
  }
  return <div style={{ position: "absolute", left: 70, right: 70, top: 250, height: 470, display: "flex", alignItems: "center", justifyContent: "center" }}>{body}</div>;
};

// Spoken words, a few at a time, with the current word highlighted (timed by its share of the line)
const Subtitle: React.FC<{ seg: Segment; f: number; fps: number }> = ({ seg, f, fps }) => {
  const words = seg.text.split(/\s+/).filter(Boolean);
  if (!words.length) return null;
  const weights = words.map((w) => w.length + 1);
  const total = weights.reduce((a, b) => a + b, 0);
  const spoken = Math.max(0.5, Math.min(seg.end, seg.start + total * 0.075) - seg.start) * fps; // speech ends before the pause
  const pos = (f / spoken) * total;
  let acc = 0;
  let current = words.length - 1;
  for (let i = 0; i < words.length; i++) {
    acc += weights[i];
    if (acc > pos) {
      current = i;
      break;
    }
  }
  const CHUNK = 6;
  const start = Math.floor(current / CHUNK) * CHUNK;
  const chunk = words.slice(start, start + CHUNK);
  return (
    <div style={{ position: "absolute", left: 60, right: 60, top: 1395, display: "flex", justifyContent: "center", opacity: ease(f, 0, 5) }}>
      <div style={{ background: "#fff", border: `6px solid ${COL.ink}`, borderRadius: 22, padding: "14px 30px", textAlign: "center",
        fontFamily: FONT.hindi, fontWeight: 700, fontSize: 50, lineHeight: 1.4, color: COL.ink, boxShadow: `8px 8px 0 rgba(0,0,0,.18)` }}>
        {chunk.map((w, i) => (
          <span key={start + i} style={{ color: start + i === current ? COL.orange : start + i < current ? COL.ink : "#7a7a7a" }}>{w}{" "}</span>
        ))}
      </div>
    </div>
  );
};

const Follow: React.FC<{ f: number; handle: string }> = ({ f, handle }) => {
  const s = interpolate(f - 10, [0, 6, 10, 14], [0.3, 1.08, 0.97, 1], { extrapolateRight: "clamp" });
  return (
    <div style={{ position: "absolute", left: 0, right: 0, top: 1400, display: "flex", flexDirection: "column", alignItems: "center", gap: 18 }}>
      <div style={{ transform: `scale(${s})`, opacity: ease(f, 10, 14), background: COL.red, color: "#fff", fontFamily: FONT.hindi, fontWeight: 800,
        fontSize: 58, padding: "16px 50px", borderRadius: 60, border: `6px solid ${COL.ink}`, boxShadow: `8px 8px 0 ${COL.ink}` }}>
        फ़ॉलो करें
      </div>
      <div style={{ opacity: ease(f, 18, 26), fontFamily: FONT.hindi, fontWeight: 700, fontSize: 42, color: COL.ink }}>
        रोज़ एक नई सीख{handle ? ` · ${handle}` : ""}
      </div>
    </div>
  );
};

// The opening: a cursor draws the hero stroke by stroke, then the hero waves
const hookAct = (f: number): Act => ({
  keys: [{ f: 0, p: {} }, { f: 32, p: {} }, { f: 38, p: { ra1: 150, ra2: -20 } }],
  mod: (t, p) => (t > 38 ? { ...p, ra2: p.ra2 + Math.sin(t * 0.45) * 28 } : p),
  face: f > 30 ? "happy" : "eyes",
  hits: [],
});

const cursorAt = (f: number) => {
  const j = solve(STAND, S, 1);
  const path: [number, number][] = [[j.headC[0] + 30, j.headC[1] - 30], j.neck, j.lHand, j.rHand, j.hip, j.lFoot, j.rFoot];
  const t = interpolate(f, [4, 28], [0, path.length - 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const i = Math.min(path.length - 2, Math.floor(t));
  const k = t - i;
  return [path[i][0] + (path[i + 1][0] - path[i][0]) * k, path[i][1] + (path[i + 1][1] - path[i][1]) * k];
};

const World: React.FC<{ seg: Segment; f: number; dur: number }> = ({ seg, f, dur }) => {
  const a: Act = seg.kind === "scene" ? act(seg.action ?? "point", f, dur)
    : seg.kind === "hook" ? hookAct(f)
    : seg.kind === "lesson" ? act("point", f, dur)
    : act("think", f, dur);
  const prop = seg.kind === "scene" && seg.prop && seg.prop !== "none" && a.propAt !== null ? seg.prop : null;
  const hold = (j: Joints) => (
    <>
      {a.hold?.(j)}
      {prop === "rain_cloud" && <PropView prop={prop} x={0} f={f} dur={dur} head={j.headC} />}
    </>
  );
  const s = shakeAt(f, a.hits, 16);
  const [cx, cy] = cursorAt(f);
  return (
    <AbsoluteFill style={{ transform: `translate(${s.x}px, ${s.y}px) rotate(${s.r}deg)` }}>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ position: "absolute" }}>
        <ellipse cx={CX} cy={GROUND + 6} rx={150} ry={14} fill="rgba(0,0,0,.08)" />
        <path d={`M40,${GROUND} Q300,${GROUND - 6} 540,${GROUND} T1040,${GROUND}`} stroke={COL.ink} strokeWidth={7} fill="none" strokeLinecap="round" />
        {a.under}
        {prop && prop !== "rain_cloud" && <PropView prop={prop} x={a.propAt?.x ?? 880} f={f} dur={dur} />}
        {a.second && (
          <Actor f={f} keys={a.second.keys} mod={a.second.mod} color={a.second.color ?? COL.blue} face={a.second.face}
            facing={a.second.facing} scale={S} base={{ y: HIP }} />
        )}
        <Actor f={f} keys={a.keys} mod={a.mod} color={COL.ink} face={a.face} facing={a.facing} scale={S} base={{ y: HIP }}
          draw={seg.kind === "hook" ? ease(f, 4, 28, 0, 1, (t) => t) : 1}>
          {hold}
        </Actor>
        {a.over}
        {seg.kind === "hook" && f < 34 && <Cursor x={cx} y={cy} />}
      </svg>
    </AbsoluteFill>
  );
};

export const StickReel: React.FC<ReelProps> = (p) => {
  useFonts();
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const at = (t: number) => Math.round(t * fps);
  const index = Math.max(0, p.segments.findIndex((s) => frame >= at(s.start) && frame < at(s.end)));
  const now = p.segments[frame >= at(p.segments[p.segments.length - 1].start) ? p.segments.length - 1 : index];
  const before = p.segments[Math.max(0, p.segments.indexOf(now) - 1)];
  const bg = interpolateColors(frame - at(now.start), [0, 12], [moodOf(before).bg, moodOf(now).bg]);
  return (
    <AbsoluteFill style={{ background: bg }}>
      {p.segments.map((seg, i) => {
        const from = at(seg.start);
        const dur = Math.max(1, at(seg.end) - from);
        return (
          <Sequence key={i} from={from} durationInFrames={dur} layout="none">
            <SegmentView seg={seg} dur={dur} handle={p.handle} fps={fps} />
          </Sequence>
        );
      })}
      <div style={{ position: "absolute", left: 0, top: 0, height: 12, width: `${(frame / durationInFrames) * 100}%`, background: COL.orange }} />
      {p.handle && (
        <div style={{ position: "absolute", top: 120, width: "100%", textAlign: "center", fontFamily: FONT.hindi, fontWeight: 700, fontSize: 34, color: "rgba(0,0,0,.45)" }}>
          {p.handle}
        </div>
      )}
      {p.audio && (
        <Sequence from={at(p.lead)}>
          <Audio src={staticFile(p.audio)} />
        </Sequence>
      )}
    </AbsoluteFill>
  );
};

const SegmentView: React.FC<{ seg: Segment; dur: number; handle: string; fps: number }> = ({ seg, dur, handle, fps }) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill>
      <World seg={seg} f={f} dur={dur} />
      <Top seg={seg} f={f} />
      {seg.kind === "ask" && <Follow f={f} handle={handle} />}
      {(seg.kind === "hook" || seg.kind === "scene") && <Subtitle seg={seg} f={f} fps={fps} />}
    </AbsoluteFill>
  );
};
