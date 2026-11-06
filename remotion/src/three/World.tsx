// The 2.5D engine (REEL_ENGINE=three): a toon-shaded three.js room and a real perspective camera behind the
// SVG kid, after Mr Omi's "2D characters in a 3D world" (github.com/mromidev/claude-animated-shorts, MIT; ideas
// re-implemented, see THIRD_PARTY.md). Everything is a function of the frame: no frame callbacks, timers or unseeded random numbers.
import { useThree } from "@react-three/fiber";
import { ThreeCanvas } from "@remotion/three";
import React from "react";
import * as THREE from "three";
import { Cam3, H, W, makeCamera } from "./camera";
import { LOOKS, Lights, Look } from "./lights";
import { Room3D } from "./rooms3d";

// Points R3F's camera at `c` on every render (Remotion renders the canvas once per frame; no useFrame, no clock)
const CameraRig: React.FC<{ c: Cam3 }> = ({ c }) => {
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  const m = makeCamera(c);
  camera.position.copy(m.position);
  camera.quaternion.copy(m.quaternion);
  camera.fov = m.fov;
  camera.near = m.near;
  camera.far = m.far;
  camera.updateProjectionMatrix();
  camera.updateMatrixWorld();
  return null;
};

export const World: React.FC<{ room: string; cam: Cam3; look: Look; f: number; spot?: number; blur?: number }> = ({ room, cam, look, f, spot = 0, blur = 0 }) => (
  // `flat`: no tone mapping, so the toon colours land on their hex values
  <ThreeCanvas width={W} height={H} flat shadows camera={{ fov: 40, near: 0.05, far: 200 }}
    style={{ position: "absolute", inset: 0, filter: blur > 0.2 ? `blur(${blur}px)` : undefined }}>
    <color attach="background" args={[LOOKS[look].sky]} />
    <fog attach="fog" args={[LOOKS[look].sky, 9, 30]} />
    <CameraRig c={cam} />
    <Lights look={look} spot={spot} />
    <Room3D name={room} f={f} />
  </ThreeCanvas>
);

// The room blurs more the closer the camera is to the kid (the kid layer is always sharp). Mr Omi's blur discs at
// 1080 px: close-up 12-16, medium 10-12, full 8, wide 5; a CSS blur radius is about half a disc radius.
export const blurOf = (c: Cam3) => {
  const d = Math.hypot(c.pos[0] - c.look[0], c.pos[1] - c.look[1], c.pos[2] - c.look[2]);
  return Math.max(0, Math.min(6, (4.5 - d) * 1.9));
};
