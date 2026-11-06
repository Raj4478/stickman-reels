"""Every-frame scan of a rendered Reel: black or white frames nobody planned, frozen pictures and sudden pops, plus a
contact sheet (one frame a second) for the Telegram review. Report only: nothing is blocked.

The idea comes from Mr Omi's short_qa.py (github.com/mromidev/claude-animated-shorts, MIT); the code is new."""
import subprocess

import numpy as np

W, H = 90, 160  # tiny greyscale frames are enough to see flashes, freezes and pops


def frames(video):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(video), '-vf', f'scale={W}:{H},format=gray', '-f', 'rawvideo', '-'],
                         capture_output=True, check=True, timeout=600).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32) / 255


def mid_cut(seg, fps=30):
    """A port of midCut() in remotion/src/StickReel.tsx: a story scene longer than 3 seconds cuts to a second angle
    on the word nearest its middle (keep the two in sync)."""
    start = round(seg['start'] * fps)
    dur = round(seg['end'] * fps) - start
    if seg['kind'] != 'scene' or dur < 3 * fps:
        return None
    marks = [m for m in (round((t - seg['start']) * fps) for t in seg.get('words') or []) if m > fps and dur - m > fps]
    if not marks:
        return round(dur / 2)
    return min(marks, key=lambda m: abs(m - dur / 2))


def planned_cuts(props, fps=30):
    """Frames where the Reel cuts on purpose: each line's start and the cuts inside a line (comic: cutsOf() in
    remotion/src/comic/ComicReel.tsx; story: midCut()). Keep these ports in sync with the TSX."""
    out = []
    for seg in props['segments']:
        start = round(seg['start'] * fps)
        out.append(start)
        if props.get('style') != 'comic':
            cut = mid_cut(seg, fps)
            if cut is not None:
                out.append(start + cut)
            continue
        if seg['kind'] in ('lesson', 'ask'):
            continue
        dur, every = round(seg['end'] * fps) - start, 2 * fps
        marks = [round((t - seg['start']) * fps) for t in seg.get('words') or []] or [(k + 1) * every for k in range(dur // every)]
        last = 0
        for m in marks:
            if m - last >= every * 0.85 and dur - m >= fps:
                out.append(start + m)
                last = m
    return out


def problems(y, fps=30, planned=()):
    """Issues in a (frames, H, W) luma array. `planned` frames (cuts, and the flash or whip that may follow a line
    start) are allowed to jump: from 3 frames before to 10 frames after each."""
    near = lambda i: any(-3 <= i - p <= 10 for p in planned)  # noqa: E731
    mean = y.mean(axis=(1, 2))
    diff = np.abs(np.diff(y, axis=0)).mean(axis=(1, 2))
    out = []
    dark = [i for i in np.where(mean < 0.04)[0] if not near(i)]
    if dark:
        out.append(f'black frame at {dark[0] / fps:.1f}s')
    white = [i for i in np.where(mean > 0.93)[0] if not near(i)]
    if white:
        out.append(f'white flash at {white[0] / fps:.1f}s')
    run = 0
    for i, d in enumerate(diff):
        run = run + 1 if d < FROZEN else 0
        if run == 12:  # 12 frames with no change at all: something stopped animating
            out.append(f'frozen picture at {(i - 11) / fps:.1f}s')
    pad = np.pad(diff, 8, mode='edge')
    local = np.array([np.median(pad[k:k + 17]) for k in range(len(diff))])
    pops = [i + 1 for i in np.where(diff > 3 * local + POP)[0] if not near(i + 1)]
    out += [f'sudden pop at {i / fps:.1f}s' for i in pops[:2]]
    return out[:6]


# Thresholds, tuned on good Reels so they report nothing there (raise them if a good Reel gets flagged)
FROZEN = 0.0001  # good Reels never go below this (encoder noise, breathing, creeping cameras); a stuck render does
POP = 0.08


def sheet(video, path, every=1.0):
    """One frame every `every` seconds, 8 across, as one JPEG."""
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(video), '-vf',
                    f'fps=1/{every},scale=216:384,tile=8x4:padding=4:margin=4', '-frames:v', '1', '-q:v', '4', str(path)],
                   check=True, timeout=300)
    return path
