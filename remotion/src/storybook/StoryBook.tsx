import React from "react";
import { AbsoluteFill, Audio, Img, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { duckCurve } from "../duck";
import { FONT } from "../engine/fx";
import { SafeZones } from "../SafeZones";
import { Follow, ReelProps, Segment, useFonts } from "../StickReel";
import { Atmosphere, glowOf } from "./Atmosphere";
import { LivingPicture, MOVES } from "./Living";

// A storybook Reel (reel/storybook.py): a warm narrator tells a short original moral story over living paintings.
// Each line shows two moments of its scene (a cut on a word halfway through), each painting filmed in 3D by a
// drifting camera using its depth map (Living.tsx), with moving atmosphere over it (Atmosphere.tsx). Pictures
// cross-fade, the series strip stays at the top and the narration runs as big word-by-word Roman Hinglish captions,
// one caption word for each spoken word, the spoken word in yellow. The question and the follow card close it.

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const FADE = 8; // frames of cross-fade into each new picture
const YELLOW = "#ffd43b";

// Pictures are shared: the question keeps the moral's picture
const pictureOf = (p: ReelProps, i: number): { src: string; depth?: string } | undefined => {
  const seg = p.segments[i];
  if (seg.image) return { src: seg.image, depth: seg.depth };
  const prev = i > 0 ? p.segments[i - 1] : undefined;
  if (prev?.image_b) return { src: prev.image_b, depth: prev.depth_b };
  return i > 0 ? pictureOf(p, i - 1) : undefined;
};

// Where a line cuts to its second moment: on the start of the word nearest its middle (lines over 2 seconds)
const cutOf = (seg: Segment, fps: number, dur: number): number | null => {
  if (!seg.image_b || dur < 2 * fps) return null;
  const marks = (seg.words ?? []).map((t) => Math.round((t - seg.start) * fps)).filter((m) => m > fps * 0.8 && dur - m > fps * 0.8);
  if (!marks.length) return Math.round(dur / 2);
  return marks.reduce((best, m) => (Math.abs(m - dur / 2) < Math.abs(best - dur / 2) ? m : best));
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
  // one caption word for each spoken word (reel/hinglish.py): the word lights up when it is said
  let current = 0;
  if (spoken.length) {
    let heard = 0;
    spoken.forEach((t, k) => {
      if (now >= t) heard = k;
    });
    current = spoken.length === words.length ? heard : Math.min(words.length - 1, Math.floor(((heard + 0.5) * words.length) / spoken.length));
  } else {
    current = Math.min(words.length - 1, Math.floor(((now - seg.start) / Math.max(0.5, seg.end - seg.start)) * words.length));
  }
  const MAX = 22; // one line at 68 px: a second line would sit too close to the bottom UI
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
    <div style={{ position: "absolute", left: 50, right: 50, top: 1290, display: "flex", justifyContent: "center", flexWrap: "wrap", gap: "0 0.32em",
      fontFamily: FONT.hindi, fontWeight: 800, fontSize: 68, lineHeight: 1.25, textAlign: "center" }}>
      {chunk.map((w, i) => {
        const on = start + i === current;
        return (
          <span key={start + i} style={{ color: on ? YELLOW : "#fff", WebkitTextStroke: "3px rgba(0,0,0,.85)", paintOrder: "stroke",
            textShadow: "0 6px 18px rgba(0,0,0,.75)", display: "inline-block" }}>{w}</span>
        );
      })}
    </div>
  );
};

const AskCard: React.FC<{ text: string; f: number }> = ({ text, f }) => (
  <div style={{ position: "absolute", top: 1010, left: 70, right: 70, display: "flex", justifyContent: "center",
    opacity: interpolate(f, [2, 10], [0, 1], clamp), transform: `scale(${interpolate(f, [2, 10], [0.9, 1], clamp)})` }}>
    <div style={{ background: "rgba(255,255,255,.95)", borderRadius: 28, padding: "28px 38px", textAlign: "center", fontFamily: FONT.hindi, fontWeight: 800,
      fontSize: text.length > 40 ? 58 : 66, lineHeight: 1.3, color: "#1b1b1f", boxShadow: "0 16px 40px rgba(0,0,0,.45)" }}>{text}</div>
  </div>
);

const Line: React.FC<{ p: ReelProps; seg: Segment; i: number; dur: number }> = ({ p, seg, i, dur }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const early = i > 0 ? FADE : 0; // the picture fades in before the line starts
  const f = frame - early; // < 0 while fading in: the line has not started, so no caption yet
  const pic = pictureOf(p, i);
  const newPicture = i === 0 || seg.image !== undefined;
  const cut = cutOf(seg, fps, dur);
  const second = cut !== null && f >= cut - 4 && seg.image_b ? { src: seg.image_b, depth: seg.depth_b } : null;
  const fadeB = second && cut !== null ? interpolate(f, [cut - 4, cut + 2], [0, 1], clamp) : 0;
  const seed = `line-${i}`;
  const dim = seg.kind === "ask" ? interpolate(f, [0, 10], [0, 0.45], clamp) : 0;
  const glow = glowOf(seg.fx, frame, seed);
  // the first moment's camera runs from the fade-in to the cut (or the end); the second's from the cut to the end
  const firstLen = (cut ?? dur) + early;
  const move = MOVES[(i * 2) % MOVES.length];
  const moveB = MOVES[(i * 2 + 1) % MOVES.length];
  return (
    <AbsoluteFill>
      {pic && (
        <AbsoluteFill style={{ opacity: newPicture && i > 0 ? interpolate(frame, [0, FADE], [0, 1], clamp) : 1 }}>
          {fadeB < 1 && <LivingPicture src={pic.src} depth={pic.depth} move={seg.kind === "ask" ? "pull" : move} t={frame / Math.max(1, seg.kind === "ask" ? firstLen * 1.4 : firstLen)} glow={glow} />}
          {second && cut !== null && (
            <AbsoluteFill style={{ opacity: fadeB }}>
              <LivingPicture src={second.src} depth={second.depth} move={moveB} t={(f - cut + 4) / Math.max(1, dur - cut + 4)} glow={glow} />
            </AbsoluteFill>
          )}
          {dim > 0 && <AbsoluteFill style={{ background: `rgba(10,6,4,${dim})` }} />}
        </AbsoluteFill>
      )}
      <Atmosphere fx={seg.fx} f={frame} seed={seed} />
      {/* soft grade: darker top and bottom for the strip and the captions, a warm vignette */}
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,.55) 0%, rgba(0,0,0,0) 26%, rgba(0,0,0,0) 56%, rgba(0,0,0,.62) 82%, rgba(0,0,0,.7) 100%)" }} />
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 58%, rgba(30,12,0,.32) 100%)" }} />
      {seg.kind === "ask" ? (
        <>
          <AskCard text={seg.roman || seg.text} f={Math.max(0, f)} />
          <Follow f={Math.max(0, f)} handle={p.handle} line="रोज़ एक नई कहानी" />
        </>
      ) : (
        f >= 0 && <Captions seg={seg} f={f} fps={fps} />
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
  const src = pictureOf(p, 0)?.src;
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
