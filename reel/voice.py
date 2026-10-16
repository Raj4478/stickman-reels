"""Hindi narration with Gemini's free speech model, and the start time of every spoken line.

1. One speech call reads all lines, with a short pause between them. If the recording is far longer than
   the script, the model read its instructions aloud: it is re-recorded once with a minimal prompt.
2. The pauses are found with FFmpeg silencedetect, and each line starts at the clear pause closest to where
   its share of the text says it should; without clear pauses, timing falls back to that share.
"""
import base64
import os
import re
import subprocess
import wave

from . import gemini

DEFAULT_VOICE = 'Achird'  # friendly; set REEL_VOICE to try another (Sulafat, Charon, Kore, Puck...)
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
SHORT = 'Say in a warm, friendly Hindi storytelling voice, with a short pause between lines:\n\n{transcript}'


def speakable(text):
    text = re.sub(r'[☀-➿\U0001f000-\U0001faff]', '', text or '')
    return re.sub(r'\s+', ' ', text.replace('&', ' और ').replace('…', '...')).strip()


def expected_seconds(lines):
    """About 2.4 words a second plus a pause between lines."""
    return sum(len(speakable(line).split()) for line in lines) / 2.4 + .45 * len(lines)


def duration(path):
    with wave.open(str(path), 'rb') as wav:
        return wav.getnframes() / wav.getframerate()


def synthesize(lines, out):
    """Write out/voice.wav. Returns a record of the model and voice used."""
    voice = os.getenv('REEL_VOICE', '').strip() or DEFAULT_VOICE
    transcript = '\n\n'.join(speakable(line) for line in lines)
    limit = expected_seconds(lines) * 1.6 + 2
    path = out / 'voice.wav'
    for prompt in (NOTES, SHORT):
        audio, model = gemini.speech_call(prompt.format(transcript=transcript), voice)
        rate = int((re.search(r'rate=(\d+)', audio.get('mimeType', '')) or [0, 24000])[1])
        with wave.open(str(path), 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            wav.writeframes(base64.b64decode(audio['data']))
        if duration(path) <= limit:
            return {'model': model, 'voice': voice, 'seconds': round(duration(path), 2)}
        print(f'Narration ran {duration(path):.1f}s for about {limit:.0f}s of script (instructions read aloud?); retrying')
    path.unlink(missing_ok=True)
    raise gemini.GeminiError('the speech model kept reading its instructions aloud')


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
