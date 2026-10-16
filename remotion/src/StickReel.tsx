import React, { useEffect, useState } from "react";
import {
  AbsoluteFill, Audio, Freeze, Sequence, continueRender, delayRender, interpolate, staticFile, useCurrentFrame, useVideoConfig,
} from "remotion";
import { Act, CAST, CX, Figure, GROUND, H, HERO, HIP, PropView, S, W, act, hipFor, watcher } from "./actions";
import { cameraAt, entrance, layerTransform, tiltTransform } from "./director";
import { COL, FONT, ease, shakeAt } from "./engine/fx";
import { Actor, Joints } from "./engine/stick";
import { Glow, place } from "./places";

// One Reel, filmed like a short: the hook (title on screen from the first frame, the story's most dramatic
// action under a push-in) -> 4-6 beats, each with its own shot, place, cast and sound -> the lesson card ->
// the question and the follow card, whose last frames dissolve back into the opening so the Reel loops.

export type Segment = {
  kind: "hook" | "scene" | "lesson" | "ask";
  text: string;
  start: number;
  end: number;
  words?: number[];
  title?: string;
  name?: string;
  part?: string;
  caption?: string;
  action?: string;
  prop?: string;
  mood?: string;
  with?: string;
  place?: string;
  shot?: string;
  transition?: string;
};
export type ReelProps = { audio: string | null; music?: string | null; lead: number; handle: string; duration: number; segments: Segment[] };

const MOOD: Record<string, { bg: string; accent: string; tint: string }> = {
  calm: { bg: "#f6f1e6", accent: COL.blue, tint: "rgba(0,0,0,0)" },
  happy: { bg: "#fff1cf", accent: COL.orange, tint: "rgba(255,190,60,.12)" },
  sad: { bg: "#e3e8ef", accent: "#5b6b82", tint: "rgba(70,90,130,.18)" },
  tense: { bg: "#fbe3dc", accent: COL.red, tint: "rgba(200,40,30,.12)" },
};
const moodOf = (s: Segment) => MOOD[s.kind === "lesson" ? "happy" : s.kind === "hook" ? "tense" : s.mood ?? "calm"] ?? MOOD.calm;
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

// Big words at the top that slam in (no letter-spacing: it breaks Hindi shaping). `instant` shows them fully on
// frame 0, for the hook: the first frame must already say something.
const Slam: React.FC<{ f: number; children: React.ReactNode; size: number; color?: string; bar?: string; instant?: boolean; outline?: boolean }> = ({
  f, children, size, color = COL.ink, bar, instant, outline,
}) => {
  const s = instant ? interpolate(f, [0, 4, 8], [1.12, 0.97, 1], { extrapolateRight: "clamp" }) : interpolate(f, [0, 5, 9, 13], [1.7, 0.94, 1.03, 1], { extrapolateRight: "clamp" });
  return (
    <div style={{ transform: `scale(${s}) rotate(${instant ? -1.5 : (1 - ease(f, 0, 10)) * -4}deg)`, opacity: instant ? 1 : ease(f, 0, 4), textAlign: "center" }}>
      <span style={{
        fontFamily: FONT.hindi, fontWeight: 800, fontSize: size, lineHeight: 1.32, color,
        background: bar ? `linear-gradient(transparent 58%, ${bar} 58%, ${bar} 92%, transparent 92%)` : undefined,
        WebkitTextStroke: outline ? `2px ${COL.ink}` : undefined, paintOrder: "stroke fill",
        textShadow: outline ? `0 6px 0 ${COL.ink}` : undefined,
        boxDecorationBreak: "clone", WebkitBoxDecorationBreak: "clone", padding: "0 12px",
      }}>{children}</span>
    </div>
  );
};

