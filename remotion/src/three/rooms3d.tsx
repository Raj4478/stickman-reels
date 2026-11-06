// The 2.5D engine (REEL_ENGINE=three): a toon-shaded three.js room and a real perspective camera behind the
// SVG kid, after Mr Omi's "2D characters in a 3D world" (github.com/mromidev/claude-animated-shorts, MIT; ideas
// re-implemented, see THIRD_PARTY.md). Everything is a function of the frame: no frame callbacks, timers or unseeded random numbers.
import React from "react";
import { Box, Sign, toonRamp } from "./toon";

// A wall clock: a white face with a dark rim and two hands (signs with emoji are unsafe on CI)
const Clock3D: React.FC<{ p: [number, number, number]; r: number; f: number }> = ({ p, r, f }) => (
  <group position={p}>
    <mesh>
      <circleGeometry args={[r * 1.12, 40]} />
      <meshBasicMaterial color="#241726" />
    </mesh>
    <mesh position={[0, 0, 0.005]}>
      <circleGeometry args={[r, 40]} />
      <meshToonMaterial color="#ffffff" gradientMap={toonRamp()} />
    </mesh>
    <mesh position={[0, r * 0.25, 0.01]}>
      <boxGeometry args={[r * 0.08, r * 0.55, 0.005]} />
      <meshBasicMaterial color="#241726" />
    </mesh>
    <mesh position={[0, 0, 0.012]} rotation={[0, 0, -f * 0.05]}>
      <boxGeometry args={[r * 0.05, r * 1.6, 0.005]} />
      <meshBasicMaterial color="#e03131" />
    </mesh>
  </group>
);

const Shell: React.FC<{ wall: string; side: string; floor: string }> = ({ wall, side, floor }) => (
  <>
    <Box p={[0, -0.05, -1]} s={[9, 0.1, 9]} c={floor} ink={0} />
    <Box p={[0, 1.7, -2.45]} s={[9, 3.6, 0.1]} c={wall} />
    <Box p={[-2.9, 1.7, -0.6]} s={[0.1, 3.6, 4]} c={side} />
    <Box p={[2.9, 1.7, -0.6]} s={[0.1, 3.6, 4]} c={side} />
  </>
);

const Window: React.FC<{ x: number; y: number; sky?: string }> = ({ x, y, sky = "#bfe3ff" }) => (
  <>
    <Box p={[x, y, -2.38]} s={[1.3, 1.1, 0.06]} c="#8a5a33" />
    <mesh position={[x, y, -2.34]}>
      <planeGeometry args={[1.12, 0.92]} />
      <meshBasicMaterial color={sky} toneMapped={false} />
    </mesh>
  </>
);

const Bedroom = () => (
  <group>
    <Shell wall="#f2dcc2" side="#ecd2b5" floor="#c8a27a" />
    <Window x={1.4} y={1.8} />
    <Box p={[-1.6, 0.25, -1.5]} s={[1.8, 0.5, 1.2]} c="#5c7cfa" />   {/* bed */}
    <Box p={[-1.6, 0.6, -2.15]} s={[1.8, 0.8, 0.12]} c="#8a5a33" />  {/* headboard */}
    <Box p={[-1.95, 0.6, -1.5]} s={[0.6, 0.18, 0.4]} c="#ffffff" />  {/* pillow */}
    <Box p={[2.2, 0.95, -1.9]} s={[0.7, 1.9, 0.45]} c="#c8813f" />   {/* cupboard */}
    {/* a poster: a yellow card with a red diamond (no symbol characters: CI fonts may lack them) */}
    <Box p={[-0.7, 2.15, -2.39]} s={[0.7, 0.9, 0.02]} c="#ffd43b" />
    <Box p={[-0.7, 2.15, -2.37]} s={[0.32, 0.32, 0.02]} c="#e03131" r={[0, 0, Math.PI / 4]} />
  </group>
);

const Kitchen = () => (
  <group>
    <Shell wall="#fff3d6" side="#f5e3bd" floor="#d9c3a5" />
    <Box p={[0, 0.45, -2.1]} s={[5, 0.9, 0.6]} c="#c8813f" />        {/* counter */}
    <Box p={[0.9, 0.95, -2.1]} s={[0.9, 0.1, 0.5]} c="#495057" />    {/* stove */}
    <Box p={[-1.4, 2.0, -2.3]} s={[2.2, 0.08, 0.3]} c="#8a5a33" />   {/* shelf */}
    {[-2.2, -1.8, -1.4, -1.0].map((x) => <Box key={x} p={[x, 2.15, -2.3]} s={[0.22, 0.26, 0.22]} c="#ffc078" />)}
    <Window x={2.0} y={1.9} />
  </group>
);

