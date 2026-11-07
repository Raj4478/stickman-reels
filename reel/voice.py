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
               'child': 'Leda', 'stranger': 'Charon', 'teacher': 'Gacrux', 'grandma': 'Vindemiatrix', 'sibling': 'Leda'}
# A girl hero's partner is a young man
PARTNER_OF_GIRL = ('Orus', ('hi-IN-MadhurNeural', '+8Hz', '+6%'))
# Edge backup voices: (voice, pitch, rate) for the narrator, the hero and each kind of other person
EDGE = {'narrator': ('hi-IN-MadhurNeural', '+0Hz', '+12%'), 'hero': ('hi-IN-MadhurNeural', '+6Hz', '+12%'),
        'mother': ('hi-IN-SwaraNeural', '-6Hz', '+0%'), 'partner': ('hi-IN-SwaraNeural', '+2Hz', '+6%'),
        'child': ('hi-IN-SwaraNeural', '+30Hz', '+10%'), 'father': ('hi-IN-MadhurNeural', '-14Hz', '-4%'),
        'boss': ('hi-IN-MadhurNeural', '-8Hz', '+0%'), 'friend': ('hi-IN-MadhurNeural', '+12Hz', '+8%'),
        'stranger': ('hi-IN-MadhurNeural', '-4Hz', '+0%'), 'teacher': ('hi-IN-MadhurNeural', '-10Hz', '-2%'),
        'grandma': ('hi-IN-SwaraNeural', '-10Hz', '-8%'), 'sibling': ('hi-IN-SwaraNeural', '+18Hz', '+8%')}
GAP = 0.42  # seconds of silence between lines in the Edge backup
# The bot's voice choice (NARRATOR=male/female): the Gemini narrator, and the Edge backup's narrator and hero
NARRATORS = {'male': ('Achird', 'hi-IN-MadhurNeural'), 'female': ('Sulafat', 'hi-IN-SwaraNeural')}
# Comic Reels (reel/comic.py): Gemini's casual, easy-going voices, which sound like a real person talking rather
# than a performer. The Edge backup keeps its natural pitch (pitching it up sounds robotic), only a little faster.
COMIC_NARRATORS = {'male': ('Zubenelgenubi', 'hi-IN-MadhurNeural'), 'female': ('Callirrhoe', 'hi-IN-SwaraNeural')}
COMIC_EDGE = {'male': ('+0Hz', '+8%'), 'female': ('+0Hz', '+6%')}
COMIC_GAP = 0.3  # a rant runs on: shorter pauses than a story
# Kids and family comic Reels: bright, youthful voices (try Fenrir "excitable" or Puck "upbeat" for a boy)
KID_NARRATORS = {'male': ('Puck', 'hi-IN-MadhurNeural'), 'female': ('Leda', 'hi-IN-SwaraNeural')}
KID_EDGE = {'male': ('+14Hz', '+0%'), 'female': ('+10Hz', '+0%')}  # a little higher, not faster: kids need time to read


def narrator(style='story', audience='adult'):
    """(Gemini voice, Edge voice) of the storyteller: REEL_VOICE wins, then NARRATOR, then male."""
    voices = KID_NARRATORS if style == 'comic' and audience != 'adult' else COMIC_NARRATORS if style == 'comic' else NARRATORS
    choice = voices.get(os.getenv('NARRATOR', '').strip().lower(), voices['male'])
    return os.getenv('REEL_VOICE', '').strip() or choice[0], choice[1]

