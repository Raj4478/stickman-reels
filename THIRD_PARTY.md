# Third-party code and assets

| What | Where | Licence |
| --- | --- | --- |
| Stick-figure rig, poses, motion cycles, effects; Box and Coin props | `remotion/src/engine/stick.tsx`, `fx.tsx`, `props.tsx`, adapted from [nispa/stickman-video](https://github.com/nispa/stickman-video) | MIT, © 2026 nispa ([copy](remotion/src/engine/LICENSE-stickman-video.txt)) |
| Poppins | `remotion/public/fonts/Poppins-*.ttf` | SIL Open Font License ([copy](remotion/public/fonts/Poppins-OFL.txt)) |
| Noto Sans Devanagari | `remotion/public/fonts/NotoSansDevanagari.ttf` | SIL Open Font License ([copy](remotion/public/fonts/NotoSansDevanagari-OFL.txt)) |
| Remotion | npm dependency | [Remotion licence](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md): free for individuals and companies of up to 3 people |

## Mr Omi, claude-animated-shorts (ideas only)

The camera, acting, audio and QA rules in `remotion/src/comic/ComicReel.tsx`, `remotion/src/comic/Kid.tsx`,
`remotion/src/director.ts`, `remotion/src/duck.ts` and `reel/scan.py` follow the notes in
[mromidev/claude-animated-shorts](https://github.com/mromidev/claude-animated-shorts) (MIT, Copyright (c) 2026 Mr omi).
No code or images were copied; the formulas (smootherstep glide, sign-flipping impact kick, word-keyed ducking) are
re-implemented here.