const Top: React.FC<{ seg: Segment; f: number; dark: boolean }> = ({ seg, f, dark }) => {
  const mood = moodOf(seg);
  const ink = dark ? "#fff" : COL.ink;
  let body: React.ReactNode = null;
  if (seg.kind === "hook") {
    body = (
      <div>
        {seg.part && (
          <div style={{ display: "inline-block", marginBottom: 18, background: COL.red, color: "#fff", fontFamily: FONT.hindi, fontWeight: 800,
            fontSize: 40, padding: "4px 26px", borderRadius: 30 }}>भाग {seg.part}</div>
        )}
        <Slam f={f} size={124} bar={COL.yellow} instant>{seg.title}</Slam>
      </div>
    );
  }
  if (seg.kind === "scene") body = <Slam f={f - 3} size={seg.caption && seg.caption.length > 18 ? 92 : 108} color={dark ? COL.yellow : mood.accent}>{seg.caption}</Slam>;
  if (seg.kind === "ask") body = <Slam f={f - 3} size={seg.text.length > 40 ? 64 : 76} color={ink}>{seg.text}</Slam>;
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
  return <div style={{ position: "absolute", left: 70, right: 70, top: 230, height: 500, display: "flex", alignItems: "center", justifyContent: "center" }}>{body}</div>;
};

// Spoken words, a few at a time, with the word being spoken highlighted (Whisper word times when available)
const Subtitle: React.FC<{ seg: Segment; f: number; fps: number }> = ({ seg, f, fps }) => {
  const words = seg.text.split(/\s+/).filter(Boolean);
  if (!words.length) return null;
  const now = seg.start + f / fps;
  let current = 0;
  if (seg.words && seg.words.length === words.length) {
    seg.words.forEach((t, i) => {
      if (now >= t) current = i;
    });
  } else {
    const weights = words.map((w) => w.length + 1);
    const total = weights.reduce((a, b) => a + b, 0);
    const pos = ((now - seg.start) / Math.max(0.5, Math.min(seg.end - seg.start, total * 0.075))) * total;
    let acc = 0;
    current = words.length - 1;
    for (let i = 0; i < words.length; i++) {
      acc += weights[i];
      if (acc > pos) {
        current = i;
        break;
      }
    }
  }
  const CHUNK = 5;
  const start = Math.floor(current / CHUNK) * CHUNK;
  const chunk = words.slice(start, start + CHUNK);
  return (
    <div style={{ position: "absolute", left: 60, right: 60, top: 1395, display: "flex", justifyContent: "center", opacity: ease(f, 0, 4) }}>
      <div style={{ background: "#fff", border: `6px solid ${COL.ink}`, borderRadius: 22, padding: "14px 30px", textAlign: "center",
        fontFamily: FONT.hindi, fontWeight: 700, fontSize: 52, lineHeight: 1.4, color: COL.ink, boxShadow: `8px 8px 0 rgba(0,0,0,.18)` }}>
        {chunk.map((w, i) => {
          const on = start + i === current;
          return (
            <span key={start + i} style={{ display: "inline-block", margin: "0 0.16em", color: on ? COL.orange : start + i < current ? COL.ink : "#8a8a8a",
              transform: on ? "scale(1.12) translateY(-3px)" : undefined }}>{w}</span>
          );
        })}
      </div>
    </div>
  );
};

const Follow: React.FC<{ f: number; handle: string; part?: string }> = ({ f, handle, part }) => {
  const s = interpolate(f - 10, [0, 6, 10, 14], [0.3, 1.08, 0.97, 1], { extrapolateRight: "clamp" });
  return (
    <div style={{ position: "absolute", left: 0, right: 0, top: 1400, display: "flex", flexDirection: "column", alignItems: "center", gap: 18 }}>
      <div style={{ transform: `scale(${s})`, opacity: ease(f, 10, 14), background: COL.red, color: "#fff", fontFamily: FONT.hindi, fontWeight: 800,
        fontSize: 58, padding: "16px 50px", borderRadius: 60, border: `6px solid ${COL.ink}`, boxShadow: `8px 8px 0 ${COL.ink}` }}>
        {part === "1/2" ? "भाग 2 के लिए फ़ॉलो करें" : "फ़ॉलो करें"}
      </div>
      <div style={{ opacity: ease(f, 18, 26), fontFamily: FONT.hindi, fontWeight: 700, fontSize: 42, color: COL.ink, background: "rgba(255,255,255,.85)", padding: "4px 18px", borderRadius: 14 }}>
        रोज़ एक नई सीख{handle ? ` · ${handle}` : ""}
      </div>
    </div>
  );
};