NOTES = """# AUDIO PROFILE: A young Indian person telling a short story from their own life
## THE SCENE: Recording the voice-over for an animated Instagram Reel, speaking straight to one viewer.
### DIRECTOR'S NOTES
Style: Personal and sincere, like confiding in a close friend: a little shy in the sweet moments, a little
broken in the sad ones, warm and hopeful at the end. It is their own story, so they feel every line.
Natural rhythm; never robotic, preachy or like a news announcer.
Pacing: brisk but clear, with a short, clear pause between lines.
Language and accent: Hindi, with a natural Indian accent.
Read only the transcript below, exactly as written. Never read these notes, headings or labels aloud.
#### TRANSCRIPT
{transcript}"""
# A dialogue goes to Gemini as one part per line, each tagged with its speaker and a delivery style (the 3.8
# speech models refuse a "Narrator: ..." transcript). The style takes the place of the director's notes.
DIALOGUE_STYLES = {
    'story': ('Sincere and personal, the hero telling their own story to a close friend in natural Hindi; their own '
              'words in a scene are acted with feeling',
              'The {who}, speaking naturally and in character, with real emotion, in natural Hindi'),
    'comic': ('A real, natural person (never a cartoon dub) with cheeky, playful energy: quick, expressive and a '
              'little mischievous, mock-dramatic where it is funny and dry on the deadpan lines, in everyday Hindi',
              'The {who}, calling from another room: real, exasperated and natural, the way family shouts at home'),    'kids': ('A real, cheeky 8-to-10-year-old Indian kid (never an adult doing a kid voice): bright, playful and full of '
             'mischief, with big honest reactions, a little slower than an adult, in simple everyday Hindi',
             'The {who}, calling from another room: real, warm and natural, the way family talks at home'),
}
KIDS_NOTES = """# AUDIO PROFILE: A real, cheeky 8-to-10-year-old Indian kid telling the viewer about their latest big plan
## THE SCENE: At home, talking to a phone camera, bursting with energy. Not an adult doing a kid voice.
### DIRECTOR'S NOTES
Style: bright, playful and full of mischief, with big honest reactions: proud when the plan sounds great, a
gasp when it goes wrong, a little giggle on the sneaky lines, mock-panic on the disasters. Natural kid speech,
never a cartoon squeak, never a news reader.
Pacing: lively but clear, a little slower than an adult so kids can follow, with a short pause between lines
and a tiny pause before the last line, said with a cheeky grin in the voice.
Language and accent: simple everyday Hindi with a natural Indian accent.
Read only the transcript below, exactly as written. Never read these notes, headings or labels aloud.
#### TRANSCRIPT
{transcript}"""
COMIC_PUNCH = ', after a tiny pause, with a cheeky, pleased-with-yourself grin in the voice'  # the punchline
COMIC_NOTES = """# AUDIO PROFILE: A real young person from a small Indian town, venting to a friend about their own life
## THE SCENE: Sitting at the desk at home, talking into a phone camera, unscripted. Nobody is performing.
### DIRECTOR'S NOTES
Style: completely natural and conversational, exactly like a real person talking, never a voice actor, a cartoon
voice or an announcer. Lively and cheeky: playful, quick and a little mischievous, with mock-dramatic moments
(a fake sob, an outraged "क्या?!") and dry, deadpan lines in between; the switches are what make it funny. Real speech: small breaths, a slight drag on words like "बस" and "अब", a
little sigh where it fits, natural rises and falls instead of a sing-song pattern, the odd word said a touch faster.
Pacing: brisk, lively talking speed, never slow, with a short pause between lines and a tiny pause before the
last line, which is said with a cheeky grin in the voice.
Language and accent: everyday Hindi with a natural Indian accent and a light UP/Bihar flavour, the way people
actually talk at home.
Read only the transcript below, exactly as written. Never read these notes, headings or labels aloud.
#### TRANSCRIPT
{transcript}"""
COMIC_SHORT = ('Say this naturally, like a real, cheeky person talking to a friend: lively, playful and conversational, '
               'in everyday Hindi, with a short pause between lines:\n\n{transcript}')
