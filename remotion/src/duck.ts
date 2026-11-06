import type { Segment } from "./StickReel";

// Music gain per video frame: 1 between words, 0.71 (-3 dB) while someone speaks. The attack is fast (~70 ms)
// and the release slow (~450 ms), like Mr Omi's mix.py. Spans come from Whisper's word starts.
export const duckCurve = (segs: Segment[], fps: number, total: number): Float32Array => {
  const on = new Float32Array(total);
  for (const s of segs) {
    const w = s.words ?? [];
    w.forEach((t, k) => {
      const a = Math.max(0, Math.round((t - 0.08) * fps));
      const end = Math.min(w[k + 1] ?? s.end, t + 0.7) + 0.12;
      for (let x = a; x < Math.min(total, Math.round(end * fps)); x++) on[x] = 1;
    });
  }
  const gain = new Float32Array(total);
  let v = 0;
  for (let x = 0; x < total; x++) {
    v += (on[x] - v) * (on[x] > v ? 0.6 : 0.07); // per frame at 30 fps: ~2 frames attack, ~14 frames release
    gain[x] = 1 - 0.29 * v;
  }
  return gain;
};
