"""Carousel slides and the weekly compilation, both made from finished Reels with FFmpeg.

Slides: 5 portrait images (1080x1350, Instagram's 4:5) cut from the Reel: the hook, three beats and the
lesson card. Carousels earn the most saves, and these cost nothing extra to make.

Compilation: the week's posted Reels joined into one long video ("इस हफ्ते की 5 सीख") between an intro and
an outro card rendered by Remotion (composition "Card"), with YouTube chapters for each lesson.
"""
import json
import subprocess
from pathlib import Path

CROP_TOP = 170  # keeps the caption, the stage and the subtitle of the 1080x1920 frame


def slide_times(props):
    segments = props['segments']
    scenes = [s for s in segments if s['kind'] == 'scene']
    if len(scenes) > 3:
        scenes = [scenes[0], scenes[len(scenes) // 2], scenes[-1]]
    lesson = next((s for s in segments if s['kind'] == 'lesson'), segments[-1])
    return [0.7, *(s['start'] + (s['end'] - s['start']) * 0.7 for s in scenes), min(lesson['start'] + 1.6, lesson['end'] - 0.1)]


def slides(folder, video):
    """Write folder/slides/1.jpg ... 5.jpg and return their paths."""
    folder = Path(folder)
    props = json.loads((folder / 'props.json').read_text(encoding='utf-8'))
    out = folder / 'slides'
    out.mkdir(exist_ok=True)
    paths = []
    for n, t in enumerate(slide_times(props), 1):
        path = out / f'{n}.jpg'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.2f}', '-i', str(video), '-frames:v', '1',
                        '-vf', f'crop=1080:1350:0:{CROP_TOP}', '-q:v', '3', str(path)], check=True, timeout=60)
        paths.append(path)
    return paths


def stamp(seconds):
    seconds = int(seconds)
    return f'{seconds // 60}:{seconds % 60:02d}'


def duration(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)],
                         capture_output=True, text=True, timeout=60).stdout
    return float(out.strip() or 0)


def join(clips, out):
    """Concatenate 1080x1920 clips (each with sound) into one video, re-encoded to a common format."""
    inputs, chains = [], []
    for i, clip in enumerate(clips):
        inputs += ['-i', str(clip)]
        chains.append(f'[{i}:v]scale=1080:1920,setsar=1,fps=30,format=yuv420p[v{i}];'
                      f'[{i}:a]aformat=sample_rates=48000:channel_layouts=stereo[a{i}]')
    pairs = ''.join(f'[v{i}][a{i}]' for i in range(len(clips)))
    graph = ';'.join(chains) + f';{pairs}concat=n={len(clips)}:v=1:a=1[v][a]'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *inputs, '-filter_complex', graph, '-map', '[v]', '-map', '[a]',
                    '-c:v', 'libx264', '-crf', '23', '-preset', 'veryfast', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart',
                    str(out)], check=True, timeout=1800)
    return out


def chapters(intro, reels):
    """YouTube chapters: (start, title) for the intro and each Reel."""
    marks, t = [(0.0, 'शुरुआत')], intro
    for title, length in reels:
        marks.append((t, title))
        t += length
    return marks


def description(marks, lessons):
    lines = ['इस हफ्ते की छोटी-छोटी कहानियाँ, बड़ी सीख। कौन सी सीख आपको सबसे अच्छी लगी? comment में बताइए।', '']
    lines += [f'{stamp(t)} {title}' for t, title in marks]
    lines += ['', 'सीख:'] + [f'• {lesson}' for lesson in lessons]
    lines += ['', 'रोज़ नई सीख के लिए subscribe करें। #hindi #lifelessons #stickman #motivation']
    return '\n'.join(lines)
