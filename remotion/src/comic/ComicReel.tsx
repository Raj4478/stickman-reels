import React from "react";
import { AbsoluteFill, Audio, Easing, Freeze, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { COL, FONT, ease, shakeAt } from "../engine/fx";
import { Follow, ReelProps, Segment, Subtitle, useFonts } from "../StickReel";
import { Emoji } from "./Emoji";
import { HEAD, Kid, hitsOf } from "./Kid";
import { room } from "./rooms";

// A comic Reel (reel/comic.py): one room, one cartoon kid behind a table, talking straight to the viewer.
// The title strip with two emoji stays at the top while the kid rants; every line cuts to a new framing
// (medium, then close, like a sitcom), the eyes and eyebrows do the acting, the punchline snaps the camera in
// and a "ba-dum-tss" follows it; then the question for the comments and the Like/Subscribe/Follow/Share card.
// The segments are the story-Reel ones: hook = the setup, scene = a rant line, lesson = the punchline, ask.

const W = 1080;
const H = 1920;
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

type Cam = { x: number; y: number; z: number };
const MEDIUM: Cam = { x: 540, y: 950, z: 1.1 };
const CLOSE: Cam = { x: 540, y: 905, z: 1.32 };
const TIGHT: Cam = { x: HEAD.x, y: HEAD.y + 40, z: 1.5 };

// The framing of each line: medium and close alternate; big emotions and the punchline go tighter
const shotOf = (seg: Segment, i: number): { from: Cam; to: Cam; snap?: boolean } => {
  if (seg.kind === "hook") return { from: MEDIUM, to: { ...MEDIUM, z: 1.16 } };
  if (seg.kind === "lesson") return { from: CLOSE, to: TIGHT, snap: true };
  if (seg.kind === "ask") return { from: MEDIUM, to: MEDIUM };
  if (["shock", "cry", "angry"].includes(seg.face ?? "")) return { from: CLOSE, to: { ...TIGHT, z: 1.42 } };
  if (seg.speaker === "other") return { from: { ...MEDIUM, x: 590 }, to: { ...MEDIUM, x: 600, z: 1.14 } };
  return i % 2 ? { from: CLOSE, to: { ...CLOSE, z: 1.38 } } : { from: MEDIUM, to: { ...MEDIUM, z: 1.15 } };
};

const camAt = (seg: Segment, i: number, f: number, dur: number): Cam => {
  const s = shotOf(seg, i);
  const t = s.snap
    ? interpolate(f, [0, 6], [0, 1], { ...clamp, easing: Easing.out(Easing.back(1.6)) })
    : interpolate(f, [0, dur], [0, 1], { ...clamp, easing: Easing.inOut(Easing.quad) });
  return { x: s.from.x + (s.to.x - s.from.x) * t, y: s.from.y + (s.to.y - s.from.y) * t, z: s.from.z + (s.to.z - s.from.z) * t };
};

const view = (c: Cam, depth = 1, shake = { x: 0, y: 0, r: 0 }) => {
  const z = 1 + (c.z - 1) * depth;
  const x = W / 2 + (c.x - W / 2) * depth;
  const y = H / 2 + (c.y - H / 2) * depth;
  return `translate(${shake.x}px, ${shake.y}px) translate(${W / 2}px, ${H / 2}px) rotate(${shake.r}deg) scale(${z}) translate(${-x}px, ${-y}px)`;
};

// How the kid acts a segment (the setup and punchline get theirs from reel/build.py)
const actOf = (seg: Segment) => ({
  face: seg.kind === "ask" ? "happy" : seg.face ?? "deadpan",
  gesture: seg.kind === "ask" ? "point_viewer" : seg.gesture ?? "talk",
  look: seg.kind === "ask" ? "viewer" : seg.look ?? "viewer",
});

const TitleStrip: React.FC<{ title: string; emoji: string; f: number }> = ({ title, emoji, f }) => {
  const pop = interpolate(f, [0, 4, 8], [1.08, 0.98, 1], clamp);
  return (
    <div style={{ position: "absolute", top: 250, left: 0, right: 0, display: "flex", justifyContent: "center", transform: `scale(${pop})` }}>
      <div style={{ background: "#fff", padding: "12px 34px", borderRadius: 14, boxShadow: "0 8px 0 rgba(0,0,0,.18)", display: "flex", alignItems: "center", gap: 14,
        fontFamily: FONT.hindi, fontWeight: 700, fontSize: 66, lineHeight: 1.25, color: COL.ink }}>
        <span>{title}</span>
        {emoji !== "none" && <span style={{ display: "flex", gap: 4 }}><Emoji name={emoji} size={74} /><Emoji name={emoji} size={74} /></span>}
      </div>
    </div>
  );
};

// Someone calling from another room: shout lines at the edge of the frame on the side the kid looks to
const Shout: React.FC<{ f: number }> = ({ f }) => {
  const k = 0.6 + Math.abs(Math.sin(f * 0.5)) * 0.4;
  return (
    <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>
      <g stroke={COL.red} strokeWidth={12} strokeLinecap="round" opacity={ease(f, 0, 4)}>
        <path d={`M${1070 - 60 * k},720 L1070,690`} />
        <path d={`M${1070 - 80 * k},800 L1070,800`} />
        <path d={`M${1070 - 60 * k},880 L1070,910`} />
      </g>
    </svg>
  );
};

const AskCard: React.FC<{ text: string; f: number }> = ({ text, f }) => {
  const s = interpolate(f - 2, [0, 6, 10], [0.4, 1.05, 1], clamp);
  return (
    <div style={{ position: "absolute", top: 230, left: 70, right: 70, display: "flex", justifyContent: "center" }}>
      <div style={{ transform: `scale(${s}) rotate(-1.5deg)`, opacity: ease(f, 2, 7), background: "#fff", border: `7px solid ${COL.ink}`, borderRadius: 26,
        boxShadow: `12px 12px 0 ${COL.ink}`, padding: "26px 36px", textAlign: "center", fontFamily: FONT.hindi, fontWeight: 800,
        fontSize: text.length > 34 ? 56 : 64, lineHeight: 1.3, color: COL.ink }}>{text}</div>
    </div>
  );
};

// Sound for one segment: typing, a slam, a cartoon boing for a shock, a sad horn for tears, the punch's whip
const Sounds: React.FC<{ seg: Segment; dur: number }> = ({ seg, dur }) => {
  const act = actOf(seg);
  const cues: [number, string, number][] = [];
  if (seg.kind === "hook") cues.push([0, "pop", 0.6]);
  if (act.gesture === "type") for (let at = 2; at < dur - 10; at += 40) cues.push([at, "typing", 0.22]);
  hitsOf(act.gesture).forEach((h) => cues.push([h, "thud", 0.7]));
  if (act.face === "shock") cues.push([1, "boing", 0.5]);
  if (act.face === "cry") cues.push([4, "sad", 0.32]);
  if (seg.kind === "lesson") cues.push([0, "whip", 0.4]);
  if (seg.kind === "ask") [0, 1, 2, 3].forEach((i) => cues.push([14 + i * 9, "pop", 0.55]));
  return (
    <>
      {cues.filter(([at]) => at < dur).map(([at, name, v], i) => (
        <Sequence key={i} from={at} durationInFrames={Math.max(1, dur - at)} layout="none">
          <Audio src={staticFile(`sfx/${name}.wav`)} volume={v} />
        </Sequence>
      ))}
    </>
  );
};

const Line: React.FC<{ p: ReelProps; seg: Segment; i: number; dur: number; sound?: boolean }> = ({ p, seg, i, dur, sound = true }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const leadFrames = Math.round(p.lead * fps);
  const start = Math.round(seg.start * fps);
  const level = seg.speaker === "other" ? 0 : (p.mouth ?? [])[start + f - leadFrames] ?? 0;
  const act = actOf(seg);
  const where = room(p.place, start + f);
  const cam = camAt(seg, i, f, dur);
  const shake = shakeAt(f, [...hitsOf(act.gesture), ...(seg.kind === "lesson" ? [3] : [])], 14);
  return (
    <AbsoluteFill style={{ background: "#ead3c2" }}>
      <AbsoluteFill style={{ transform: view(cam, 0.7, { x: shake.x * 0.5, y: shake.y * 0.5, r: 0 }), transformOrigin: "0 0", filter: "blur(2.5px)" }}>
        <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ position: "absolute", overflow: "visible" }}>{where.back}</svg>
      </AbsoluteFill>
      <AbsoluteFill style={{ transform: view(cam, 1, shake), transformOrigin: "0 0" }}>
        <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ position: "absolute", overflow: "visible" }}>
          <Kid f={f} clock={start + f} face={act.face} look={act.look} gesture={act.gesture} mouth={Math.min(1, level)} girl={p.hero === "girl"} table={where.table} />
        </svg>
      </AbsoluteFill>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0) 62%, rgba(0,0,0,.16) 100%)" }} />
      {seg.speaker === "other" && <Shout f={f} />}
      {seg.kind === "ask" ? <AskCard text={seg.text} f={f} /> : <TitleStrip title={p.segments[0].title ?? ""} emoji={p.emoji ?? "sob"} f={seg.kind === "hook" ? f : 99} />}
      {seg.kind === "ask" ? <Follow f={f} handle={p.handle} line="रोज़ नई हँसी, रोज़ नई सीख" /> : <Subtitle seg={seg} f={f} fps={fps} top={1540} />}
      {sound && <Sounds seg={seg} dur={dur} />}
    </AbsoluteFill>
  );
};

