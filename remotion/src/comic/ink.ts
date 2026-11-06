// The plum ink A/B test (REEL_INK=plum, Mr Omi's #241726: softer on OLED phones than near-black). The kid, the
// cutaways and the rooms each register how they change their ink; ComicReel and the cover call inkUp once per
// render, before anything is drawn. A module of its own, so nothing imports in a circle.
const listeners: ((plum: boolean) => void)[] = [];
export const onInk = (fn: (plum: boolean) => void) => {
  listeners.push(fn);
};
export const inkUp = (plum: boolean) => listeners.forEach((fn) => fn(plum));
