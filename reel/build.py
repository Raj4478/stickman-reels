"""Turn a script (and its narration) into remotion/public/props.json: every segment with its start, end and
word times, plus the music bed for this Reel."""
import json
import os
import shutil

from . import script as scripts
from . import gemini, sounds, voice

LEAD = 0.3      # silence before the narration starts
TAIL = 2.2      # the end card stays on screen after the last word
FALLBACK_RATE = 2.4  # words a second, for a silent preview


def segments(script, starts, speech_end, words=None):
    texts = scripts.spoken_lines(script)
    ends = [*starts[1:], speech_end]
    shift = lambda t: round(t + LEAD, 3)  # noqa: E731
    hook = {'kind': 'hook', 'text': script['hook'], 'title': script['title'], 'name': script.get('name', ''),
            'action': script.get('hook_action', 'shock'), 'with': script.get('hook_with', 'none'),
            'part': script.get('part', '')}
    out = [hook]
    out += [{'kind': 'scene', 'text': beat['line'], **beat} for beat in script['scenes']]
    out += [{'kind': 'lesson', 'text': script['lesson']}, {'kind': 'ask', 'text': script['ask'], 'part': script.get('part', '')}]
    for i, (segment, start, end) in enumerate(zip(out, starts, ends)):
        segment.pop('line', None)
        segment.update(start=shift(start), end=shift(end))
        if words:
            segment['words'] = [shift(t) for t in words[i]]
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


def build(script, out, public, narrate=True, music=True, prefix=''):
    """Write out/props.json and copy it (with the voice and music) to public/<prefix> for Remotion.

    `prefix` (e.g. "reels/2/") keeps several Reels of one run apart; props name files relative to public.
    """
    out.mkdir(parents=True, exist_ok=True)
    public = public / prefix
    public.mkdir(parents=True, exist_ok=True)
    (out / 'script.json').write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = scripts.spoken_lines(script)
    record, audio, heard, mouth = {'narration': 'none'}, None, None, []
    if narrate:
        try:
            record = voice.synthesize(scripts.spoken_turns(script), out, script.get('other_voice', 'friend'))
            if record.get('starts'):  # the Edge backup knows exactly where each line starts
                starts, speech_end = record.pop('starts'), record.pop('speech_end')
            else:
                starts, speech_end = voice.line_times(out / 'voice.wav', lines)
            mouth = voice.mouth_curve(out / 'voice.wav')
            shutil.copyfile(out / 'voice.wav', public / 'voice.wav')
            audio = f'{prefix}voice.wav'
        except Exception as exc:  # the Reel still renders (silent) so the visuals can be checked
            print(f'::warning::No narration: {exc}')
            record = {'narration': 'failed', 'reason': str(exc)[:300]}
    if audio:
        try:
            heard = voice.heard_words(out / 'voice.wav', ' '.join(lines))
            record['word_timing'] = f'whisper ({len(heard)} words heard)' if heard is not None else 'estimated'
        except Exception as exc:  # timing falls back to word lengths
            print(f'::warning::Whisper word timing failed: {exc}')
            record['word_timing'] = 'estimated'
    else:
        starts, speech_end = silent_times(script)
        (public / 'voice.wav').unlink(missing_ok=True)
    words = voice.word_times(lines, starts, speech_end, heard)
    props = {'audio': audio, 'music': None, 'lead': LEAD, 'handle': os.getenv('REEL_HANDLE', '').strip(),
             'mouth': mouth, 'hero': script.get('hero', 'boy'), 'segments': segments(script, starts, speech_end, words)}
    props['duration'] = props['segments'][-1]['end']
    if music:
        sounds.write_music(public / 'music.wav', props['duration'], script.get('music', 'warm'), script['title'])
        props['music'] = f'{prefix}music.wav'
    for folder in (out, public):
        (folder / 'props.json').write_text(json.dumps(props, ensure_ascii=False, indent=2), encoding='utf-8')
    if os.getenv('HOOK_TEST', '').strip().lower() == 'true' and script.get('title_b'):
        # the same Reel with the other on-screen hook, for an Instagram trial Reel (reel/publish.py)
        variant = json.loads(json.dumps(props))
        variant['segments'][0]['title'] = script['title_b']
        (public / 'props-b.json').write_text(json.dumps(variant, ensure_ascii=False, indent=2), encoding='utf-8')
    if gemini.USED:
        record['backups'] = list(gemini.USED)
    (out / 'voice-record.json').write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding='utf-8')
    return props, record