export const ComicReel: React.FC<ReelProps> = (p) => {
  useFonts();
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const at = (t: number) => Math.round(t * fps);
  const LOOP = 14; // the last frames dissolve into the opening frame, so a replay feels seamless
  const hook = p.segments[0];
  const punch = p.segments.find((s) => s.kind === "lesson");
  // "ba-dum-tss" right after the punchline's last word
  const lastWord = punch?.words?.length ? punch.words[punch.words.length - 1] + 0.5 : punch ? punch.end - 0.6 : 0;
  const rimshot = punch ? at(Math.min(lastWord, punch.end)) : -1;
  const speechEnd = durationInFrames - at(2.2);
  return (
    <AbsoluteFill style={{ background: "#ead3c2" }}>
      {p.segments.map((seg, i) => {
        const from = at(seg.start);
        const dur = Math.max(1, at(seg.end) - from);
        return (
          <Sequence key={i} from={from} durationInFrames={dur} layout="none">
            <Line p={p} seg={seg} i={i} dur={dur} />
          </Sequence>
        );
      })}
      <Sequence from={durationInFrames - LOOP} durationInFrames={LOOP} layout="none">
        <AbsoluteFill style={{ opacity: interpolate(frame, [durationInFrames - LOOP, durationInFrames - 1], [0, 1]) }}>
          <Freeze frame={0}>
            <Line p={p} seg={hook} i={0} dur={Math.max(1, at(hook.end) - at(hook.start))} sound={false} />
          </Freeze>
        </AbsoluteFill>
      </Sequence>
      {p.handle && (
        <div style={{ position: "absolute", top: 150, width: "100%", textAlign: "center", fontFamily: FONT.hindi, fontWeight: 700, fontSize: 34, color: "rgba(0,0,0,.45)" }}>
          {p.handle}
        </div>
      )}
      {rimshot > 0 && (
        <Sequence from={rimshot} layout="none">
          <Audio src={staticFile("sfx/rimshot.wav")} volume={0.75} />
        </Sequence>
      )}
      {p.audio && (
        <Sequence from={at(p.lead)}>
          <Audio src={staticFile(p.audio)} />
        </Sequence>
      )}
      {p.music && (
        <Audio
          src={staticFile(p.music)}
          // a light bouncy bed under the voice that rises for the end card
          volume={(f) => interpolate(f, [0, 8, speechEnd, speechEnd + 15, durationInFrames - 10, durationInFrames], [0, 0.08, 0.08, 0.24, 0.24, 0], clamp)}
        />
      )}
    </AbsoluteFill>
  );
};
