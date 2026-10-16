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
