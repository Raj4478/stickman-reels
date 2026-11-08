// The 2.5D engine (REEL_ENGINE=three): a toon-shaded three.js room and a real perspective camera behind the
// SVG kid, after Mr Omi's "2D characters in a 3D world" (github.com/mromidev/claude-animated-shorts, MIT; ideas
// re-implemented, see THIRD_PARTY.md). Everything is a function of the frame: no frame callbacks, timers or unseeded random numbers.
import React from "react";
import * as THREE from "three";
import type { V3 } from "./camera";

export const INK3 = "#241726"; // Mr Omi's plum ink

// Three bands of light (shade, mid, lit). Nearest filtering keeps the bands hard, like cel animation.
let ramp: THREE.DataTexture | null = null;
export const toonRamp = () => {
  if (!ramp) {
    ramp = new THREE.DataTexture(new Uint8Array([110, 185, 255]), 3, 1, THREE.RedFormat);
    ramp.minFilter = ramp.magFilter = THREE.NearestFilter;
    ramp.generateMipmaps = false;
    ramp.needsUpdate = true;
  }
  return ramp;
};

// A toon-shaded box with an inverted-hull outline about `ink` metres thick (a cheap stand-in for Mr Omi's
// screen-space ink pass, ink.ts in his repo: port that later if the hull looks too uniform)
export const Box: React.FC<{ p: V3; s: V3; c: string; ink?: number; r?: V3 }> = ({ p, s, c, ink = 0.018, r = [0, 0, 0] }) => (
  <group position={p} rotation={r}>
    <mesh castShadow receiveShadow>
      <boxGeometry args={s} />
      <meshToonMaterial color={c} gradientMap={toonRamp()} />
    </mesh>
    {ink > 0 && (
      <mesh scale={[1 + (2 * ink) / s[0], 1 + (2 * ink) / s[1], 1 + (2 * ink) / s[2]]}>
        <boxGeometry args={s} />
        <meshBasicMaterial color={INK3} side={THREE.BackSide} />
      </mesh>
    )}
  </group>
);

// Flat lit-from-nowhere text on a board ("GYM", "चाय", the blackboard). Mr Omi: side-lit signs go unreadable, so
// signs are unlit. The texture is redrawn once the fonts are loaded (document.fonts.status turns "loaded").
export const Sign: React.FC<{ p: V3; w: number; h: number; text: string; bg: string; fg: string; r?: V3 }> = ({ p, w, h, text, bg, fg, r = [0, 0, 0] }) => {
  const ready = document.fonts.status;
  const tex = React.useMemo(() => {
    const c = document.createElement("canvas");
    c.width = Math.round(w * 400);
    c.height = Math.round(h * 400);
    const g = c.getContext("2d")!;
    g.fillStyle = bg;
    g.fillRect(0, 0, c.width, c.height);
    g.fillStyle = fg;
    g.font = `800 ${Math.round(c.height * 0.55)}px Poppins, "Noto Sans Devanagari", sans-serif`;
    g.textAlign = "center";
    g.textBaseline = "middle";
    g.fillText(text, c.width / 2, c.height / 2);
    const t = new THREE.CanvasTexture(c);
    t.colorSpace = THREE.SRGBColorSpace;
    return t;
  }, [w, h, text, bg, fg, ready]);
  return (
    <mesh position={p} rotation={r}>
      <planeGeometry args={[w, h]} />
      <meshBasicMaterial map={tex} toneMapped={false} />
    </mesh>
  );
};
