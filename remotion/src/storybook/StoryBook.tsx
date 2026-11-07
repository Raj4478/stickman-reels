import React from "react";
import { AbsoluteFill, Audio, Img, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { duckCurve } from "../duck";
import { FONT } from "../engine/fx";
import { SafeZones } from "../SafeZones";
import { Follow, ReelProps, Segment, useFonts } from "../StickReel";

// A storybook Reel (reel/storybook.py): a warm narrator tells an original moral story over painted illustrations,
// one picture per line. Each picture fills the 9:16 frame and moves slowly (a Ken Burns push or pull with a gentle
// pan, alternating direction), pictures cross-fade, the series strip stays at the top and the narration runs as big
// word-by-word Roman Hinglish captions, the spoken word in yellow. The question and the follow card close it.

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const FADE = 8; // frames of cross-fade into each new picture
const YELLOW = "#ffd43b";
const glide = (u: number) => {
  const x = Math.min(1, Math.max(0, u));
  return x * x * x * (x * (6 * x - 15) + 10);
};

// The slow camera on picture i: push in or pull out, drifting left or right, a different mix per picture
const kenBurns = (i: number, f: number, dur: number, shot?: string) => {
  const t = glide(f / Math.max(1, dur));
  const push = i % 2 === 0;
  const tight = shot === "close" || shot === "detail" ? 0.04 : 0;
  const z0 = 1.04 + tight;
  const z1 = 1.15 + tight;
  const z = push ? z0 + (z1 - z0) * t : z1 - (z1 - z0) * t;
  const dir = [1, -1, 0.5, -0.5][i % 4];
  const x = dir * 34 * (t - 0.5);
  const y = (i % 3 === 0 ? -14 : 10) * (t - 0.5);
  return `translate(${x}px, ${y}px) scale(${z})`;
};

// Pictures are shared: the question keeps the moral's picture
const pictureOf = (p: ReelProps, i: number): string | undefined => {
  const seg = p.segments[i];
  return seg.image ?? (i > 0 ? pictureOf(p, i - 1) : undefined);
};

const Picture: React.FC<{ src: string; i: number; dur: number; shot?: string; fadeIn: boolean; dim?: number }> = ({ src, i, dur, shot, fadeIn, dim = 0 }) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ opacity: fadeIn ? interpolate(f, [0, FADE], [0, 1], clamp) : 1, overflow: "hidden" }}>
      <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover", transform: kenBurns(i, f, dur + FADE, shot), transformOrigin: "50% 45%" }} />
      {dim > 0 && <AbsoluteFill style={{ background: `rgba(10,6,4,${dim})` }} />}
    </AbsoluteFill>
  );
};

// The series strip: the first word in yellow, the rest white, over a soft dark band
const SeriesStrip: React.FC<{ text: string }> = ({ text }) => {
  const [first, ...rest] = text.split(" ");
  return (
    <div style={{ position: "absolute", top: 290, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
      <div style={{ fontFamily: FONT.hindi, fontWeight: 800, fontSize: 68, lineHeight: 1.2, color: "#fff", padding: "8px 34px", borderRadius: 18,
        background: "rgba(0,0,0,.42)", textShadow: "0 4px 14px rgba(0,0,0,.6)" }}>
        <span style={{ color: YELLOW }}>{first}</span> {rest.join(" ")}
      </div>
    </div>
  );
};

// Word-by-word Roman captions, paged by characters so a page is one or two short lines; the word being said is yellow
const Captions: React.FC<{ seg: Segment; f: number; fps: number }> = ({ seg, f, fps }) => {
  const text = seg.roman || seg.text;
  const words = text.split(/\s+/).filter(Boolean);
  if (!words.length) return null;
  const now = seg.start + f / fps;
  const spoken = seg.words ?? [];
  // the Roman words share the Devanagari words' timing in proportion (the counts can differ by a word or two)
  let current = 0;
  if (spoken.length) {
    let heard = 0;
    spoken.forEach((t, k) => {
      if (now >= t) heard = k;
    });
    current = Math.min(words.length - 1, Math.floor(((heard + 0.5) * words.length) / spoken.length));
  } else {
    current = Math.min(words.length - 1, Math.floor(((now - seg.start) / Math.max(0.5, seg.end - seg.start)) * words.length));
  }
  const MAX = 26;
  const pages: number[] = [0];
  let len = 0;
  words.forEach((w, i) => {
    if (i > pages[pages.length - 1] && len + w.length + 1 > MAX) {
      pages.push(i);
      len = 0;
    }
    len += w.length + 1;
  });
  const page = pages.filter((p) => p <= current).length - 1;
  const start = pages[page];
  const chunk = words.slice(start, pages[page + 1] ?? words.length);
  return (
    <div style={{ position: "absolute", left: 50, right: 50, top: 1290, display: "flex", justifyContent: "center", flexWrap: "wrap", gap: "0 16px",
      fontFamily: FONT.hindi, fontWeight: 800, fontSize: 68, lineHeight: 1.25, textAlign: "center" }}>
      {chunk.map((w, i) => {
        const on = start + i === current;
        return (
          <span key={start + i} style={{ color: on ? YELLOW : "#fff", WebkitTextStroke: "3px rgba(0,0,0,.85)", paintOrder: "stroke",
            textShadow: "0 6px 18px rgba(0,0,0,.75)", transform: on ? "scale(1.08)" : undefined, display: "inline-block" }}>{w}</span>
        );
      })}
    </div>
  );
};

const AskCard: React.FC<{ text: string; f: number }> = ({ text, f }) => (
  <div style={{ position: "absolute", top: 520, left: 70, right: 70, display: "flex", justifyContent: "center",
    opacity: interpolate(f, [2, 10], [0, 1], clamp), transform: `scale(${interpolate(f, [2, 10], [0.9, 1], clamp)})` }}>
    <div style={{ background: "rgba(255,255,255,.95)", borderRadius: 28, padding: "28px 38px", textAlign: "center", fontFamily: FONT.hindi, fontWeight: 800,
      fontSize: text.length > 40 ? 58 : 66, lineHeight: 1.3, color: "#1b1b1f", boxShadow: "0 16px 40px rgba(0,0,0,.45)" }}>{text}</div>
  </div>
);

const Line: React.FC<{ p: ReelProps; seg: Segment; i: number; dur: number }> = ({ p, seg, i, dur }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const early = i > 0 ? FADE : 0; // the picture fades in before the line starts
  const f = Math.max(0, frame - early);
  const src = pictureOf(p, i);
  const newPicture = i === 0 || seg.image !== undefined;
  return (
    <AbsoluteFill>
      {src && <Picture src={src} i={i} dur={dur} shot={seg.shot} fadeIn={newPicture && i > 0} dim={seg.kind === "ask" ? interpolate(f, [0, 10], [0, 0.45], clamp) : 0} />}
      {/* soft grade: darker top and bottom for the strip and the captions, a warm vignette */}
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,.55) 0%, rgba(0,0,0,0) 26%, rgba(0,0,0,0) 56%, rgba(0,0,0,.62) 82%, rgba(0,0,0,.7) 100%)" }} />
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 58%, rgba(30,12,0,.32) 100%)" }} />
      {seg.kind === "ask" ? (
        <>
          <AskCard text={seg.roman || seg.text} f={f} />
          <Follow f={f} handle={p.handle} line="रोज़ एक नई कहानी" />
        </>
      ) : (
        <Captions seg={seg} f={f} fps={fps} />
      )}
    </AbsoluteFill>
  );
};

