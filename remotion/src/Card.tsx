import React from "react";
import { AbsoluteFill, Audio, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import { COL, FONT, ease } from "./engine/fx";
import { Actor, P } from "./engine/stick";
import { CX, GROUND, HIP, HERO, S } from "./actions";
import { useFonts } from "./StickReel";

// A title card for the weekly compilation: the hero waves under a big title (intro), or cheers under the
// follow line (outro). Has sound, so it joins the Reels cleanly.
export type CardProps = { title: string; subtitle: string; outro?: boolean };

export const Card: React.FC<CardProps> = ({ title, subtitle, outro }) => {
  useFonts();
  const f = useCurrentFrame();
  const s = interpolate(f, [0, 6, 10, 14], [1.6, 0.94, 1.04, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: outro ? "#fff1cf" : "#fbe3dc" }}>
      <svg width={1080} height={1920} viewBox="0 0 1080 1920" style={{ position: "absolute" }}>
        <path d={`M40,${GROUND} Q300,${GROUND - 6} 540,${GROUND} T1040,${GROUND}`} stroke={COL.ink} strokeWidth={7} fill="none" strokeLinecap="round" />
        <Actor f={f} keys={[{ f: 0, p: {} }, { f: 8, p: outro ? P.cheer : { ra1: 150, ra2: -20 } }]}
          mod={(t, p) => (outro ? { ...p, y: p.y - Math.abs(Math.sin(t * 0.3)) * 22 } : { ...p, ra2: p.ra2 + Math.sin(t * 0.45) * 28 })}
          color={HERO.color} accessory={HERO.accessory} face={outro ? "big_smile" : "happy"} scale={S} base={{ x: CX, y: HIP }} />
      </svg>
      <div style={{ position: "absolute", left: 70, right: 70, top: 300, textAlign: "center", transform: `scale(${s})`, opacity: ease(f, 0, 4) }}>
        <span style={{ fontFamily: FONT.hindi, fontWeight: 800, fontSize: 120, lineHeight: 1.3, color: COL.ink,
          background: `linear-gradient(transparent 58%, ${COL.yellow} 58%, ${COL.yellow} 92%, transparent 92%)`, padding: "0 12px" }}>{title}</span>
      </div>
      <div style={{ position: "absolute", left: 70, right: 70, top: 1420, textAlign: "center", opacity: ease(f, 10, 18),
        fontFamily: FONT.hindi, fontWeight: 700, fontSize: 56, color: COL.ink }}>{subtitle}</div>
      <Sequence from={0}><Audio src={staticFile(outro ? "sfx/tada.wav" : "sfx/riser.wav")} volume={0.6} /></Sequence>
      <Sequence from={outro ? 20 : 26}><Audio src={staticFile("sfx/pop.wav")} volume={0.5} /></Sequence>
    </AbsoluteFill>
  );
};