SHORT = 'Say in a warm, friendly Hindi storytelling voice, with a short pause between lines:\n\n{transcript}'
# Storybook Reels (reel/storybook.py): a warm storyteller telling a moral story, like a grandparent at night
STORYBOOK_NOTES = """# AUDIO PROFILE: A warm Indian storyteller telling a short, moving moral story
## THE SCENE: Recording the voice-over for an illustrated story Reel, speaking gently to one listener at night.
### DIRECTOR'S NOTES
Style: warm, sincere and emotional, like a grandparent telling a story everyone remembers: soft and slow in the sad
moments, a held breath before the turn, a little catch in the voice when the kindness comes, and calm conviction on
the last line. Never dramatic like a TV serial, never robotic or like a news reader.
Pacing: unhurried but never slow, with a clear pause between lines and a longer pause before the moral.
Language and accent: Hindi, with a natural Indian accent.
Read only the transcript below, exactly as written. Never read these notes, headings or labels aloud.
#### TRANSCRIPT
{transcript}"""
WHO = {'mother': 'mother', 'father': 'father', 'boss': 'strict boss', 'friend': 'close friend', 'partner': 'partner',
       'child': 'young child', 'stranger': 'stranger', 'teacher': 'strict school teacher', 'grandma': 'loving grandmother',
       'sibling': 'bossy elder sister'}


def girl_hero():
    return os.getenv('NARRATOR', '').strip().lower() == 'female'


def cast_voice(other):
    """The Gemini voice of the other person (a girl hero's partner is a young man)."""
    return PARTNER_OF_GIRL[0] if other == 'partner' and girl_hero() else CAST_VOICES.get(other, 'Kore')


def edge_cast(other):
    return PARTNER_OF_GIRL[1] if other == 'partner' and girl_hero() else EDGE.get(other, EDGE['narrator'])


# Mouth shapes: M (lips closed, the start of म ब प फ), O (round), E (wide), A (open, the default)
ROUND = set('ओऔउऊोौुू')
WIDE = set('ईइएऐिीेै')
CLOSED = set('मबपफ')


def vowel_shape(text):
    for ch in text:
        if ch in ROUND:
            return 'O'
        if ch in WIDE:
            return 'E'
    return 'A'


def visemes(segments, duration, fps=30):
    """One letter per video frame of the whole Reel: the mouth shape of the word being said, ' ' between words.
    Segments are props segments (times already include the lead); words without times are skipped."""
    frames = [' '] * (int(duration * fps) + 1)
    for seg in segments:
        words, times = seg.get('text', '').split(), seg.get('words') or []
        if len(words) != len(times):
            continue
        ends = [*times[1:], seg['end']]
        for word, t0, t1 in zip(words, times, ends):
            a, b = int(t0 * fps), min(len(frames), int(min(t1, t0 + 0.7) * fps))
            if word[:1] in CLOSED:
                frames[a:min(b, a + 2)] = ['M'] * len(frames[a:min(b, a + 2)])
                a += 2
            frames[a:b] = [vowel_shape(word)] * len(frames[a:b])
    return ''.join(frames)


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


def gemini_voice(turns, other, path, style='story', audience='adult'):
    """Record with Gemini (one call). Returns the record, or raises GeminiError."""
    voice = narrator(style, audience)[0]
    comic = style == 'comic'
    kid = comic and audience != 'adult'
    lines = [text for _, text in turns]
    dialogue = any(who == 'other' for who, _ in turns)
    if dialogue:
        speakers = {'Narrator': voice, 'Other': cast_voice(other)}
        hero_style, other_style = DIALOGUE_STYLES['kids' if kid else 'comic' if comic else 'story']
        other_style = other_style.format(who=WHO.get(other, 'friend'))
        # the comic punchline is the line before the closing question
        punch = len(turns) - 2 if comic else -1
        tagged = [('Other', speakable(text), other_style) if who == 'other' else
                  ('Narrator', speakable(text), hero_style + (COMIC_PUNCH if i == punch else '')) for i, (who, text) in enumerate(turns)]
        # with the delivery styles first, then plain turns if the recording runs long
        prompts = (tagged, [(who, text, '') for who, text, _ in tagged])
    else:
        speakers = None
        transcript = '\n\n'.join(speakable(line) for line in lines)
        notes = STORYBOOK_NOTES if style == 'storybook' else KIDS_NOTES if kid else COMIC_NOTES if comic else NOTES
        prompts = (notes.format(transcript=transcript),
                   (COMIC_SHORT if comic else SHORT).format(transcript=transcript))
    limit = expected_seconds(lines) * (1.15 if kid else 1) * 1.6 + 2  # a kid's read is a little slower
    for prompt in prompts:
        audio, model = gemini.speech_call(prompt, voice, speakers)
        rate = int((re.search(r'rate=(\d+)', audio.get('mimeType', '')) or [0, 24000])[1])
        write_pcm(path, base64.b64decode(audio['data']), rate)
        if duration(path) <= limit:
            return {'model': model, 'voice': voice, 'speakers': speakers, 'seconds': round(duration(path), 2)}
        print(f'Narration ran {duration(path):.1f}s for about {limit:.0f}s of script (instructions read aloud?); retrying')
    path.unlink(missing_ok=True)
    raise gemini.GeminiError('the speech model kept reading its instructions aloud')