export const StoryBook: React.FC<ReelProps> = (p) => {
  useFonts();
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const at = (t: number) => Math.round(t * fps);
  const speechEnd = durationInFrames - at(2.2);
  const duck = React.useMemo(() => duckCurve(p.segments, fps, durationInFrames), [p.segments, fps, durationInFrames]);
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      {p.segments.map((seg, i) => {
        const from = at(seg.start);
        // the last line runs to the very last frame (rounding must not leave a black frame at the end)
        const dur = Math.max(1, (i === p.segments.length - 1 ? durationInFrames : at(seg.end)) - from);
        const early = i > 0 ? FADE : 0;
        return (
          <Sequence key={i} from={from - early} durationInFrames={dur + early} layout="none">
            <Line p={p} seg={seg} i={i} dur={dur} />
          </Sequence>
        );
      })}
      <SeriesStrip text={p.series_title ?? "Zindagi ki seekh"} />
      {p.handle && (
        <div style={{ position: "absolute", top: 392, width: "100%", textAlign: "center", fontFamily: FONT.hindi, fontWeight: 700, fontSize: 30, color: "rgba(255,255,255,.7)" }}>
          {p.handle}
        </div>
      )}
      <div style={{ position: "absolute", left: 0, top: 0, height: 10, width: `${(frame / durationInFrames) * 100}%`, background: YELLOW }} />
      {p.audio && (
        <Sequence from={at(p.lead)}>
          <Audio src={staticFile(p.audio)} />
        </Sequence>
      )}
      {p.music && (
        <Audio
          src={staticFile(p.music)}
          // a soft emotional bed, ducked under every word, rising for the end card
          volume={(f) => interpolate(f, [0, 8, speechEnd, speechEnd + 15, durationInFrames - 10, durationInFrames], [0, 0.12, 0.12, 0.28, 0.28, 0], clamp)
            * (f < speechEnd ? duck[f] ?? 1 : 1)}
        />
      )}
      {p.guides && <SafeZones />}
    </AbsoluteFill>
  );
};

// The grid cover: the opening picture with 2-4 teaser words inside the band that survives the 4:5 and 3:4 crops
export const StoryCover: React.FC<ReelProps> = (p) => {
  useFonts();
  const src = pictureOf(p, 0);
  const text = p.cover_text || p.series_title || "";
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      {src && <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover", transform: "scale(1.06)" }} />}
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,0) 45%, rgba(0,0,0,.7) 80%)" }} />
      <div style={{ position: "absolute", top: 1240, left: 50, right: 50, textAlign: "center", fontFamily: FONT.hindi, fontWeight: 800, fontSize: 104,
        lineHeight: 1.1, color: "#fff", WebkitTextStroke: "4px rgba(0,0,0,.85)", paintOrder: "stroke", textShadow: "0 8px 24px rgba(0,0,0,.8)" }}>
        {text.split(" ").map((w, i) => <span key={i} style={{ color: i === 0 ? YELLOW : "#fff" }}>{w} </span>)}
      </div>
    </AbsoluteFill>
  );
};