const beatOf = (seg: Segment) => ({
  action: seg.kind === "scene" || seg.kind === "hook" ? seg.action ?? "point" : seg.kind === "lesson" ? "point" : "think",
  shot: seg.kind === "hook" ? "push_in" : seg.kind === "lesson" ? "low_angle" : seg.kind === "ask" ? "medium" : seg.shot ?? "medium",
  place: seg.kind === "scene" ? seg.place : "plain",
});

const World: React.FC<{ seg: Segment; f: number; dur: number }> = ({ seg, f, dur }) => {
  const beat = beatOf(seg);
  const other = seg.with && seg.with !== "none" ? CAST[seg.with] : undefined;
  const a: Act = act(beat.action, f, dur, other);
  const where = place(beat.place, f);
  const prop = seg.kind === "scene" && seg.prop && seg.prop !== "none" && a.propAt !== null ? seg.prop : null;
  // a cast member watches one-person beats from the side, unless the prop or action needs that space
  const watchX = !a.second && other && a.watcherAt != null ? a.watcherAt : null;
  const propX = prop && watchX != null && Math.abs((a.propAt?.x ?? 880) - watchX) < 200 ? W - (a.propAt?.x ?? 880) : a.propAt?.x ?? 880;
  const second: Figure | undefined = a.second ?? (watchX != null ? watcher(watchX, seg.mood) : undefined);
  const hold = (j: Joints) => (
    <>
      {a.hold?.(j)}
      {prop === "rain_cloud" && <PropView prop={prop} x={0} f={f} dur={dur} head={j.headC} />}
    </>
  );
  const cam = cameraAt(beat.shot, f, dur, a.hits);
  const enter = entrance(seg.kind === "scene" ? seg.transition : "cut", f);
  const shake = shakeAt(f, a.hits, 16);
  const c = { ...cam, x: cam.x - enter.x, z: cam.z * enter.z };
  const layer = (depth: number, children: React.ReactNode) => (
    <AbsoluteFill style={{ transform: layerTransform(c, depth, depth === 1 ? shake : { x: shake.x * 0.4, y: shake.y * 0.4, r: 0 }), transformOrigin: "0 0" }}>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ position: "absolute", overflow: "visible" }}>{children}</svg>
    </AbsoluteFill>
  );
  const otherScale = other?.scale ?? S;
  return (
    <AbsoluteFill style={{ transform: tiltTransform(c), transformOrigin: "50% 60%", filter: enter.blur > 0.5 ? `blur(${enter.blur}px)` : undefined }}>
      {where.far && layer(0.45, where.far)}
      {where.mid && layer(0.75, where.mid)}
      {layer(1, (
        <>
          {where.glow && <Glow x={CX} y={HIP - 120} />}
          {!where.mid && (
            <path d={`M-400,${GROUND} Q300,${GROUND - 6} 540,${GROUND} T1480,${GROUND}`} stroke={COL.ink} strokeWidth={7} fill="none" strokeLinecap="round" />
          )}
          <ellipse cx={CX} cy={GROUND + 6} rx={150} ry={14} fill="rgba(0,0,0,.1)" />
          {a.under}
          {prop && prop !== "rain_cloud" && <PropView prop={prop} x={propX} f={f} dur={dur} />}
          {second && (
            <Actor f={f} keys={second.keys} mod={second.mod} color={other?.color ?? COL.blue} face={second.face} facing={second.facing}
              scale={otherScale} base={{ y: hipFor(otherScale) }} accessory={other?.accessory} label={f < 40 ? other?.label : undefined}>
              {second.hold}
            </Actor>
          )}
          <Actor f={f} keys={a.keys} mod={a.mod} color={HERO.color} accessory={HERO.accessory} face={a.face} facing={a.facing} scale={S}
            base={{ y: HIP, ...a.base }} label={seg.kind === "hook" && seg.name && f > 6 ? seg.name : undefined}>
            {hold}
          </Actor>
          {a.over}
        </>
      ))}
      {enter.flash > 0 && <AbsoluteFill style={{ background: "#fff", opacity: enter.flash }} />}
    </AbsoluteFill>
  );
};