const LivingRoom: React.FC<{ f: number }> = ({ f }) => (
  <group>
    <Shell wall="#e7f5ff" side="#d0ebff" floor="#c8a27a" />
    <Box p={[-1.3, 0.35, -1.9]} s={[2.2, 0.7, 0.8]} c="#e8590c" />   {/* sofa */}
    <Box p={[-1.3, 0.85, -2.25]} s={[2.2, 0.6, 0.15]} c="#d9480f" />
    <Box p={[1.6, 1.3, -2.38]} s={[1.3, 0.75, 0.06]} c="#212529" />  {/* TV */}
    <Box p={[1.6, 0.4, -2.2]} s={[1.5, 0.8, 0.4]} c="#8a5a33" />
    <Clock3D p={[0.1, 2.5, -2.38]} r={0.24} f={f} />
  </group>
);

const Classroom = () => (
  <group>
    <Shell wall="#e3ead6" side="#d8e2c8" floor="#b8966f" />
    <Box p={[0, 1.7, -2.4]} s={[4.2, 1.6, 0.06]} c="#8a5a33" />
    <Sign p={[0, 1.7, -2.36]} w={4.0} h={1.45} text="2 + 2 = 5 ?" bg="#2f5240" fg="#f1f3f5" />
    {[-1.8, 1.8].map((x) => <Box key={x} p={[x, 0.38, -1.2]} s={[1.0, 0.76, 0.5]} c="#cf9a5e" />)}
  </group>
);

const Office: React.FC<{ f: number }> = ({ f }) => (
  <group>
    <Shell wall="#edf2f7" side="#dee5ee" floor="#868e96" />
    {[-1.5, 1.5].map((x) => <Box key={x} p={[x, 1.8, -2.38]} s={[1.4, 1.3, 0.06]} c="#adb5bd" />)}
    <Box p={[2.3, 0.5, -1.8]} s={[0.4, 1.0, 0.4]} c="#c8643b" />     {/* plant pot */}
    <Box p={[2.3, 1.25, -1.8]} s={[0.7, 0.6, 0.7]} c="#3f8f4a" />
    <Clock3D p={[0, 2.6, -2.38]} r={0.22} f={f} />
  </group>
);

const Gym = () => (
  <group>
    <Shell wall="#dfe3ea" side="#ced4da" floor="#5c6370" />
    <Box p={[0, 1.8, -2.38]} s={[3.6, 1.6, 0.05]} c="#cfe3f5" />      {/* mirror */}
    <Sign p={[-1.2, 2.45, -2.33]} w={0.9} h={0.35} text="GYM" bg="#cfe3f5" fg="#e03131" />
    {[-2.3, 2.3].map((x) => <Box key={x} p={[x, 0.7, -1.9]} s={[0.6, 1.4, 0.5]} c="#495057" />)}  {/* racks */}
  </group>
);

const Street = () => (
  <group>
    <Box p={[0, -0.05, -3]} s={[14, 0.1, 14]} c="#868e96" ink={0} />
    {[["#ffd8a8", -3], ["#ffc9c9", -1], ["#d3f9d8", 1], ["#e5dbff", 3]].map(([c, x]) => (
      <Box key={String(x)} p={[Number(x), 1.8, -4.5]} s={[1.9, 3.6 + Number(x) * 0.1, 1.5]} c={String(c)} />
    ))}
    <Sign p={[0, 2.6, -3.74]} w={1.2} h={0.45} text="चाय" bg="#c8813f" fg="#fff3bf" />
  </group>
);

// One case per reel/comic.py ROOMS key (tests/test_three.py checks this)
export const Room3D: React.FC<{ name: string; f: number }> = ({ name, f }) => {
  switch (name) {
    case "kitchen": return <Kitchen />;
    case "living_room": return <LivingRoom f={f} />;
    case "classroom": return <Classroom />;
    case "office": return <Office f={f} />;
    case "gym": return <Gym />;
    case "street": return <Street />;
    case "bedroom":
    default: return <Bedroom />;
  }
};
