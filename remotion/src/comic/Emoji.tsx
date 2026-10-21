import React from "react";

// The emoji after a comic Reel's title strip, drawn as shapes: the Linux render machine has no emoji font.
// Each is drawn in a 100x100 box. Keys match reel/comic.py EMOJI.

const INK = "#2a2320";
const Y = "#ffcc33";
const TEAR = "#5cb8ff";
const face = <circle cx={50} cy={50} r={46} fill={Y} stroke={INK} strokeWidth={4} />;

const DRAWN: Record<string, React.ReactNode> = {
  sob: (
    <>
      {face}
      <path d="M22,40 Q32,32 42,40 M58,40 Q68,32 78,40" stroke={INK} strokeWidth={5} fill="none" strokeLinecap="round" />
      <path d="M26,44 L22,96 L36,96 L36,46 Z M74,44 L78,96 L64,96 L64,46 Z" fill={TEAR} />
      <path d="M32,62 Q50,54 68,62 L64,80 Q50,88 36,80 Z" fill="#7a2b2b" stroke={INK} strokeWidth={4} strokeLinejoin="round" />
    </>
  ),
  joy: (
    <>
      {face}
      <path d="M22,42 Q32,30 42,42 M58,42 Q68,30 78,42" stroke={INK} strokeWidth={5} fill="none" strokeLinecap="round" />
      <path d="M24,56 L76,56 Q72,84 50,86 Q28,84 24,56 Z" fill="#7a2b2b" stroke={INK} strokeWidth={4} strokeLinejoin="round" />
      <path d="M30,60 L70,60" stroke="#fff" strokeWidth={6} />
      <path d="M10,40 q-8,14 2,20 q10,-6 -2,-20 Z M90,40 q8,14 -2,20 q-10,-6 2,-20 Z" fill={TEAR} />
    </>
  ),
  skull: (
    <>
      <path d="M50,6 C20,6 8,28 10,50 C11,64 20,70 26,72 L26,88 L74,88 L74,72 C80,70 89,64 90,50 C92,28 80,6 50,6 Z" fill="#f4f1ea" stroke={INK} strokeWidth={4} />
      <ellipse cx={34} cy={48} rx={11} ry={13} fill={INK} />
      <ellipse cx={66} cy={48} rx={11} ry={13} fill={INK} />
      <path d="M50,58 L44,70 L56,70 Z" fill={INK} />
      <path d="M38,78 L38,88 M50,78 L50,88 M62,78 L62,88" stroke={INK} strokeWidth={4} />
    </>
  ),
  facepalm: (
    <>
      {face}
      <path d="M30,64 Q50,72 70,64" stroke={INK} strokeWidth={5} fill="none" strokeLinecap="round" />
      <path d="M18,58 C14,40 26,22 40,24 L66,30 C74,32 74,42 66,42 L52,40 L70,46 C78,48 76,58 68,57 L50,54 C40,62 26,66 18,58 Z" fill="#f7c58f" stroke={INK} strokeWidth={4} strokeLinejoin="round" />
    </>
  ),
  clown: (
    <>
      <circle cx={50} cy={50} r={46} fill="#fff7ef" stroke={INK} strokeWidth={4} />
      <path d="M12,36 Q22,8 50,10 Q78,8 88,36 Q74,22 50,24 Q26,22 12,36 Z" fill="#e5322d" />
      <path d="M26,40 L38,30 L40,44 Z M74,40 L62,30 L60,44 Z" fill="#3d7bd9" />
      <circle cx={34} cy={42} r={5} fill={INK} />
      <circle cx={66} cy={42} r={5} fill={INK} />
      <circle cx={50} cy={58} r={10} fill="#e5322d" stroke={INK} strokeWidth={3} />
      <path d="M28,70 Q50,90 72,70" stroke="#e5322d" strokeWidth={8} fill="none" strokeLinecap="round" />
    </>
  ),
};

export const Emoji: React.FC<{ name: string; size: number }> = ({ name, size }) =>
  DRAWN[name] ? (
    <svg width={size} height={size} viewBox="0 0 100 100" style={{ display: "inline-block", verticalAlign: "middle" }}>
      {DRAWN[name]}
    </svg>
  ) : null;

export const EMOJI_NAMES = Object.keys(DRAWN);
