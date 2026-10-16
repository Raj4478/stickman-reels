"""Hindi narration and dialogue, the start time of every spoken line, and the mouth movement.

1. Gemini's free speech model reads all lines in one call: one warm narrator voice, or (when the story has
   dialogue) two speakers: the narrator, who also voices the hero, and the other person with a voice that
   suits them (माँ, पापा, बॉस...). If the recording is far longer than the script, the model read its
   instructions aloud: it is re-recorded once with a minimal prompt.
2. When Gemini's speech fails (quota, outage), free Microsoft Edge neural voices read each line instead
   (hi-IN Madhur and Swara, pitch-shifted per character); the line times are then exact.
3. Otherwise the pauses are found with FFmpeg silencedetect, and each line starts at the clear pause closest
   to where its share of the text says it should.
4. mouth_curve() turns the loudness of each video frame into how wide the speaking figure's mouth opens.
"""
import asyncio
import base64
import os
import re
import subprocess
import tempfile
import wave
from pathlib import Path

from . import gemini

DEFAULT_VOICE = 'Achird'  # friendly; set REEL_VOICE to try another (Sulafat, Charon, Kore, Puck...)
# Gemini voices for the other person, by who they are
CAST_VOICES = {'mother': 'Sulafat', 'father': 'Algenib', 'boss': 'Alnilam', 'friend': 'Puck', 'partner': 'Despina',
               'child': 'Leda', 'stranger': 'Charon'}
# Edge backup voices: (voice, pitch, rate) for the narrator, the hero and each kind of other person
EDGE = {'narrator': ('hi-IN-MadhurNeural', '+0Hz', '+12%'), 'hero': ('hi-IN-MadhurNeural', '+6Hz', '+12%'),
        'mother': ('hi-IN-SwaraNeural', '-6Hz', '+0%'), 'partner': ('hi-IN-SwaraNeural', '+2Hz', '+6%'),
        'child': ('hi-IN-SwaraNeural', '+30Hz', '+10%'), 'father': ('hi-IN-MadhurNeural', '-14Hz', '-4%'),
        'boss': ('hi-IN-MadhurNeural', '-8Hz', '+0%'), 'friend': ('hi-IN-MadhurNeural', '+12Hz', '+8%'),
        'stranger': ('hi-IN-MadhurNeural', '-4Hz', '+0%')}
GAP = 0.42  # seconds of silence between lines in the Edge backup
# The bot's voice choice (NARRATOR=male/female): the Gemini narrator, and the Edge backup's narrator and hero
NARRATORS = {'male': ('Achird', 'hi-IN-MadhurNeural'), 'female': ('Sulafat', 'hi-IN-SwaraNeural')}


def narrator():
    """(Gemini voice, Edge voice) of the storyteller: REEL_VOICE wins, then NARRATOR, then male."""
    choice = NARRATORS.get(os.getenv('NARRATOR', '').strip().lower(), NARRATORS['male'])
    return os.getenv('REEL_VOICE', '').strip() or choice[0], choice[1]

NOTES = """# AUDIO PROFILE: A warm Indian storyteller sharing a short life lesson
## THE SCENE: Recording the voice-over for an animated Instagram Reel, speaking straight to one viewer.
### DIRECTOR'S NOTES
Style: Warm, sincere and gently energetic, like a big brother or sister telling a small story that matters.
Natural rhythm; never robotic, preachy or like a news announcer.
Pacing: brisk but clear, with a short, clear pause between lines.
Language and accent: Hindi, with a natural Indian accent.
Read only the transcript below, exactly as written. Never read these notes, headings or labels aloud.
#### TRANSCRIPT
{transcript}"""
DIALOGUE = """# AUDIO PROFILE: An animated Hindi Reel with a narrator and a {who}
### DIRECTOR'S NOTES
Narrator: a warm, sincere Indian storyteller; when he says the hero's own words he acts them, with feeling.
Other: the {who}, speaking naturally and in character, with real emotion.
Pacing: brisk but clear, with a short, clear pause between lines. Language: Hindi, natural Indian accent.
Read only the conversation below, exactly as written. Never read these notes or the speaker names aloud.
#### CONVERSATION
{transcript}"""
SHORT = 'Say in a warm, friendly Hindi storytelling voice, with a short pause between lines:\n\n{transcript}'
SHORT_DIALOGUE = 'TTS the following Hindi conversation between Narrator and Other, with a short pause between lines:\n\n{transcript}'
WHO = {'mother': 'mother', 'father': 'father', 'boss': 'strict boss', 'friend': 'close friend', 'partner': 'partner',
       'child': 'young child', 'stranger': 'stranger'}


