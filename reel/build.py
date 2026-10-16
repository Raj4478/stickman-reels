"""Turn a script (and its narration) into remotion/public/props.json: every segment with its start and end."""
import json
import os
import shutil

from . import script as scripts
from . import voice

LEAD = 0.3      # silence before the narration starts
TAIL = 2.2      # the end card stays on screen after the last word
FALLBACK_RATE = 2.4  # words a second, for a silent preview


def segments(script, starts, speech_end):
    texts = scripts.spoken_lines(script)
    ends = [*starts[1:], speech_end]
    shift = lambda t: round(t + LEAD, 3)  # noqa: E731
    out = [{'kind': 'hook', 'text': script['hook'], 'title': script['title']}]
    out += [{'kind': 'scene', 'text': beat['line'], **beat} for beat in script['scenes']]
    out += [{'kind': 'lesson', 'text': script['lesson']}, {'kind': 'ask', 'text': script['ask']}]
    for segment, text, start, end in zip(out, texts, starts, ends):
        segment.pop('line', None)
        segment.update(start=shift(start), end=shift(end))
    out[0]['start'] = 0.0
    out[-1]['end'] = round(speech_end + LEAD + TAIL, 3)
    return out


def silent_times(script):
    lines = scripts.spoken_lines(script)
    starts, t = [], 0.0
    for line in lines:
        starts.append(t)
        t += len(voice.speakable(line).split()) / FALLBACK_RATE + .45
    return starts, t


def build(script, out, public, narrate=True):
    """Write out/props.json and copy it (with the voice) into the Remotion public folder."""
    out.mkdir(parents=True, exist_ok=True)
    public.mkdir(parents=True, exist_ok=True)
    (out / 'script.json').write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding='utf-8')
    record, audio = {'narration': 'none'}, None
    if narrate:
        try:
            record = voice.synthesize(scripts.spoken_lines(script), out)
            starts, speech_end = voice.line_times(out / 'voice.wav', scripts.spoken_lines(script))
            shutil.copyfile(out / 'voice.wav', public / 'voice.wav')
            audio = 'voice.wav'
        except Exception as exc:  # the Reel still renders (silent) so the visuals can be checked
            print(f'::warning::No narration: {exc}')
            record = {'narration': 'failed', 'reason': str(exc)[:300]}
    if not audio:
        starts, speech_end = silent_times(script)
        (public / 'voice.wav').unlink(missing_ok=True)
    props = {'audio': audio, 'lead': LEAD, 'handle': os.getenv('REEL_HANDLE', '').strip(),
             'segments': segments(script, starts, speech_end)}
    props['duration'] = props['segments'][-1]['end']
    for folder in (out, public):
        (folder / 'props.json').write_text(json.dumps(props, ensure_ascii=False, indent=2), encoding='utf-8')
    (out / 'voice-record.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    return props, record
