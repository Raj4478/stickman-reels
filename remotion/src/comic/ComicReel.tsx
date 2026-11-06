import React from "react";
import { AbsoluteFill, Audio, Easing, Freeze, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { duckCurve } from "../duck";
import { COL, FONT, ease, kickAt } from "../engine/fx";
import { SafeZones } from "../SafeZones";
import { Follow, ReelProps, Segment, Subtitle, useFonts } from "../StickReel";
import { Emoji } from "./Emoji";
import { CUTAWAY_SOUND, Cutaway } from "./cutaways";
import { inkUp } from "./ink";
import { HEAD, Kid, hitsOf } from "./Kid";
import { room } from "./rooms";

// A comic Reel (reel/comic.py): a cartoon kid behind a table, talking straight to the viewer, and a picture that
// follows the words. The title strip with two emoji stays at the top; every line cuts to its visual:
//   kid       the kid in their room, medium or close like a sitcom, the eyes and eyebrows doing the acting;
//   person    the person who speaks (मम्मी in the kitchen) or is quoted, as a sepia flashback ("सर बोले थे...");
//   dream     the kid with a thought bubble;
//   cutaways  the screen, calendar, salary slip... (cutaways.tsx) with the kid talking in a corner bubble.
// The punchline snaps the camera in and a "ba-dum-tss" follows it; then the question for the comments and the
// Like/Subscribe/Follow/Share card. The segments are the story-Reel ones: hook = the setup, scene = a rant line,
// lesson = the punchline, ask.

const W = 1080;
const H = 1920;
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

type Cam = { x: number; y: number; z: number };
// Size classes. Neighbours in a cut always differ by >= 1.4x zoom or a quarter of the frame (bigChange)
const WIDE: Cam = { x: 540, y: 980, z: 0.98 }; // the whole table and the room (establishing)
const MEDIUM: Cam = { x: 540, y: 950, z: 1.1 };
const CLOSE: Cam = { x: 540, y: 905, z: 1.55 };
const XCLOSE: Cam = { x: HEAD.x, y: HEAD.y - 10, z: 2.2 }; // eyes and brows fill the frame: the reaction shot
const CLOSE_L: Cam = { x: 430, y: 905, z: 1.55 }; // the kid on the right third
const CLOSE_R: Cam = { x: 650, y: 905, z: 1.55 }; // the kid on the left third

// faces whose joke is in the eyes get the extreme close-up
const EYE_JOKES = ["shock", "side_eye", "eye_roll", "cheeky"];

// The framing of each line: medium and close alternate; eye jokes, big emotions and the punchline go tighter
const shotOf = (seg: Segment, i: number): { from: Cam; to: Cam; snap?: boolean } => {
  if (seg.kind === "hook") return { from: MEDIUM, to: { ...MEDIUM, z: 1.16 } };
  if (seg.kind === "lesson") return { from: CLOSE, to: XCLOSE, snap: true };
  if (seg.kind === "ask") return { from: MEDIUM, to: MEDIUM };
  if (seg.visual === "person") return { from: { ...MEDIUM, y: 980, z: 1.02 }, to: { ...MEDIUM, y: 970, z: 1.08 } };
  if (seg.visual === "dream") return { from: MEDIUM, to: { ...MEDIUM, z: 1.14 } }; // room for the thought bubble
  if (EYE_JOKES.includes(seg.face ?? "")) return { from: { ...XCLOSE, z: 2.05 }, to: XCLOSE };
  if (["cry", "angry", "panic"].includes(seg.face ?? "")) return { from: CLOSE, to: { ...CLOSE, z: 1.66 } };
  if (seg.speaker === "other") return { from: { ...MEDIUM, x: 590 }, to: { ...MEDIUM, x: 600, z: 1.14 } };
  return i % 2 ? { from: CLOSE, to: { ...CLOSE, z: 1.62 } } : { from: MEDIUM, to: { ...MEDIUM, z: 1.15 } };
};

// Later shots inside one line: a new framing at every cut, like a sitcom editor cutting between cameras
const ANGLES: Cam[] = [CLOSE, MEDIUM, XCLOSE, WIDE, CLOSE_L, MEDIUM, CLOSE_R];

// Rule C1 (Mr Omi's "cut only on big jumps"): a cut changes the size by 40% or moves the subject a quarter frame
export const bigChange = (a: Cam, b: Cam) => Math.max(a.z / b.z, b.z / a.z) >= 1.4 || Math.abs(a.x - b.x) * Math.min(a.z, b.z) >= 270;

// The framing of shot `part` (>= 1) of line i: the next angle that is a big change from the previous shot
const angleFor = (seg: Segment, i: number, part: number): Cam => {
  const prev = part === 1 ? shotOf(seg, i).to : angleFor(seg, i, part - 1);
  for (let k = 0; k < ANGLES.length; k++) {
    const c = ANGLES[(i + part * 2 + k) % ANGLES.length];
    if (bigChange(prev, c)) return c;
  }
  return WIDE;
};

const camAt = (seg: Segment, i: number, f: number, dur: number, part = 0, twist = 0): Cam => {
  if (part > 0) {
    const c = angleFor(seg, i, part);
    const t = interpolate(f, [0, dur], [0, 1], { ...clamp, easing: Easing.inOut(Easing.quad) });
    return { ...c, z: c.z * (1 + 0.05 * t) };
  }
  const s = shotOf(seg, i);
  const t = s.snap
    ? interpolate(f, [twist, twist + 4], [0, 1], { ...clamp, easing: Easing.out(Easing.back(1.6)) })
    : interpolate(f, [0, dur], [0, 1], { ...clamp, easing: Easing.inOut(Easing.quad) });
  return { x: s.from.x + (s.to.x - s.from.x) * t, y: s.from.y + (s.to.y - s.from.y) * t, z: s.from.z + (s.to.z - s.from.z) * t };
};

const view = (c: Cam, depth = 1, shake = { x: 0, y: 0, r: 0 }) => {
  const z = 1 + (c.z - 1) * depth;
  const x = W / 2 + (c.x - W / 2) * depth;
  const y = H / 2 + (c.y - H / 2) * depth;
  return `translate(${shake.x}px, ${shake.y}px) translate(${W / 2}px, ${H / 2}px) rotate(${shake.r}deg) scale(${z}) translate(${-x}px, ${-y}px)`;
};

// How a segment is acted and shown (the setup and punchline get theirs from reel/build.py)
const actOf = (seg: Segment, kids = false) => ({
  face: seg.kind === "ask" ? (kids ? "cheeky" : "happy") : seg.face ?? "deadpan",
  gesture: seg.kind === "ask" ? "point_viewer" : seg.gesture ?? "talk",
  look: seg.kind === "ask" ? "viewer" : seg.look ?? "viewer",
  visual: seg.kind === "ask" ? "kid" : seg.visual ?? "kid",
});
const CHARACTERS = ["kid", "person", "dream"];

// Where a line cuts to its next shot (frames from the line's start): about every 2 seconds, always on the start
// of a word, never leaving a last shot under a second. The punchline and the question stay one shot.
export const cutsOf = (seg: Segment, fps: number, dur: number): number[] => {
  // the punchline, the question and a daydream (its thought bubble needs the medium framing) stay one shot
  if (seg.kind === "lesson" || seg.kind === "ask" || seg.visual === "dream") return [0];
  const every = 2 * fps;
  const marks = seg.words?.length ? seg.words.map((t) => Math.round((t - seg.start) * fps)) : Array.from({ length: Math.floor(dur / every) }, (_, k) => (k + 1) * every);
  const cuts = [0];
  for (const m of marks) if (m - cuts[cuts.length - 1] >= every * 0.85 && dur - m >= fps) cuts.push(m);
  return cuts;
};
// Where each person is found (reel/comic.py PEOPLE)
const ROOM_OF: Record<string, string> = { mother: "kitchen", father: "living_room", teacher: "classroom", boss: "office", friend: "living_room",
  grandma: "living_room", sibling: "bedroom" };

// The kid's face in a corner bubble during a cutaway: still reacting and talking
// (bottom left: Instagram's Like/Comment/Share column covers the right edge from y ~1150)
const Bubble: React.FC<{ face: string; look: string; mouth: number; girl: boolean; f: number; clock: number; viseme?: string }> = ({ face, look, mouth, girl, f, clock, viseme }) => {
  const s = interpolate(f, [0, 6, 10], [0, 1.08, 1], clamp);
  return (
    <div style={{ position: "absolute", left: 40, top: 1105, width: 250, height: 250, borderRadius: "50%", overflow: "hidden", border: "10px solid #fff",
      boxShadow: "0 10px 0 rgba(0,0,0,.25)", background: "#ead3c2", transform: `scale(${s})` }}>
      <svg width={250} height={250} viewBox="270 560 540 540" style={{ display: "block" }}>
        <Kid f={f} clock={clock} face={face} look={look} gesture="talk" mouth={mouth} girl={girl} viseme={viseme} />
      </svg>
    </div>
  );
};

const Thought: React.FC<{ text: string; f: number }> = ({ text, f }) => {
  const s = interpolate(f, [2, 10], [0, 1], { ...clamp, easing: Easing.out(Easing.back(1.4)) });
  const bob = Math.sin(f * 0.12) * 6;
  return (
    <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>
      <g transform={`translate(0 ${bob}) translate(540 520) scale(${s}) translate(-540 -520)`}>
        <circle cx={790} cy={640} r={22} fill="#fff" stroke={COL.ink} strokeWidth={6} />
        <circle cx={830} cy={600} r={14} fill="#fff" stroke={COL.ink} strokeWidth={6} />
        <path d="M200,520 C150,440 240,380 320,410 C350,350 470,340 520,390 C570,340 700,345 730,410 C820,380 920,440 870,520 C930,590 840,660 760,630 C720,690 590,690 540,640 C480,690 350,690 320,630 C230,660 140,590 200,520 Z"
          fill="#fff" stroke={COL.ink} strokeWidth={8} strokeLinejoin="round" />
        <text x={540} y={548} textAnchor="middle" fontFamily={FONT.hindi} fontWeight={800} fontSize={text.length > 10 ? 64 : 80} fill={COL.ink}>{text}</text>
      </g>
    </svg>
  );
};

const FlashbackTag: React.FC<{ f: number }> = ({ f }) => (
  <div style={{ position: "absolute", top: 400, left: 60, transform: "rotate(-4deg)", opacity: ease(f, 0, 5), background: "#5c3d1e", color: "#fff3d6",
    fontFamily: FONT.hindi, fontWeight: 800, fontSize: 44, padding: "6px 26px", borderRadius: 12, border: "5px solid #fff3d6" }}>फ्लैशबैक</div>
);

const TitleStrip: React.FC<{ title: string; emoji: string; f: number }> = ({ title, emoji, f }) => {
  const pop = interpolate(f, [0, 4, 8], [1.08, 0.98, 1], clamp);
  return (
    <div style={{ position: "absolute", top: 285, left: 0, right: 0, display: "flex", justifyContent: "center", transform: `scale(${pop})` }}>
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
    <div style={{ position: "absolute", top: 290, left: 70, right: 70, display: "flex", justifyContent: "center" }}>
      <div style={{ transform: `scale(${s}) rotate(-1.5deg)`, opacity: ease(f, 2, 7), background: "#fff", border: `7px solid ${COL.ink}`, borderRadius: 26,
        boxShadow: `12px 12px 0 ${COL.ink}`, padding: "26px 36px", textAlign: "center", fontFamily: FONT.hindi, fontWeight: 800,
        fontSize: text.length > 34 ? 56 : 64, lineHeight: 1.3, color: COL.ink }}>{text}</div>
    </div>
  );
};

// Sound for one segment: typing, a slam, a cartoon boing for a shock, a sad horn for tears, the punch's whip
const Sounds: React.FC<{ seg: Segment; dur: number }> = ({ seg, dur }) => {
  const { fps } = useVideoConfig();
  const act = actOf(seg);
  const cues: [number, string, number][] = [];
  cutsOf(seg, fps, dur).slice(1).forEach((c) => cues.push([Math.max(0, c - 3), "whoosh", 0.12])); // a soft whoosh on every cut
  const character = CHARACTERS.includes(act.visual);
  if (seg.kind === "hook") cues.push([0, "pop", 0.6]);
  if (act.gesture === "type" && character) for (let at = 2; at < dur - 10; at += 40) cues.push([at, "typing", 0.22]);
  if (character) hitsOf(act.gesture).forEach((h) => cues.push([h, "thud", 0.7]));
  (CUTAWAY_SOUND[act.visual] ?? []).forEach((c) => cues.push(c));
  if (act.visual === "dream") cues.push([2, "swoosh_up", 0.35]);
  if (act.visual === "person" && seg.speaker !== "other") cues.push([0, "riser", 0.25]);
  if (act.face === "shock") cues.push([1, "boing", 0.5]);
  if (act.face === "cry") cues.push([4, "sad", 0.32]);
  if (act.gesture === "jump" && character) cues.push([2, "boing", 0.35]);
  if (act.gesture === "sneak" && character) for (let at = 0; at < dur - 8; at += 12) cues.push([at, "tiptoe", 0.3]);
  if (act.gesture === "eat" && character) cues.push([6, "squeak", 0.25]);
  if (act.face === "dizzy") cues.push([0, "slide_down", 0.35]);
  if (act.face === "giggle") cues.push([3, "sparkle", 0.2]);
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

const Line: React.FC<{ p: ReelProps; seg: Segment; i: number; dur: number; sound?: boolean; early?: number }> = ({ p, seg, i, dur, sound = true, early = 0 }) => {
  // the first `early` frames show frame 0 of this line: the new face lands just before the word (Mr Omi: 0-3 f)
  const f = Math.max(0, useCurrentFrame() - early);
  const { fps } = useVideoConfig();
  const leadFrames = Math.round(p.lead * fps);
  const start = Math.round(seg.start * fps);
  const voice = Math.min(1, (p.mouth ?? [])[start + f - leadFrames] ?? 0);
  // made for kids (YouTube turns comments off): the closing line is the catchphrase with a wink, not a question
  const kidsEnd = seg.kind === "ask" && p.audience === "kids";
  const act = actOf(seg, kidsEnd);
  // more shots: the line cuts to a new framing every couple of seconds, and a cutaway or another person's line
  // cuts back to the kid reacting on every other shot
  const cuts = cutsOf(seg, fps, dur);
  const part = cuts.filter((c) => c <= f).length - 1;
  const partF = f - cuts[part];
  const partDur = (cuts[part + 1] ?? dur) - cuts[part];
  const reacting = part % 2 === 1 && act.visual !== "kid" && act.visual !== "dream";
  const visual = reacting ? "kid" : act.visual;
  const face = reacting && seg.speaker === "other" ? "side_eye" : act.face;
  const person = visual === "person" && seg.who && seg.who !== "none" ? seg.who : null;
  // the person on screen moves their mouth to the voice: their own line, or the words the kid quotes
  const level = person ? voice : seg.speaker === "other" ? 0 : voice;
  const flashback = person !== null && seg.speaker !== "other";
  // the kid is where the line happens; the computer is only on the desk when the line is about it
  const computer = act.gesture === "type" || act.look === "screen";
  const where = room(person ? ROOM_OF[person] : seg.place ?? p.place, start + f, computer);
  // the punchline's twist: its third-last word (Whisper word times), else 60% into the line
  const twist = seg.kind === "lesson"
    ? (seg.words?.length ? Math.round((seg.words[Math.max(0, seg.words.length - 3)] - seg.start) * fps) : Math.round(dur * 0.6))
    : 0;
  const cam = part > 0 ? camAt(seg, i, partF, partDur, part) : camAt(seg, i, f, cuts.length > 1 ? partDur : dur, 0, twist);
  const cutaway = !CHARACTERS.includes(visual) && visual !== "person";
  const kick = kickAt(f, [...(cutaway ? [] : hitsOf(act.gesture)), ...(seg.kind === "lesson" ? [twist] : [])]);
  const shake = { x: kick, y: kick * 0.3, r: kick * 0.03 };
  const girl = p.hero === "girl";
  // a face change at the line's start hides behind a blink
  const prevFace = i > 0 ? actOf(p.segments[i - 1]).face : face;
  const swap = part === 0 && prevFace !== face;
  // the mouth shape of the word being said (reel/voice.py visemes)
  const viseme = (p.visemes ?? "")[start + f] ?? " ";
  return (
    <AbsoluteFill style={{ background: "#ead3c2" }}>
      {cutaway ? (
        <AbsoluteFill style={{ transform: `translate(540px, 800px) scale(${interpolate(f, [0, dur], [1, 1.05], clamp)}) translate(-540px, -800px)` }}>
          <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ position: "absolute" }}>
            <Cutaway name={visual} text={seg.visual_text ?? ""} screen={seg.screen} f={f} dur={dur} />
          </svg>
        </AbsoluteFill>
      ) : (
        <AbsoluteFill style={{ filter: flashback ? "sepia(0.75) saturate(0.8)" : undefined }}>
          <AbsoluteFill style={{ transform: view(cam, 0.7, { x: shake.x * 0.5, y: shake.y * 0.5, r: 0 }), transformOrigin: "0 0", filter: "blur(2.5px)" }}>
            <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ position: "absolute", overflow: "visible" }}>{where.back}</svg>
          </AbsoluteFill>
          <AbsoluteFill style={{ transform: view(cam, 1, shake), transformOrigin: "0 0" }}>
            <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ position: "absolute", overflow: "visible" }}>
              <Kid f={f} clock={start + f} face={face} look={person ? "viewer" : reacting ? "side" : act.look} gesture={act.gesture} mouth={level} girl={girl} toon={person ?? undefined} table={where.table}
                swap={swap} viseme={person || seg.speaker !== "other" ? viseme : " "} />
            </svg>
          </AbsoluteFill>
        </AbsoluteFill>
      )}
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0) ${flashback ? 48 : 62}%, rgba(0,0,0,${flashback ? 0.35 : 0.16}) 100%)` }} />
      {seg.kind === "lesson" && (
        // a spotlight: the room dims on the punchline's twist
        <AbsoluteFill style={{ background: `radial-gradient(circle at 50% 44%, rgba(20,10,30,0) 24%, rgba(20,10,30,${0.5 * ease(f, twist, twist + 4)}) 62%)` }} />
      )}
      {seg.speaker === "other" && visual === "kid" && <Shout f={f} />}
      {visual === "dream" && <Thought text={seg.visual_text ?? ""} f={f} />}
      {flashback && <FlashbackTag f={f} />}
      {cutaway && <Bubble face={act.face} look="viewer" mouth={seg.speaker === "other" ? 0 : voice} girl={girl} f={f} clock={start + f} viseme={seg.speaker === "other" ? " " : viseme} />}
      {seg.kind === "ask" && !kidsEnd ? <AskCard text={seg.text} f={f} /> : <TitleStrip title={p.segments[0].title ?? ""} emoji={p.emoji ?? "sob"} f={seg.kind === "hook" ? f : 99} />}
      {seg.kind === "ask" && !kidsEnd ? <Follow f={f} handle={p.handle} line="रोज़ नई हँसी, रोज़ नई सीख" /> : <Subtitle seg={seg} f={f} fps={fps} top={1372} />}
      {sound && <Sounds seg={seg} dur={dur} />}
    </AbsoluteFill>
  );
};

export const ComicReel: React.FC<ReelProps> = (p) => {
  useFonts();
  inkUp(p.ink === "plum");
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
  const duck = React.useMemo(() => duckCurve(p.segments, fps, durationInFrames), [p.segments, fps, durationInFrames]);
  // the punchline's twist word (its third-last word): the music stops dead there until the rimshot
  const twistAt = punch
    ? at(punch.words?.length ? punch.words[Math.max(0, punch.words.length - 3)] : punch.start + (punch.end - punch.start) * 0.6)
    : -1;
  return (
    <AbsoluteFill style={{ background: "#ead3c2" }}>
      {p.segments.map((seg, i) => {
        const REACT = i ? 2 : 0; // the face and gesture change 2 frames before the first word
        const from = at(seg.start);
        const dur = Math.max(1, at(seg.end) - from);
        return (
          <Sequence key={i} from={from - REACT} durationInFrames={dur + REACT} layout="none">
            <Line p={p} seg={seg} i={i} dur={dur} early={REACT} />
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
        // just under the title strip: the top ~270 px sit under Instagram's top bar
        <div style={{ position: "absolute", top: 400, width: "100%", textAlign: "center", fontFamily: FONT.hindi, fontWeight: 700, fontSize: 30, color: "rgba(0,0,0,.4)" }}>
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
          // a bouncy bed that ducks under every word, stops dead for the punchline's twist and rises for the end card
          volume={(f) => {
            const bed = interpolate(f, [0, 8, speechEnd, speechEnd + 15, durationInFrames - 10, durationInFrames], [0, 0.11, 0.11, 0.24, 0.24, 0], clamp);
            const hush = twistAt > 0 && f >= twistAt && f < rimshot + 6 ? 0 : 1;
            return bed * (f < speechEnd ? duck[f] ?? 1 : 1) * hush;
          }}
        />
      )}
      {p.guides && <SafeZones />}
    </AbsoluteFill>
  );
};
