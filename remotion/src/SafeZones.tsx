import React from "react";
import { AbsoluteFill } from "remotion";

// Instagram/YouTube UI over a 1080x1920 Reel (measured values for organic Reels; Meta's ad guide is stricter)
export const SAFE = { top: 270, bottom: 1460, right: 940, rightFrom: 1150, left: 60 };

const red = { position: "absolute" as const, background: "rgba(255,0,0,.28)" };
// A debug overlay (props.guides): Studio and the PR look-book stills only, never a real render
export const SafeZones: React.FC = () => (
  <AbsoluteFill style={{ pointerEvents: "none" }}>
    <div style={{ ...red, left: 0, right: 0, top: 0, height: SAFE.top }} />
    <div style={{ ...red, left: 0, right: 0, top: SAFE.bottom, bottom: 0 }} />
    <div style={{ ...red, left: SAFE.right, right: 0, top: SAFE.rightFrom, bottom: 0 }} />
  </AbsoluteFill>
);
