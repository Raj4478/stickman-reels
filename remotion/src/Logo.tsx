import React from "react";
import { AbsoluteFill } from "remotion";
import { useFonts } from "./StickReel";

// Seekh Sketch brand: a speech bubble (a story being told) holding a geometric stick figure that raises its
// arm to a spark (the moment a lesson clicks). Two colours, so it stays sharp from a 32 px icon to a banner.
// Compositions: LogoAvatar (profile picture, everything inside the central circle), LogoLockup (mark + name),
// LogoMark (the mark alone, transparent).

export const BRAND = { ink: "#15151c", saffron: "#ffb000", paper: "#fffaf0", name: "Seekh Sketch", hindi: "सीख स्केच" };

// The mark in a 100 x 100 box
export const Mark: React.FC<{ size: number; bubble?: string; figure?: string; spark?: string }> = ({
  size,
  bubble = BRAND.ink,
  figure = "#ffffff",
  spark = BRAND.saffron,
}) => {
  const line = { stroke: figure, strokeWidth: 6.6, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, fill: "none" };
  return (
    <svg width={size} height={size} viewBox="0 0 100 100">
      {/* speech bubble with its tail at the lower left */}
      <path d="M26,8 H74 A18,18 0 0 1 92,26 V58 A18,18 0 0 1 74,76 H40 L22,93 L25,76 A18,18 0 0 1 8,58 V26 A18,18 0 0 1 26,8 Z" fill={bubble} />
      {/* the stick figure: head, body, legs, one arm down, one arm raised to the spark */}
      <circle cx={41} cy={27.5} r={8.4} fill={figure} />
      <path d="M41,38 V54 M41,54 L34,67 M41,54 L48,67 M41,43.5 L32.5,51.5 M41,42 L56.5,29.5" {...line} />
      {/* the spark: a four-point star */}
      <path d="M66,13 Q67.6,21.4 76,23 Q67.6,24.6 66,33 Q64.4,24.6 56,23 Q64.4,21.4 66,13 Z" fill={spark} />
    </svg>
  );
};

const Wordmark: React.FC<{ size: number; color: string; accent: string; hindi?: string }> = ({ size, color, accent, hindi }) => (
  <div style={{ display: "flex", flexDirection: "column", lineHeight: 1 }}>
    <div style={{ fontFamily: "Poppins, sans-serif", fontWeight: 800, fontSize: size, letterSpacing: -size * 0.02, color }}>
      Seekh <span style={{ color: accent }}>Sketch</span>
    </div>
    {hindi && (
      <div style={{ fontFamily: "'Noto Sans Devanagari', Poppins, sans-serif", fontWeight: 700, fontSize: size * 0.36, color, opacity: 0.75,
        marginTop: size * 0.16 }}>
        {hindi}
      </div>
    )}
  </div>
);

export const LogoAvatar: React.FC = () => {
  useFonts();
  return (
    <AbsoluteFill style={{ background: BRAND.saffron, alignItems: "center", justifyContent: "center" }}>
      <div style={{ marginTop: 40 }}>
        <Mark size={700} />
      </div>
    </AbsoluteFill>
  );
};

export const LogoLockup: React.FC<{ dark?: boolean; transparent?: boolean }> = ({ dark, transparent }) => {
  useFonts();
  const bg = transparent ? "transparent" : dark ? BRAND.ink : BRAND.paper;
  const ink = dark ? "#ffffff" : BRAND.ink;
  return (
    <AbsoluteFill style={{ background: bg, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 70 }}>
      <Mark size={520} bubble={dark ? BRAND.saffron : BRAND.ink} figure={dark ? BRAND.ink : "#ffffff"} spark={dark ? "#ffffff" : BRAND.saffron} />
      <Wordmark size={230} color={ink} accent={BRAND.saffron} hindi={`${BRAND.hindi} · छोटी कहानियाँ, बड़ी सीख`} />
    </AbsoluteFill>
  );
};

export const LogoMark: React.FC = () => (
  <AbsoluteFill style={{ background: "transparent", alignItems: "center", justifyContent: "center" }}>
    <Mark size={1000} />
  </AbsoluteFill>
);
