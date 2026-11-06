// The 2.5D engine (REEL_ENGINE=three): a toon-shaded three.js room and a real perspective camera behind the
// SVG kid, after Mr Omi's "2D characters in a 3D world" (github.com/mromidev/claude-animated-shorts, MIT; ideas
// re-implemented, see THIRD_PARTY.md). Everything is a function of the frame: no frame callbacks, timers or unseeded random numbers.
import React from "react";
import * as THREE from "three";

export type Look = "day" | "evening" | "night";
export const LOOKS: Record<Look, { sky: string; ground: string; key: string; keyI: number; fill: number }> = {
  day: { sky: "#cfe8ff", ground: "#e6c9a3", key: "#fff1dc", keyI: 2.4, fill: 1.1 },
  evening: { sky: "#ffcf9e", ground: "#c99a7a", key: "#ffb36b", keyI: 2.0, fill: 0.8 }, // warm key, cooler fill
  night: { sky: "#2b3a67", ground: "#3b2f4a", key: "#a9c4ff", keyI: 1.2, fill: 0.5 },
};

// A hemisphere fill, one shadow-casting key from the upper right (side-back, like Mr Omi's day sun) and, on the
// punchline, a spotlight on the kid while the room dims (`spot` 0..1)
export const Lights: React.FC<{ look: Look; spot?: number }> = ({ look, spot = 0 }) => {
  const l = LOOKS[look];
  const target = React.useMemo(() => {
    const o = new THREE.Object3D();
    o.position.set(0, 1.3, 0);
    o.updateMatrixWorld();
    return o;
  }, []);
  return (
    <>
      <hemisphereLight args={[l.sky, l.ground, l.fill * (1 - 0.55 * spot)]} />
      <directionalLight position={[2.5, 4.5, 3.5]} color={l.key} intensity={l.keyI * (1 - 0.5 * spot)} castShadow
        shadow-mapSize={[1024, 1024]} shadow-camera-left={-5} shadow-camera-right={5} shadow-camera-top={5} shadow-camera-bottom={-5}
        shadow-bias={-0.0005} />
      {spot > 0 && <spotLight position={[0, 4, 2.5]} target={target} angle={0.35} penumbra={0.6} intensity={40 * spot} color="#fff6e0" />}
    </>
  );
};

// The look of a line: sad lines go golden-evening, dreams go night-blue, everything else is day
export const lookOf = (face?: string, visual?: string): Look => (visual === "dream" ? "night" : face === "sad" || face === "cry" ? "evening" : "day");
