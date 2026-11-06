import React from "react";
import { Easing, interpolate } from "remotion";
import { FONT } from "../engine/fx";
import { onInk } from "./ink";

// Cutaways of a comic Reel (reel/comic.py VISUALS): when a line names something you can show, the Reel cuts from
// the kid to it, full frame, while the kid keeps talking in a small bubble in the corner. `text` is the line's
// visual_text (₹15,000, 4 साल, गाना.mp3...), drawn into the picture. The drawings keep to y 430-1160, between
// the title strip and the subtitles, and leave the bottom left corner (x < 300, y > 1100) to the kid's bubble.

let INK = "#1b1b1f";
const O = { stroke: INK, strokeWidth: 8, strokeLinejoin: "round" as const, strokeLinecap: "round" as const };
onInk((plum) => {
  INK = plum ? "#241726" : "#1b1b1f"; // the plum ink A/B test (ink.ts)
  O.stroke = INK;
});
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const pop = (f: number, at = 0) => interpolate(f - at, [0, 6, 10], [0.6, 1.06, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
const T: React.FC<{ x: number; y: number; size: number; color?: string; weight?: number; anchor?: "start" | "middle" | "end"; children: React.ReactNode }> = ({ x, y, size, color = INK, weight = 800, anchor = "middle", children }) => (
  <text x={x} y={y} fontFamily={FONT.hindi} fontWeight={weight} fontSize={size} fill={color} textAnchor={anchor}>{children}</text>
);

const Cursor: React.FC<{ from: [number, number]; to: [number, number]; f: number; at?: number }> = ({ from, to, f, at = 18 }) => {
  const t = interpolate(f, [4, at], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const press = f >= at && f < at + 4 ? 6 : 0;
  const x = from[0] + (to[0] - from[0]) * t;
  const y = from[1] + (to[1] - from[1]) * t + press;
  return <path d={`M${x},${y} l0,64 l16,-16 l12,28 l12,-6 l-12,-27 l22,0 Z`} fill="#fff" stroke={INK} strokeWidth={5} strokeLinejoin="round" />;
};

// ---- the computer screen ----------------------------------------------------------------------------------
const SCREENS: Record<string, { title: string; bar: string }> = {
  music: { title: "Music Player", bar: "#7048e8" },
  video: { title: "Movies HD", bar: "#e03131" },
  jobs: { title: "Naukri Search", bar: "#1971c2" },
  search: { title: "Search", bar: "#2f9e44" },
  error: { title: "Windows", bar: "#495057" },
};

const ScreenContent: React.FC<{ kind: string; text: string; f: number }> = ({ kind, text, f }) => {
  switch (kind) {
    case "video":
      return (
        <g>
          <rect x={130} y={560} width={820} height={420} rx={12} fill="#111" />
          <path d="M490,690 L630,770 L490,850 Z" fill="#fff" transform={`translate(540 770) scale(${1 + Math.sin(f * 0.3) * 0.05}) translate(-540 -770)`} />
          <rect x={150} y={950} width={780} height={10} rx={5} fill="#555" />
          <rect x={150} y={950} width={780 * interpolate(f, [0, 120], [0.05, 0.9], clamp)} height={10} rx={5} fill="#e03131" />
          <T x={540} y={1060} size={54}>{text || "फिल्म.mp4"}</T>
        </g>
      );
    case "jobs":
      return (
        <g>
          <rect x={150} y={560} width={780} height={70} rx={35} fill="#fff" {...O} strokeWidth={5} />
          <T x={190} y={608} size={36} weight={600} anchor="start" color="#555">computer operator jobs</T>
          {[680, 770, 860].map((y, i) => (
            <g key={y} opacity={0.35}>
              <rect x={150} y={y} width={780} height={70} rx={10} fill="#dee2e6" />
              <rect x={180} y={y + 22} width={300 - i * 40} height={24} rx={12} fill="#adb5bd" />
            </g>
          ))}
          <g transform={`translate(540 960) scale(${pop(f, 10)}) rotate(-6) translate(-540 -960)`} opacity={f >= 10 ? 1 : 0}>
            <rect x={230} y={900} width={620} height={130} rx={16} fill="none" stroke="#e03131" strokeWidth={12} />
            <T x={540} y={990} size={70} color="#e03131">{text || "0 नौकरियाँ"}</T>
          </g>
        </g>
      );
    case "search": {
      const typed = Math.floor(interpolate(f, [4, 30], [0, (text || "नौकरी कैसे मिले").length], clamp));
      return (
        <g>
          <T x={540} y={650} size={70} color="#2f9e44">Search</T>
          <rect x={150} y={700} width={780} height={90} rx={45} fill="#fff" {...O} strokeWidth={5} />
          <T x={200} y={762} size={44} weight={600} anchor="start">{(text || "नौकरी कैसे मिले").slice(0, typed)}{f % 16 < 8 ? "|" : ""}</T>
          {f > 36 && <T x={540} y={900} size={44} weight={600} color="#868e96">कोई result नहीं मिला</T>}
        </g>
      );
    }
    case "error": {
      const shake = f < 12 ? Math.sin(f * 2.6) * 12 : 0;
      return (
        <g transform={`translate(${shake} 0)`}>
          <rect x={200} y={600} width={680} height={400} rx={14} fill="#f8f9fa" {...O} strokeWidth={6} />
          <rect x={200} y={600} width={680} height={64} rx={14} fill="#495057" />
          <circle cx={320} cy={790} r={60} fill="#e03131" />
          <path d="M295,765 L345,815 M345,765 L295,815" stroke="#fff" strokeWidth={14} strokeLinecap="round" />
          <T x={410} y={800} size={50} anchor="start">{text || "Error!"}</T>
          <rect x={620} y={900} width={200} height={70} rx={10} fill="#dee2e6" {...O} strokeWidth={4} />
          <T x={720} y={948} size={36} weight={700}>OK</T>
        </g>
      );
    }
    default: {
      // music: album art, the track name and bars that bounce to the beat
      return (
        <g>
          <rect x={160} y={570} width={300} height={300} rx={20} fill="#7048e8" {...O} strokeWidth={5} />
          <circle cx={310} cy={720} r={90} fill="#9775fa" />
          <circle cx={310} cy={720} r={22} fill="#7048e8" />
          <T x={500} y={660} size={50} anchor="start">{text || "गाना.mp3"}</T>
          {Array.from({ length: 9 }).map((_, i) => {
            const h = 40 + Math.abs(Math.sin(f * 0.35 + i * 1.3)) * 110;
            return <rect key={i} x={500 + i * 44} y={850 - h} width={28} height={h} rx={8} fill="#7048e8" />;
          })}
          <rect x={160} y={930} width={760} height={10} rx={5} fill="#ced4da" />
          <rect x={160} y={930} width={760 * interpolate(f, [0, 150], [0.1, 0.7], clamp)} height={10} rx={5} fill="#7048e8" />
          <circle cx={540} cy={1030} r={50} fill="#7048e8" />
          <path d="M520,1005 L520,1055 M560,1005 L560,1055" stroke="#fff" strokeWidth={14} strokeLinecap="round" />
        </g>
      );
    }
  }
};

const Screen: React.FC<{ kind: string; text: string; f: number }> = ({ kind, text, f }) => {
  const s = SCREENS[kind] ?? SCREENS.music;
  return (
    <g>
      <rect width={1080} height={1920} fill="#343a40" />
      <rect x={60} y={430} width={960} height={740} rx={30} fill="#212529" {...O} />
      <rect x={90} y={460} width={900} height={680} rx={10} fill="#f1f3f5" />
      <rect x={90} y={460} width={900} height={64} fill={s.bar} />
      {["#ff6b6b", "#ffd43b", "#69db7c"].map((c, i) => <circle key={c} cx={130 + i * 40} cy={492} r={12} fill={c} />)}
      <T x={540} y={506} size={34} weight={700} color="#fff">{s.title}</T>
      <ScreenContent kind={kind} text={text} f={f} />
      {kind !== "search" && <Cursor from={[860, 1100]} to={kind === "error" ? [700, 930] : kind === "video" ? [560, 790] : [560, 1020]} f={f} />}
      <rect x={430} y={1170} width={220} height={80} fill="#212529" />
      <rect x={330} y={1240} width={420} height={30} rx={10} fill="#212529" />
    </g>
  );
};

// ---- the other cutaways -----------------------------------------------------------------------------------
const MONTHS = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"];

const Calendar: React.FC<{ text: string; f: number; dur: number }> = ({ text, f, dur }) => {
  // pages fly off every few frames, then it stops on the text
  const stop = Math.max(16, Math.round(dur * 0.55));
  const page = Math.min(Math.floor(f / 3), Math.floor(stop / 3));
  const flying = f < stop ? (f % 3) / 3 : 0;
  const sheet = (label: React.ReactNode, key: string, style?: React.CSSProperties) => (
    <g key={key} style={style}>
      <rect x={240} y={560} width={600} height={560} rx={16} fill="#fff" {...O} />
      <rect x={240} y={560} width={600} height={130} rx={16} fill="#e03131" {...O} />
      {label}
    </g>
  );
  return (
    <g>
      <rect width={1080} height={1920} fill="#ead3c2" />
      {sheet(f >= stop ? <T x={540} y={940} size={text.length > 8 ? 110 : 150}>{text || "4 साल"}</T> : <T x={540} y={920} size={110}>{MONTHS[(page + 1) % 12]}</T>, "under")}
      {f < stop && (
        <g transform={`translate(${flying * 260} ${-flying * 500}) rotate(${flying * 40} 540 840)`} opacity={1 - flying}>
          {sheet(<T x={540} y={920} size={110}>{MONTHS[page % 12]}</T>, "top")}
        </g>
      )}
      {[330, 540, 750].map((x) => <rect key={x} x={x - 14} y={520} width={28} height={80} rx={14} fill="#adb5bd" {...O} strokeWidth={5} />)}
      <T x={540} y={650} size={56} color="#fff">{f >= stop ? "बाद में..." : String(2022 + Math.floor(page / 12))}</T>
    </g>
  );
};

const Money: React.FC<{ text: string; f: number }> = ({ text, f }) => (
  <g>
    <rect width={1080} height={1920} fill="#e6fcf5" />
    <g transform={`translate(540 800) scale(${pop(f)}) rotate(-3) translate(-540 -800)`}>
      <rect x={200} y={470} width={680} height={660} rx={16} fill="#fff" {...O} />
      <T x={540} y={570} size={60}>सैलरी स्लिप</T>
      {[640, 710, 780].map((y) => <rect key={y} x={260} y={y} width={560} height={22} rx={11} fill="#e9ecef" />)}
      <path d="M260,860 L820,860" stroke={INK} strokeWidth={5} strokeDasharray="16 12" />
      <T x={540} y={1010} size={text.length > 8 ? 96 : 120} color="#2b8a3e">{text || "₹15,000"}</T>
    </g>
    {[0, 1, 2].map((i) => {
      const t = interpolate(f - 6 - i * 5, [0, 14], [0, 1], { ...clamp, easing: Easing.bounce });
      return (
        <g key={i} transform={`translate(${300 + i * 210} ${380 + t * 760})`} opacity={f > 6 + i * 5 ? 1 : 0}>
          <circle r={46} fill="#fcc419" {...O} strokeWidth={6} />
          <T x={0} y={18} size={52} color="#e67700">₹</T>
        </g>
      );
    })}
  </g>
);

const Certificate: React.FC<{ text: string; f: number }> = ({ text, f }) => {
  const swing = Math.sin(f * 0.2) * interpolate(f, [0, 60], [8, 2], clamp);
  const web = interpolate(f, [20, 40], [0, 1], clamp);
  return (
    <g>
      <rect width={1080} height={1920} fill="#e9dccb" />
      <circle cx={540} cy={470} r={12} fill={INK} />
      <g transform={`rotate(${swing} 540 470)`}>
        <path d="M540,470 L300,560 M540,470 L780,560" stroke={INK} strokeWidth={5} />
        <rect x={160} y={560} width={760} height={540} rx={10} fill="#fff9db" stroke="#c99a2e" strokeWidth={20} />
        <rect x={200} y={600} width={680} height={460} fill="none" stroke="#c99a2e" strokeWidth={4} />
        <T x={540} y={700} size={64} color="#8a6116">CERTIFICATE</T>
        <T x={540} y={760} size={34} weight={600} color="#8a6116">of Completion</T>
        <T x={540} y={880} size={text.length > 14 ? 56 : 70}>{text || "कंप्यूटर कोर्स"}</T>
        <circle cx={760} cy={990} r={56} fill="#e03131" {...O} strokeWidth={5} />
        <path d="M730,1040 L720,1100 L760,1080 L800,1100 L790,1040" fill="#e03131" {...O} strokeWidth={5} />
      </g>
      {/* nobody has looked at it in years */}
      <g opacity={web} stroke="#fff" strokeWidth={4} fill="none">
        <path d="M920,430 L780,430 M920,430 L920,570 M920,430 L800,530 M880,430 Q870,470 920,480 M840,430 Q830,500 920,520 M800,430 Q800,520 920,560" />
        <path d={`M860,430 L860,${470 + web * 90}`} />
        <circle cx={860} cy={480 + web * 90} r={14} fill={INK} stroke="none" />
      </g>
    </g>
  );
};

const Clock: React.FC<{ text: string; f: number; dur: number }> = ({ text, f, dur }) => {
  const spin = interpolate(f, [0, Math.max(12, dur * 0.6)], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  return (
    <g>
      <rect width={1080} height={1920} fill="#d0ebff" />
      <circle cx={540} cy={780} r={300} fill="#fff" {...O} strokeWidth={14} />
      {Array.from({ length: 12 }).map((_, i) => {
        const a = (i / 12) * Math.PI * 2;
        return <path key={i} d={`M${540 + Math.sin(a) * 250},${780 - Math.cos(a) * 250} L${540 + Math.sin(a) * 280},${780 - Math.cos(a) * 280}`} stroke={INK} strokeWidth={10} strokeLinecap="round" />;
      })}
      <path d="M540,780 L540,600" stroke={INK} strokeWidth={14} strokeLinecap="round" transform={`rotate(${spin * 1440} 540 780)`} />
      <path d="M540,780 L540,520" stroke="#e03131" strokeWidth={8} strokeLinecap="round" transform={`rotate(${spin * 17280} 540 780)`} />
      <circle cx={540} cy={780} r={18} fill={INK} />
      <g transform={`translate(540 1150) scale(${pop(f, 8)}) translate(-540 -1150)`} opacity={f >= 8 ? 1 : 0}>
        <rect x={190} y={1080} width={700} height={120} rx={60} fill="#fff" {...O} />
        <T x={540} y={1162} size={64}>{text || "घंटों बाद..."}</T>
      </g>
    </g>
  );
};

const Chat: React.FC<{ text: string; f: number }> = ({ text, f }) => (
  <g>
    <rect width={1080} height={1920} fill="#dbe4ff" />
    <rect x={280} y={420} width={520} height={900} rx={60} fill="#212529" {...O} />
    <rect x={306} y={470} width={468} height={800} rx={30} fill="#efe7dd" />
    <rect x={306} y={470} width={468} height={100} rx={30} fill="#075e54" />
    <circle cx={370} cy={520} r={30} fill="#ced4da" />
    <T x={420} y={535} size={38} weight={700} color="#fff" anchor="start">Chat</T>
    <g opacity={f > 4 ? 1 : 0}>
      <rect x={330} y={620} width={260} height={70} rx={20} fill="#fff" />
      <T x={360} y={666} size={34} weight={600} anchor="start">Hi</T>
    </g>
    {f > 10 && f < 26 && (
      <g>
        <rect x={330} y={720} width={140} height={60} rx={20} fill="#fff" />
        {[0, 1, 2].map((i) => <circle key={i} cx={370 + i * 30} cy={750 + (Math.floor(f / 3) % 3 === i ? -6 : 0)} r={9} fill="#868e96" />)}
      </g>
    )}
    {f >= 26 && (
      <g transform={`translate(330 720) scale(${pop(f, 26)})`}>
        <rect width={420} height={140} rx={24} fill="#fff" />
        <T x={24} y={90} size={text.length > 12 ? 38 : 48} weight={700} anchor="start">{text || "hmm"}</T>
      </g>
    )}
    {f >= 40 && (
      <g>
        <T x={690} y={1240} size={30} weight={600} color="#4dabf7" anchor="end">Seen</T>
        <path d="M700,1228 l10,10 l18,-22 M716,1228 l10,10 l18,-22" stroke="#4dabf7" strokeWidth={5} fill="none" strokeLinecap="round" />
      </g>
    )}
  </g>
);

const Result: React.FC<{ text: string; f: number }> = ({ text, f }) => {
  const ring = interpolate(f, [8, 22], [0, 1], clamp);
  return (
    <g>
      <rect width={1080} height={1920} fill="#fff3bf" />
      <g transform="rotate(-3 540 800)">
        <rect x={180} y={460} width={720} height={680} rx={10} fill="#fff" {...O} />
        <T x={540} y={540} size={44} weight={700}>उत्तर पुस्तिका</T>
        {[600, 660, 720, 780].map((y, i) => <path key={y} d={`M240,${y} q60,-20 120,0 t120,0 t120,0 t${80 + i * 20},0`} stroke="#4263eb" strokeWidth={6} fill="none" opacity={0.6} />)}
        <T x={540} y={1000} size={text.length > 6 ? 110 : 150} color="#e03131">{text || "2/100"}</T>
        <ellipse cx={540} cy={960} rx={260} ry={120} fill="none" stroke="#e03131" strokeWidth={12} strokeDasharray={`${ring * 1200} 1300`} transform="rotate(-8 540 960)" />
      </g>
    </g>
  );
};

export const Cutaway: React.FC<{ name: string; text: string; screen?: string; f: number; dur: number }> = ({ name, text, screen = "music", f, dur }) => {
  switch (name) {
    case "screen":
      return <Screen kind={screen} text={text} f={f} />;
    case "calendar":
      return <Calendar text={text} f={f} dur={dur} />;
    case "money":
      return <Money text={text} f={f} />;
    case "certificate":
      return <Certificate text={text} f={f} />;
    case "clock":
      return <Clock text={text} f={f} dur={dur} />;
    case "chat":
      return <Chat text={text} f={f} />;
    case "result":
      return <Result text={text} f={f} />;
    default:
      return null;
  }
};

// Sound for each cutaway (names in remotion/public/sfx)
export const CUTAWAY_SOUND: Record<string, [number, string, number][]> = {
  screen: [[18, "pop", 0.5]],
  calendar: [[0, "whoosh", 0.4], [2, "tick", 0.35]],
  money: [[6, "ding", 0.45], [11, "ding", 0.35], [16, "ding", 0.3]],
  certificate: [[0, "whoosh", 0.35]],
  clock: [[0, "tick", 0.4], [8, "tick", 0.4]],
  chat: [[4, "pop", 0.45], [26, "pop", 0.55]],
  result: [[8, "thud", 0.5]],
};