def speakable(text):
    text = re.sub(r'[☀-➿\U0001f000-\U0001faff]', '', text or '')
    return re.sub(r'\s+', ' ', text.replace('&', ' और ').replace('…', '...')).strip()


def expected_seconds(lines):
    """About 2.4 words a second plus a pause between lines."""
    return sum(len(speakable(line).split()) for line in lines) / 2.4 + .45 * len(lines)


def duration(path):
    with wave.open(str(path), 'rb') as wav:
        return wav.getnframes() / wav.getframerate()


def write_pcm(path, data, rate):
    with wave.open(str(path), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(data)


def gemini_voice(turns, other, path):
    """Record with Gemini (one call). Returns the record, or raises GeminiError."""
    voice = narrator()[0]
    lines = [text for _, text in turns]
    dialogue = any(who == 'other' for who, _ in turns)
    if dialogue:
        speakers = {'Narrator': voice, 'Other': CAST_VOICES.get(other, 'Kore')}
        transcript = '\n'.join(f"{'Other' if who == 'other' else 'Narrator'}: {speakable(text)}" for who, text in turns)
        prompts = (DIALOGUE.format(who=WHO.get(other, 'friend'), transcript=transcript), SHORT_DIALOGUE.format(transcript=transcript))
    else:
        speakers = None
        transcript = '\n\n'.join(speakable(line) for line in lines)
        prompts = (NOTES.format(transcript=transcript), SHORT.format(transcript=transcript))
    limit = expected_seconds(lines) * 1.6 + 2
    for prompt in prompts:
        audio, model = gemini.speech_call(prompt, voice, speakers)
        rate = int((re.search(r'rate=(\d+)', audio.get('mimeType', '')) or [0, 24000])[1])
        write_pcm(path, base64.b64decode(audio['data']), rate)
        if duration(path) <= limit:
            return {'model': model, 'voice': voice, 'speakers': speakers, 'seconds': round(duration(path), 2)}
        print(f'Narration ran {duration(path):.1f}s for about {limit:.0f}s of script (instructions read aloud?); retrying')
    path.unlink(missing_ok=True)
    raise gemini.GeminiError('the speech model kept reading its instructions aloud')


def edge_voice(turns, other, path, rate=24000):
    """Record each line with free Edge voices and join them with short pauses. Returns the record with exact starts."""
    import edge_tts  # only needed for the backup

    async def say(text, voice, pitch, speed, target):
        await edge_tts.Communicate(text, voice, rate=speed, pitch=pitch).save(str(target))

    pcm, starts, t = b'', [], 0.0
    silence = b'\x00\x00' * int(rate * GAP)
    with tempfile.TemporaryDirectory() as tmp:
        for i, (who, text) in enumerate(turns):
            voice, pitch, speed = EDGE.get(other if who == 'other' else who, EDGE['narrator'])
            if who in ('narrator', 'hero'):
                voice = narrator()[1]
            mp3 = Path(tmp) / f'{i}.mp3'
            asyncio.run(say(speakable(text), voice, pitch, speed, mp3))
            raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(mp3), '-ac', '1', '-ar', str(rate), '-f', 's16le', '-'],
                                 capture_output=True, check=True, timeout=120).stdout
            starts.append(round(t, 3))
            pcm += raw + silence
            t += len(raw) / 2 / rate + GAP
    write_pcm(path, pcm, rate)
    return {'model': 'edge-tts', 'voice': narrator()[1], 'seconds': round(duration(path), 2), 'starts': starts,
            'speech_end': round(t - GAP, 3)}


def synthesize(turns, out, other='friend'):
    """Write out/voice.wav for `turns` [(speaker, text)] where speaker is narrator, hero or other.

    Returns a record of the service and voices used; it has exact 'starts' when the Edge backup recorded it.
    """
    path = out / 'voice.wav'
    try:
        return gemini_voice(turns, other, path)
    except (gemini.GeminiError, OSError) as exc:
        if any(who == 'other' for who, _ in turns):
            # Gemini still comes first: if only its two-voice dialogue failed, use its single storyteller voice
            try:
                record = gemini_voice([('narrator', text) for _, text in turns], other, path)
                record['dialogue'] = f'one voice (two voices failed: {str(exc)[:120]})'
                return record
            except (gemini.GeminiError, OSError) as single:
                exc = single
        try:
            record = edge_voice(turns, other, path)
        except Exception as backup:  # noqa: BLE001 - any failure here means no narration
            raise gemini.GeminiError(f'Gemini speech failed ({exc}) and so did the Edge backup ({backup})') from None
        gemini.note('Edge voices (hi-IN Madhur/Swara)', f'Gemini speech failed: {exc}')
        return record


