"""Quality check of a rendered Reel before it is sent for review.

Hard checks (FFmpeg): the length is 20-60 seconds, the video is 1080x1920, there is sound, and the voice is
not too quiet. A Gemini look at four frames (the cover, two beats and the end card) then reports text that is
cut off, overlapping or unreadable, or a figure cut off by the frame. Problems are listed in the Telegram
caption; nothing is blocked, because you decide with the ✅ Post button.

The Instagram lint (what its originality and Reels rules look for): a full 1080x1920 frame with no black letterbox
or pillarbox bars, under 3 minutes, captions a small share of the frame, and a perceptual hash of the video that
must not match an earlier Reel (a re-upload is "unoriginal content" and loses reach). The hashes live in the topic
history (history.json).
"""
import json
import re
import subprocess
import tempfile
from pathlib import Path

from . import gemini, script

SCHEMA = {
    'type': 'object',
    'properties': {
        'ok': {'type': 'boolean'},
        'issues': {'type': 'array', 'items': {'type': 'string'}, 'maxItems': 5,
                   'description': 'Short, specific problems, e.g. "frame 2: caption cut off at the right edge"'},
    },
    'required': ['ok', 'issues'],
}
PROMPT = """These are frames (in order) of a vertical Hindi Instagram Reel with a stick-figure cartoon: the opening,
the story beats and the end card. Check them like a strict video editor. Report only real problems a viewer
would notice:
- text cut off at an edge of the frame, or overlapping other text
- text covering the stick figure's face, or unreadable text (too small, low contrast)
- a figure accidentally cut off by the frame, or an empty-looking frame
- anything important (a face, a caption, a subtitle) inside the phone's UI areas: in these 540-pixel-wide frames,
  the top 135 px, the bottom 230 px, or the right 70 px below y 575
- captions or text boxes that cover a big part of the picture (more than about a fifth of the frame)
Hindi in Devanagari is expected. A small pencil cursor on the end card is intentional. In comic Reels a big-headed
cartoon kid sits behind a table, so only the upper body shows, and a short Roman-letter title strip sits at the
top: both are intentional. Be brief."""


def probe(video):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=codec_type,width,height',
                          '-of', 'json', str(video)], capture_output=True, text=True, timeout=60).stdout
    info = json.loads(out or '{}')
    streams = info.get('streams', [])
    video_stream = next((s for s in streams if s.get('codec_type') == 'video'), {})
    return {'duration': float(info.get('format', {}).get('duration', 0)), 'audio': any(s.get('codec_type') == 'audio' for s in streams),
            'width': video_stream.get('width'), 'height': video_stream.get('height')}


def loudness(video):
    log = subprocess.run(['ffmpeg', '-v', 'info', '-i', str(video), '-vn', '-af', 'volumedetect', '-f', 'null', '-'],
                         capture_output=True, text=True, timeout=120).stderr
    found = re.search(r'mean_volume: (-?[\d.]+) dB', log)
    return float(found.group(1)) if found else None


REELS_LIMIT = 180  # seconds: longer videos are not recommended as Reels


def hard_checks(video, narrated=True, shortest=20, longest=60):
    info = probe(video)
    issues = []
    if info['duration'] >= REELS_LIMIT:
        issues.append(f"length is {info['duration']:.0f}s: Instagram only recommends Reels under 3 minutes")
    elif not shortest <= info['duration'] <= longest:
        issues.append(f"length is {info['duration']:.0f}s (best {shortest}-{longest}s)")
    if (info['width'], info['height']) != (1080, 1920):
        issues.append(f"size is {info['width']}x{info['height']} (expected 1080x1920)")
    if not info['audio']:
        issues.append('the video has no sound')
    elif narrated:
        level = loudness(video)
        if level is not None and level < -28:  # every Reel is loudness-normalised now (-14 LUFS)
            issues.append(f'the sound is very quiet ({level:.0f} dB)')
    return info, issues


# --- the Instagram lint ------------------------------------------------------------------------

SMALL = (108, 192)  # grey frames for the border check
DARK = 22           # a bar is darker than this everywhere (0-255)
BAR = 0.04          # a band this deep at an edge (4 %, 77 px of 1920)


def gray(video, at, size):
    """One frame at `at` seconds as a list of grey rows (size = width, height)."""
    w, h = size
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{max(0, at):.2f}', '-i', str(video), '-frames:v', '1',
                          '-vf', f'scale={w}:{h},format=gray', '-f', 'rawvideo', '-'], capture_output=True, timeout=60).stdout
    if len(raw) < w * h:
        return None
    return [list(raw[r * w:(r + 1) * w]) for r in range(h)]


