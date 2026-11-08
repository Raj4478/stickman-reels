import React from "react";
import { AbsoluteFill } from "remotion";
import { FONT } from "../engine/fx";
import { ReelProps, useFonts } from "../StickReel";
import { PartBadge } from "../storybook/StoryBook";
import { Emoji } from "./Emoji";
import { inkUp } from "./ink";
import { Kid } from "./Kid";
import { room } from "./rooms";

// The grid image of a comic Reel: the punchline's face, big, and 1-3 words inside the band that survives
// both the 4:5 feed crop (y 285..1635) and the 3:4 grid crop (y 240..1680)
export const ComicCover: React.FC<ReelProps> = (p) => {
  useFonts();
  inkUp(p.ink === "plum");
  const punch = p.segments.find((s) => s.kind === "lesson") ?? p.segments[0];
  const title = p.segments[0].title || "";
  const text = p.cover_text || title;
  const where = room(punch.place ?? p.place, 0, false);
  return (
    <AbsoluteFill style={{ background: "#ead3c2" }}>
      <AbsoluteFill style={{ transform: "translate(540px, 900px) scale(1.4) translate(-540px, -900px)", transformOrigin: "0 0" }}>
        <svg width={1080} height={1920} viewBox="0 0 1080 1920" style={{ position: "absolute" }}>
          {where.back}
          <Kid f={10} clock={10} face={punch.face ?? "shock"} look="viewer" gesture={punch.gesture ?? "talk"} mouth={0}
            girl={p.hero === "girl"} table={where.table} />
        </svg>
      </AbsoluteFill>
      {title && title !== text && (
        // the title strip, inside the 3:4 grid crop
        <div style={{ position: "absolute", top: 300, left: 50, right: 50, display: "flex", justifyContent: "center" }}>
          <div style={{ background: "#ffd43b", border: "7px solid #1b1b1f", borderRadius: 20, padding: "6px 30px", fontFamily: FONT.hindi,
            fontWeight: 800, fontSize: 64, lineHeight: 1.2, color: "#1b1b1f", whiteSpace: "nowrap" }}>{title}</div>
        </div>
      )}
      <PartBadge part={p.part} top={1170} />
      <div style={{ position: "absolute", top: 1290, left: 50, right: 50, display: "flex", justifyContent: "center" }}>
        <div style={{ background: "#fff", border: "8px solid #1b1b1f", borderRadius: 26, boxShadow: "12px 12px 0 #1b1b1f", padding: "14px 34px",
          display: "flex", alignItems: "center", gap: 14, fontFamily: FONT.hindi, fontWeight: 800, fontSize: text.length > 12 ? 70 : 92, lineHeight: 1.2,
          color: "#1b1b1f", whiteSpace: "nowrap" }}>
          <span>{text}</span>
          {p.emoji && p.emoji !== "none" && <Emoji name={p.emoji} size={96} />}
        </div>
      </div>
    </AbsoluteFill>
  );
};