def mouth_curve(path, fps=30):
    """How open the speaker's mouth is on each video frame (0..1), from the narration's loudness."""
    import numpy as np
    with wave.open(str(path), 'rb') as wav:
        rate = wav.getframerate()
        x = np.frombuffer(wav.readframes(wav.getnframes()), '<i2').astype(np.float32) / 32768
    hop = max(1, int(rate / fps))
    frames = len(x) // hop
    if not frames:
        return []
    rms = np.sqrt((x[:frames * hop].reshape(frames, hop) ** 2).mean(axis=1))
    peak = np.percentile(rms, 95) or 1.0
    level = np.clip(rms / peak, 0, 1)
    level[level < 0.12] = 0  # closed between words
    return [round(float(v), 2) for v in level]


def silences(path):
    log = subprocess.run(['ffmpeg', '-v', 'info', '-i', str(path), '-af', 'silencedetect=noise=-36dB:d=0.16',
                          '-f', 'null', '-'], capture_output=True, text=True, timeout=120).stderr
    starts = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', log)]
    ends = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', log)]
    return list(zip(starts, ends + [duration(path)] * (len(starts) - len(ends))))


def split(lines, total, gaps=()):
    """Start time of each line and when speech ends, from the pauses in a `total`-second recording."""
    speech_start = gaps[0][1] if gaps and gaps[0][0] < .05 else 0.0
    speech_end = gaps[-1][0] if gaps and gaps[-1][1] >= total - .05 else total
    inner = [g for g in gaps if g[0] > speech_start + .2 and g[1] < speech_end - .2]
    weights = [max(len(speakable(line)), 1) for line in lines]
    span, starts, used = speech_end - speech_start, [speech_start], 0.0
    for weight in weights[:-1]:
        used += weight
        expected = speech_start + span * used / sum(weights)
        # The clear pause (between lines, not a breath inside one) closest to where this line should end.
        near = [g for g in inner if abs((g[0] + g[1]) / 2 - expected) < span * .18 and (g[0] + g[1]) / 2 > starts[-1] + .4]
        clear = [g for g in near if g[1] - g[0] >= .25] or near
        pick = min(clear, key=lambda g: abs((g[0] + g[1]) / 2 - expected)) if clear else None
        starts.append((pick[0] + pick[1]) / 2 if pick else expected)
    return starts, speech_end


def line_times(path, lines):
    return split(lines, duration(path), silences(path))


def heard_words(path, transcript=''):
    """[(start, end)] of every word Whisper hears in the narration, or None when Whisper is not installed.

    Only the timing is used: Hindi transcription is imperfect, but where each word starts and ends is reliable.
    The script is passed as a prompt, which lets the "small" model (about 460 MB, cached between runs on Actions)
    hear nearly every Hindi word; WHISPER_MODEL picks another size.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    import numpy as np
    # Decode with FFmpeg (16 kHz mono float) rather than Whisper's own decoder, whose PyAV versions vary.
    pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'],
                         capture_output=True, check=True, timeout=120).stdout
    model = WhisperModel(os.getenv('WHISPER_MODEL', 'small'), device='cpu', compute_type='int8')
    segments, _ = model.transcribe(np.frombuffer(pcm, np.float32), language='hi', word_timestamps=True, beam_size=1,
                                   initial_prompt=transcript or None, condition_on_previous_text=False)
    return [(float(w.start), float(w.end)) for s in segments for w in (s.words or [])]


def word_times(lines, starts, speech_end, heard):
    """Start time of each written word of each line.

    The heard words inside a line's span are matched to its written words in order; when the counts differ,
    each written word takes the heard word at the same relative position. Without Whisper (or when it heard
    nothing in a line), words are spread by their length across the line.
    """
    ends = [*starts[1:], speech_end]
    out = []
    for line, a, b in zip(lines, starts, ends):
        words = speakable(line).split()
        inside = [w for w in heard or () if a - .15 <= w[0] < b - .05]
        if words and inside:
            n, m = len(words), len(inside)
            times = [inside[round(i * (m - 1) / max(n - 1, 1))][0] for i in range(n)]
            times[0] = max(a, min(times[0], inside[0][0]))
            times = [max(t, times[i - 1]) if i else t for i, t in enumerate(times)]  # never go backwards
        else:
            weights = [len(w) + 1 for w in words]
            spoken = min(b, a + sum(weights) * .075) - a
            times, acc = [], 0
            for w in weights:
                times.append(a + spoken * acc / max(sum(weights), 1))
                acc += w
        out.append([round(t, 3) for t in times])
    return out
