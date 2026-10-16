"""Quality check of a rendered Reel before it is sent for review.

Hard checks (FFmpeg): the length is 20-60 seconds, the video is 1080x1920, there is sound, and the voice is
not too quiet. A Gemini look at four frames (the cover, two beats and the end card) then reports text that is
cut off, overlapping or unreadable, or a figure cut off by the frame. Problems are listed in the Telegram
caption; nothing is blocked, because you decide with the ✅ Post button.
"""
import json
import re
import subprocess
import tempfile
from pathlib import Path

from . import gemini

SCHEMA = {
    'type': 'object',
    'properties': {
        'ok': {'type': 'boolean'},
        'issues': {'type': 'array', 'items': {'type': 'string'}, 'maxItems': 5,
                   'description': 'Short, specific problems, e.g. "frame 2: caption cut off at the right edge"'},
    },
    'required': ['ok', 'issues'],
}
PROMPT = """These are 4 frames (in order) of a vertical Hindi Instagram Reel with a stick-figure cartoon: the opening,
two story beats and the end card. Check them like a strict video editor. Report only real problems a viewer
would notice:
- text cut off at an edge of the frame, or overlapping other text
- text covering the stick figure's face, or unreadable text (too small, low contrast)
- a figure accidentally cut off by the frame, or an empty-looking frame
Hindi in Devanagari is expected. A small pencil cursor on the end card is intentional. Be brief."""


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


def hard_checks(video, narrated=True):
    info = probe(video)
    issues = []
    if not 20 <= info['duration'] <= 60:
        issues.append(f"length is {info['duration']:.0f}s (best 20-60s)")
    if (info['width'], info['height']) != (1080, 1920):
        issues.append(f"size is {info['width']}x{info['height']} (expected 1080x1920)")
    if not info['audio']:
        issues.append('the video has no sound')
    elif narrated:
        level = loudness(video)
        if level is not None and level < -35:
            issues.append(f'the sound is very quiet ({level:.0f} dB)')
    return info, issues


def frames(video, props, folder):
    """JPEG frames at the cover, two beats and the end card."""
    segments = props['segments']
    scenes = [s for s in segments if s['kind'] == 'scene'] or segments
    times = [0.7, (scenes[0]['start'] + scenes[0]['end']) / 2, (scenes[-1]['start'] + scenes[-1]['end']) / 2,
             props['duration'] - 1.2]
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
    info, issues = hard_checks(video, narrated=bool(props.get('audio')))
    looked = False
    try:
        with tempfile.TemporaryDirectory() as tmp:
            answer, _ = gemini.vision_json(PROMPT, frames(video, props, tmp), SCHEMA)
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