// Sound for one beat: the action's effects, the caption's whoosh and the transition's swish
const BeatSound: React.FC<{ seg: Segment; f: number; dur: number }> = ({ seg, f, dur }) => {
  const beat = beatOf(seg);
  const a = act(beat.action, f, dur, seg.with && seg.with !== "none" ? CAST[seg.with] : undefined);
  const cues: [number, string, number][] = a.sfx.map(([at, name, v]) => [at, name, v ?? 0.5]);
  if (seg.kind === "scene") {
    cues.push([2, "whoosh", 0.3]);
    if (seg.transition === "whip") cues.push([0, "whip", 0.6]);
    if (seg.transition === "zoom") cues.push([0, "swoosh_up", 0.45]);
    if (seg.transition === "flash") cues.push([0, "thud", 0.5]);
  }
  if (seg.kind === "hook") cues.push([0, "pop", 0.6]);
  if (seg.kind === "lesson") cues.push([2, "ding", 0.6]);
  if (seg.kind === "ask") cues.push([10, "pop", 0.6]);
  return (
    <>
      {cues.filter(([at]) => at < dur).map(([at, name, v], i) => (
        <Sequence key={i} from={Math.max(0, Math.round(at))} durationInFrames={Math.max(1, dur - Math.round(at))} layout="none">
          <Audio src={staticFile(`sfx/${name}.wav`)} volume={v} />
        </Sequence>
      ))}
    </>
  );
};

const SegmentView: React.FC<{ seg: Segment; dur: number; handle: string; fps: number; sound?: boolean }> = ({ seg, dur, handle, fps, sound = true }) => {
  const f = useCurrentFrame();
  const where = place(beatOf(seg).place, f);
  const mood = moodOf(seg);
  return (
    <AbsoluteFill style={{ background: mood.bg }}>
      <World seg={seg} f={f} dur={dur} />
      <AbsoluteFill style={{ background: mood.tint, pointerEvents: "none" }} />
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 55%, rgba(0,0,0,0) 60%, rgba(0,0,0,.18) 100%)" }} />
      <Top seg={seg} f={f} dark={!!where.dark} />
      {seg.kind === "ask" && <Follow f={f} handle={handle} part={seg.part} />}
      {(seg.kind === "hook" || seg.kind === "scene") && <Subtitle seg={seg} f={f} fps={fps} />}
      {sound && <BeatSound seg={seg} f={f} dur={dur} />}
    </AbsoluteFill>
  );
};

export const StickReel: React.FC<ReelProps> = (p) => {
  useFonts();
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const at = (t: number) => Math.round(t * fps);
  const hook = p.segments[0];
  const hookDur = Math.max(1, at(hook.end) - at(hook.start));
  const LOOP = 14; // the last frames dissolve into the opening frame, so a replay feels seamless
  const speechEnd = durationInFrames - at(2.2); // the voice ends TAIL seconds before the end (reel/build.py)
  return (
    <AbsoluteFill style={{ background: MOOD.calm.bg }}>
      {p.segments.map((seg, i) => {
        const from = at(seg.start);
        const dur = Math.max(1, at(seg.end) - from);
        return (
          <Sequence key={i} from={from} durationInFrames={dur} layout="none">
            <SegmentView seg={seg} dur={dur} handle={p.handle} fps={fps} />
          </Sequence>
        );
      })}
      <Sequence from={durationInFrames - LOOP} durationInFrames={LOOP} layout="none">
        <AbsoluteFill style={{ opacity: interpolate(frame, [durationInFrames - LOOP, durationInFrames - 1], [0, 1]) }}>
          <Freeze frame={0}>
            <SegmentView seg={hook} dur={hookDur} handle={p.handle} fps={fps} sound={false} />
          </Freeze>
        </AbsoluteFill>
      </Sequence>
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
      {p.music && (
        <Audio
          src={staticFile(p.music)}
          // the music sits under the voice and rises for the end card
          volume={(f) => interpolate(f, [0, 8, speechEnd, speechEnd + 15, durationInFrames - 10, durationInFrames], [0, 0.11, 0.11, 0.3, 0.3, 0], {
            extrapolateLeft: "clamp", extrapolateRight: "clamp",
          })}
        />
      )}
    </AbsoluteFill>
  );
};