def bars(frames_):
    """The edges with a flat dark band in every frame that stops sharply at brighter picture in at least one:
    letterbox (top, bottom) or pillarbox (left, right). A dark night picture fades out; a bar has an edge."""
    frames_ = [f for f in frames_ if f]
    if not frames_:
        return []
    h, w = len(frames_[0]), len(frames_[0][0])
    edges = {  # the lines of pixels from each edge inwards
        'top': lambda f: f[:h // 2], 'bottom': lambda f: f[::-1][:h // 2],
        'left': lambda f: [list(col) for col in zip(*f)][:w // 2], 'right': lambda f: [list(col) for col in zip(*f)][::-1][:w // 2],
    }
    found = []
    for name, lines in edges.items():
        per_frame = [lines(f) for f in frames_]
        size = h if name in ('top', 'bottom') else w
        depth = 0
        while depth < len(per_frame[0]) and all(max(ls[depth]) < DARK and max(ls[depth]) - min(ls[depth]) < 8 for ls in per_frame):
            depth += 1
        if depth < max(2, round(size * BAR / 2)) or depth >= len(per_frame[0]):
            continue
        # the picture starts within a couple of lines (scaling blurs the edge by a line)
        inside = [sum(line) / len(line) for ls in per_frame for line in ls[depth:depth + 3]]
        if max(inside) > 3 * DARK:
            found.append(name)
    return found


def caption_share(props):
    """The biggest share of the frame that caption text covers (an estimate from the props and the caption boxes
    drawn in the TSX: CAPTION_BOX). Captions are one or two short lines, so this stays small."""
    box = CAPTION_BOX.get(props.get('style') or 'story', CAPTION_BOX['story'])
    worst = 0
    for seg in props.get('segments', []):
        if seg.get('kind') == 'ask':
            continue  # the question card closes the Reel on purpose
        words = (seg.get('roman') or seg.get('text') or '').split()
        page, longest = 0, 0
        for w in words:  # pages of at most `chars` characters, like the TSX
            if page and page + len(w) + 1 > box['chars']:
                longest, page = max(longest, page), 0
            page += len(w) + 1
        lines = -(-max(longest, page) // box['line_chars'])
        worst = max(worst, (box['width'] * lines * box['line_height'] + box['pad']) / (1080 * 1920))
    return round(worst, 3)


# The caption boxes as drawn: storybook/StoryBook.tsx Captions (68 px, 1.25) and StickReel.tsx Subtitle (52 px, 1.4)
CAPTION_BOX = {'storybook': {'chars': 22, 'line_chars': 26, 'line_height': 85, 'width': 980, 'pad': 0},
               'story': {'chars': 22, 'line_chars': 30, 'line_height': 73, 'width': 960, 'pad': 40},
               'comic': {'chars': 22, 'line_chars': 30, 'line_height': 73, 'width': 960, 'pad': 40}}
CAPTION_LIMIT = 0.08  # captions may cover at most 8 % of the frame


def dhash(rows):
    """A 64-bit difference hash of a 9x8 grey frame."""
    bits = 0
    for row in rows:
        for a, b in zip(row, row[1:]):
            bits = bits << 1 | (a > b)
    return f'{bits:016x}'


def fingerprint(video, duration, n=6):
    """Perceptual hashes of `n` frames spread through the video (skipping the very start and end)."""
    out = []
    for i in range(n):
        rows = gray(video, duration * (i + 1) / (n + 1), (9, 8))
        if rows:
            out.append(dhash(rows))
    return out


def distance(a, b):
    return bin(int(a, 16) ^ int(b, 16)).count('1')


def same_video(a, b, bits=8):
    """True when two fingerprints match: most frames are within `bits` of each other."""
    pairs = list(zip(a, b))
    return bool(pairs) and sum(distance(x, y) <= bits for x, y in pairs) >= max(2, round(len(pairs) * 0.67))


def reupload(story, prints, history=None):
    """The title of an earlier Reel this one looks like, else ''. Then stores this Reel's hashes in its history
    entry (the newest entry with its title and no hashes yet), so later Reels are checked against it."""
    items = history if history is not None else script.history()
    mine = next((h for h in reversed(items) if h.get('title') == story.get('title') and not h.get('phash')), None)
    match = next((h.get('title', '?') for h in items if h is not mine and h.get('phash') and same_video(prints, h['phash'])), '')
    if mine is not None and prints:
        mine['phash'] = prints
        if history is None:
            script.history_path().write_text(json.dumps(items[-200:], ensure_ascii=False, indent=1), encoding='utf-8')
    return match


def lint(folder, video, props, info):
    """The Instagram lint: problems as short lines."""
    issues = []
    duration = info['duration'] or props.get('duration', 0)
    found = bars([gray(video, duration * k / 5, SMALL) for k in (1, 2, 3, 4)])
    if found:
        issues.append(f"black bars at the {' and '.join(found)} edge: Instagram wants a full 1080x1920 frame")
    share = caption_share(props)
    if share > CAPTION_LIMIT:
        issues.append(f'captions cover {share:.0%} of the frame (keep them under {CAPTION_LIMIT:.0%})')
    story_path = Path(folder) / 'script.json'
    story = json.loads(story_path.read_text(encoding='utf-8')) if story_path.exists() else {}
    prints = fingerprint(video, duration)
    earlier = reupload(story, prints)
    if earlier:
        issues.append(f'looks like an earlier Reel ("{earlier}"): Instagram treats re-uploads as unoriginal')
    return issues


def frames(video, props, folder):
    """JPEG frames at the cover, two beats and the end card."""
    segments = props['segments']
    scenes = [s for s in segments if s['kind'] == 'scene'] or segments
    # the cover, the middle of up to six lines (every line in a comic Reel) and the end card
    times = [0.7, *[(s['start'] + s['end']) / 2 for s in scenes][:6], props['duration'] - 1.2]
    paths = []
    for i, t in enumerate(times):
        path = Path(folder) / f'frame{i}.jpg'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{max(0, t):.2f}', '-i', str(video), '-frames:v', '1',
                        '-vf', 'scale=540:-1', '-q:v', '4', str(path)], check=True, timeout=60)
        paths.append(path)
    return paths


def check(folder, video):
    """Write folder/quality.json and return it: {'ok', 'issues', 'looked': bool}."""
    folder, video = Path(folder), Path(video)
    props = json.loads((folder / 'props.json').read_text(encoding='utf-8'))
    # a comic rant is meant to be short (15-25 seconds)
    # a storybook Reel is a full story: 75-95 seconds, well within Reels' and Shorts' limits
    info, issues = hard_checks(video, narrated=bool(props.get('audio')), shortest=12 if props.get('style') == 'comic' else 20,
                               longest=120 if props.get('style') == 'storybook' else 60)
    try:
        issues += lint(folder, video, props, info)
    except Exception as exc:  # noqa: BLE001 - the lint is a bonus, like the visual check
        print(f'Instagram lint skipped: {exc}')
    try:
        from . import scan
        issues += scan.problems(scan.frames(video), planned=scan.planned_cuts(props))
        scan.sheet(video, folder / 'sheet.jpg')
    except Exception as exc:  # noqa: BLE001 - the scan is a bonus, like the visual check
        print(f'Frame scan skipped: {exc}')
    looked = False
    try:
        with tempfile.TemporaryDirectory() as tmp:
            family = '\nThis is a family Reel: also report anything a child could copy and get hurt by, or anything mean, scary or rude.'
            answer, _ = gemini.vision_json(PROMPT + (family if props.get('audience') in ('kids', 'family') else ''),
                                           frames(video, props, tmp), SCHEMA)
        looked = True
        issues += [str(i)[:160] for i in answer.get('issues', []) if str(i).strip()][:5]
    except Exception as exc:  # noqa: BLE001 - the visual check is a bonus; the Reel is still sent
        print(f'Visual check skipped: {exc}')
    result = {'ok': not issues, 'issues': issues, 'looked': looked, 'duration': round(info['duration'], 1)}
    (folder / 'quality.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print('Quality check:', 'ok' if result['ok'] else '; '.join(issues))
    return result


def note(folder):
    """A line for the Telegram caption, or '' when everything looked fine."""
    path = Path(folder) / 'quality.json'
    if not path.exists():
        return ''
    result = json.loads(path.read_text(encoding='utf-8'))
    if result.get('ok'):
        return '✅ Quality check passed' + ('' if result.get('looked') else ' (visual check skipped)')
    return '⚠️ Check before posting:\n' + '\n'.join(f'• {i}' for i in result['issues'])
