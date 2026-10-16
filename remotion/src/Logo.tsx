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

// YouTube banner, 2560 x 1440. Only the centre 1546 x 423 shows on every device (phones), so the name, mark and
// promise sit there; the rest (seen on TVs and wide screens) carries a faint pattern of the mark.
export const LogoBanner: React.FC<{ guides?: boolean }> = ({ guides }) => {
  useFonts();
  const tiles = [];
  for (let row = 0; row < 7; row++) {
    for (let col = 0; col < 13; col++) {
      const x = col * 210 + (row % 2) * 105 - 60;
      const y = row * 220 - 40;
      tiles.push(
        <div key={`${row}-${col}`} style={{ position: "absolute", left: x, top: y, opacity: 0.07, transform: `rotate(${(row + col) % 2 ? -8 : 8}deg)` }}>
          <Mark size={120} bubble="#ffffff" figure={BRAND.ink} spark={BRAND.saffron} />
        </div>,
      );
    }
  }
  return (
    <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 50%, #23232d 0%, ${BRAND.ink} 70%)`, overflow: "hidden" }}>
      {tiles}
      {/* the safe area: everything important lives inside 1546 x 423 at the centre */}
      <div style={{ position: "absolute", left: (2560 - 1546) / 2, top: (1440 - 423) / 2, width: 1546, height: 423, display: "flex",
        alignItems: "center", justifyContent: "center", gap: 56, outline: guides ? "4px dashed #ff4d4d" : undefined }}>
        <Mark size={330} bubble={BRAND.saffron} figure={BRAND.ink} spark="#ffffff" />
        <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
          <div style={{ fontFamily: "Poppins, sans-serif", fontWeight: 800, fontSize: 150, lineHeight: 1, letterSpacing: -3, color: "#ffffff" }}>
            Seekh <span style={{ color: BRAND.saffron }}>Sketch</span>
          </div>
          <div style={{ fontFamily: "'Noto Sans Devanagari', Poppins, sans-serif", fontWeight: 700, fontSize: 52, color: "#ffffff", opacity: 0.9 }}>
            छोटी कहानियाँ, बड़ी सीख
          </div>
          <div style={{ display: "flex", gap: 18 }}>
            <span style={{ background: BRAND.saffron, color: BRAND.ink, fontFamily: "'Noto Sans Devanagari', Poppins, sans-serif", fontWeight: 800,
              fontSize: 36, padding: "8px 26px", borderRadius: 40 }}>हर दिन नई Short</span>
            <span style={{ border: "4px solid #ffffff", color: "#ffffff", fontFamily: "Poppins, sans-serif", fontWeight: 700, fontSize: 34,
              padding: "6px 24px", borderRadius: 40 }}>@seekhsketch</span>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