def edge_voice(turns, other, path, rate=24000, style='story', audience='adult'):
    """Record each line with free Edge voices and join them with short pauses. Returns the record with exact starts."""
    import edge_tts  # only needed for the backup

    async def say(text, voice, pitch, speed, target):
        await edge_tts.Communicate(text, voice, rate=speed, pitch=pitch).save(str(target))

    pcm, starts, t = b'', [], 0.0
    gap = COMIC_GAP if style == 'comic' else GAP
    silence = b'\x00\x00' * int(rate * gap)
    with tempfile.TemporaryDirectory() as tmp:
        for i, (who, text) in enumerate(turns):
            voice, pitch, speed = edge_cast(other) if who == 'other' else EDGE.get(who, EDGE['narrator'])
            if who in ('narrator', 'hero'):
                voice = narrator(style, audience)[1]
                if style == 'comic':
                    pitch, speed = (KID_EDGE if audience != 'adult' else COMIC_EDGE)['female' if girl_hero() else 'male']
            mp3 = Path(tmp) / f'{i}.mp3'
            asyncio.run(say(speakable(text), voice, pitch, speed, mp3))
            raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(mp3), '-ac', '1', '-ar', str(rate), '-f', 's16le', '-'],
                                 capture_output=True, check=True, timeout=120).stdout
            starts.append(round(t, 3))
            pcm += raw + silence
            t += len(raw) / 2 / rate + gap
    write_pcm(path, pcm, rate)
    return {'model': 'edge-tts', 'voice': narrator(style, audience)[1], 'seconds': round(duration(path), 2), 'starts': starts,
            'speech_end': round(t - gap, 3)}


def synthesize(turns, out, other='friend', style='story', audience='adult'):
    """Write out/voice.wav for `turns` [(speaker, text)] where speaker is narrator, hero or other.

    Returns a record of the service and voices used; it has exact 'starts' when the Edge backup recorded it.
    """
    path = out / 'voice.wav'
    try:
        return gemini_voice(turns, other, path, style, audience)
    except (gemini.GeminiError, OSError) as exc:
        if any(who == 'other' for who, _ in turns):
            # Gemini still comes first: if only its two-voice dialogue failed, use its single storyteller voice
            try:
                record = gemini_voice([('narrator', text) for _, text in turns], other, path, style, audience)
                record['dialogue'] = f'one voice (two voices failed: {str(exc)[:120]})'
                return record
            except (gemini.GeminiError, OSError) as single:
                exc = single
        try:
            record = edge_voice(turns, other, path, style=style, audience=audience)
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
    audio = np.frombuffer(pcm, np.float32)

    def listen(prompt, beam):
        segments, _ = model.transcribe(audio, language='hi', word_timestamps=True, beam_size=beam,
                                       initial_prompt=prompt or None, condition_on_previous_text=False)
        return [(float(w.start), float(w.end)) for s in segments for w in (s.words or [])]
    heard = listen(transcript, 1)
    written = len(transcript.split())
    if written and len(heard) < written * 0.6:
        # the script as a prompt sometimes makes Whisper skip most of a voice ("already said"): listen again without it
        again = listen('', 5)
        print(f'Whisper heard {len(heard)} of {written} words with the script as a hint, {len(again)} without it')
        heard = max(heard, again, key=len)
    return heard


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
