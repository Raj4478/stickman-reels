"""Storybook Reels: an original Hindi moral story told by a warm narrator over painted storybook illustrations, one
picture per beat (the bot's "🎨 Kahani" style).

The format follows the emotional illustrated-story Reels that do well in India (a village or small-town story of
rich and poor, parents and children, pride and kindness, with a twist and a moral), but every story, character and
picture is our own: Gemini writes the story and a picture prompt for each beat, and an image model paints them
(reel/images.py).

Character bible: the writer gives each person ONE fixed look (age, face, hair, clothes and colours). That exact
description goes into every picture they appear in, with the same seed, so a person looks the same all the way
through. The narration is Devanagari (for the voice); the on-screen captions are the same words in Roman Hinglish,
like the reference format.

`clean()` returns the story-script shape (hook, scenes, lesson, ask) so voice, timing, posting and the weekly report
work unchanged; each line also carries `roman`, `image` (the prompt), `cast` and `shot`.
"""
import json
import random
import re

from . import gemini
from . import script as stories

# The series strip at the top (Roman Hinglish, the first word drawn in yellow)
SERIES = {
    'samaaj': 'Samaaj ka sach',
    'rishte': 'Rishton ki keemat',
    'zindagi': 'Zindagi ki seekh',
    'maa_baap': 'Maa-baap ka pyaar',
    'dil': 'Dil ki baat',
    'insaniyat': 'Insaniyat zinda hai',
}
SHOTS = {
    'wide': 'a wide establishing view of the whole place, people small in the scene',
    'medium': 'a medium shot, people from the knees up, the place around them',
    'close': 'a close-up on one face or two faces, the emotion filling the frame',
    'detail': 'a close detail of an object or hands (a letter, empty plates, a gift, a coin)',
}
LIMITS = {'title': 40, 'line': 110, 'roman': 120, 'image': 420, 'look': 260, 'name': 16, 'setting': 400}
CHARACTER = {
    'type': 'object',
    'properties': {
        'id': {'type': 'string', 'description': 'a short lowercase id, e.g. kisan, beti, seth'},
        'name': {'type': 'string', 'description': 'how the story calls them, in Devanagari (e.g. रामू काका, सेठ जी)'},
        'look': {'type': 'string', 'description': 'ONE fixed look in English, used in every picture: age, gender, build, '
                                                  'face, hair or turban, moustache, clothes with exact colours, accessories'},
    },
    'required': ['id', 'name', 'look'],
}
LINE = {
    'type': 'object',
    'properties': {
        'line': {'type': 'string', 'description': 'One spoken Hindi sentence in Devanagari, 5-10 words'},
        'roman': {'type': 'string', 'description': 'The SAME words in Roman Hinglish, word for word, for the captions'},
        'image': {'type': 'string', 'description': 'The picture for this line, in English, starting with WHERE it happens '
                                                   '(a specific spot: the courtyard, a shop counter, a bus stop at night), then '
                                                   'who (by id) does what, their pose, the time of day and light and the '
                                                   'emotion on their faces. No text in the picture.'},
        'cast': {'type': 'array', 'items': {'type': 'string'}, 'description': 'ids of the characters in the picture'},
        'shot': {'type': 'string', 'enum': list(SHOTS)},
    },
    'required': ['line', 'roman', 'image', 'cast', 'shot'],
}
SCHEMA = {
    'type': 'object',
    'properties': {
        'topic': {'type': 'string', 'description': 'The moral in English, a few words'},
        'title': {'type': 'string', 'description': 'A short Hindi title for the post (Devanagari), at most 6 words'},
        'series': {'type': 'string', 'enum': list(SERIES)},
        'setting': {'type': 'string', 'description': 'The world of the story in English: the region, the era, the season '
                                                     'and the colour palette only (e.g. a Rajasthan village in winter, warm '
                                                     'ochre and marigold colours); NOT one specific spot'},
        'characters': {'type': 'array', 'minItems': 2, 'maxItems': 5, 'items': CHARACTER},
        'hook': LINE,
        'beats': {'type': 'array', 'minItems': 12, 'maxItems': 20, 'items': LINE},
        'moral': LINE,
        'ask': {'type': 'string', 'description': 'A short Hindi question for the comments (Devanagari), at most 10 words'},
        'ask_roman': {'type': 'string', 'description': 'The same question in Roman Hinglish'},
        'cover_text': {'type': 'string', 'description': 'The cover image text in Roman Hinglish: 2-4 words that tease the '
                                                        'story without giving the twist away'},
        'instagram_caption': {'type': 'string', 'description': 'Hindi Instagram caption, 2-3 short lines'},
        'hashtags': {'type': 'array', 'items': {'type': 'string'}, 'maxItems': 8},
    },
    'required': ['topic', 'title', 'series', 'setting', 'characters', 'hook', 'beats', 'moral', 'ask', 'ask_roman',
                 'cover_text', 'instagram_caption', 'hashtags'],
}

STORY_RULES = """Story rules (what makes illustrated moral-story Reels get watched to the end and shared in India):
  - The FIRST line sets up a contrast or a mystery in one breath ("एक ही गाँव में दो शादियाँ होने वाली थीं।"), never a
    greeting. The viewer must want to know how it ends.
  - A simple, emotional story from ordinary Indian life (a village, a small town, a mohalla, a school, a hospital, a
    railway station): rich and poor, parents and children, pride and kindness, a promise, a sacrifice.
  - Show, don't tell: small concrete details people can picture (empty chairs, a cold chai, a torn chappal, a
    lantern, marigolds, a letter, a borrowed sari). Each line is one picture.
  - The middle builds the feeling: the hero waits, hopes, is ignored or hurt; one beat makes the viewer's heart sink.
  - Then a TURN: an unexpected kindness, a reveal or a twist the viewer did not see coming, then the payoff.
  - The moral is one short memorable line that calls back to the first line ("क्योंकि याद रखना, इज़्ज़त दौलत से नहीं...").
  - Warm and respectful: nobody is mocked for being poor, for caste, religion, region or looks; no real people,
    brands, politics or religion-specific rituals as the point of the story; no violence or medical claims."""

WRITER = """You write scripts for "Seekh Sketch", a Hindi Instagram/YouTube channel of illustrated moral stories:
a warm narrator tells the story while a painted storybook picture shows each line.

Story idea: {topic}

Write ONE original story (never retell a known story, film or viral video) for 70-85 seconds of narration:
the hook line, {beats} beats, then the moral line; 150-185 spoken words in all (count them: more is too long).
Each line is 5-10 words.
{rules}
- Language: simple, emotional spoken Hindi in Devanagari, the way a grandparent tells a story (common English words
  in Devanagari are fine). Third person ("एक गरीब किसान था..."). Each line is ONE short sentence of 5-12 words.
- roman: the SAME words in Roman Hinglish for the on-screen captions, word for word in the same order (एक ही गाँव में ->
  "Ek hi gaon mein"). No English translation.
- characters: 2-5 people, each with an id, the name the story uses, and ONE fixed look in English that never
  changes: age, gender, build, face, hair or turban, moustache or beard, clothes with exact colours, accessories
  (e.g. "a thin farmer in his 50s, sun-browned skin, grey hair, thick grey moustache, off-white kurta with a cream
  gamchha over the shoulder, patched dhoti, brown chappals").
- setting: one English description of the world: place, region, era, colours and light.
- For every line, image: an English picture prompt of what we SEE in that moment, using character ids for the
  people ("kisan sits alone on a charpai outside his small mud house at night, a single lantern, empty plastic
  chairs lined up, he looks at the gate"); cast: the ids in the picture; shot: {shots}.
  Every image starts with its own specific spot, so the story moves through real places (a home, a courtyard, a
  shop, a street, a school...), and people DO things in it (sit, run, hand over, hug, look away), not just stand
  facing us. Vary the shots like a film (wide for a new place, medium for action, close for emotion, detail for
  objects) and keep the time of day consistent from line to line. Pictures never contain written text.
- series: the series strip ({series}); cover_text: 2-4 Roman words that tease the story.
- ask: a short question for the comments; ask_roman: the same in Roman Hinglish.
- instagram_caption: 2-3 short Hindi lines; hashtags: up to 8, Hindi and English.
{avoid}"""

EDITOR = """You are the story editor of a Hindi illustrated-story Reels channel. Make this story more moving and
more watchable to the end, then return the full script in the same JSON shape.

Draft:
{draft}

{rules}
Do all of this:
1. The hook line must make a stranger stop scrolling: a contrast, a mystery or a strong image, under 12 words.
2. Cut every line that only explains; every line must be a picture. Keep {beats_min}-{beats_max} beats and 150-185
   spoken words in all (count them), each line 5-10 words.
3. Make the turn a real surprise and the payoff warm; the moral calls back to the hook in its last words.
4. roman must be the same words as line, word for word.
5. Every image prompt starts with its specific spot, names the people by id, says what they do, the light and
   the feeling, and fits the line before it. Each character keeps exactly the look in the bible.
6. Never copy a known story, film or viral video."""


def short(text, limit):
    return stories.short(text, limit)


def roman_of(text, limit=LIMITS['roman']):
    """Roman Hinglish captions: letters, digits and simple punctuation only."""
    text = re.sub(r'[^A-Za-z0-9 ,.!?\'"-]', '', str(text or ''))
    return re.sub(r'\s+', ' ', text).strip()[:limit]


def clean_line(raw, ids):
    raw = raw if isinstance(raw, dict) else {'line': raw}
    line = short(raw.get('line'), LIMITS['line'])
    if not stories.DEVANAGARI.search(line):
        return None
    image = re.sub(r'\s+', ' ', str(raw.get('image') or '')).strip()[:LIMITS['image']]
    if not image:
        return None
    cast = [c for c in (raw.get('cast') or []) if c in ids][:4]
    shot = raw.get('shot') if raw.get('shot') in SHOTS else 'medium'
    return {'line': line, 'roman': roman_of(raw.get('roman')), 'image': image, 'cast': cast, 'shot': shot,
            'caption': '', 'keyword': '', 'sticker': 'none', 'speaker': 'narrator', 'with': 'none'}


def clean(raw):
    """A storybook script in the story-script shape, or ValueError if it is unusable."""
    people = []
    for c in (raw.get('characters') or [])[:5]:
        cid = re.sub(r'[^a-z0-9_]', '', str(c.get('id', '')).lower())[:20]
        look = re.sub(r'\s+', ' ', str(c.get('look') or '')).strip()[:LIMITS['look']]
        if cid and look and cid not in {p['id'] for p in people}:
            people.append({'id': cid, 'name': short(c.get('name'), LIMITS['name']), 'look': look})
    if not people:
        raise ValueError('the story has no characters with a look')
    ids = {p['id'] for p in people}
    hook = clean_line(raw.get('hook') or {}, ids)
    moral = clean_line(raw.get('moral') or {}, ids)
    if hook is None or moral is None:
        raise ValueError('the hook or the moral is not a Hindi line with a picture')
    beats = [b for b in (clean_line(x, ids) for x in (raw.get('beats') or [])[:20]) if b]
    if len(beats) < 8:
        raise ValueError(f'the story has only {len(beats)} usable beats (need at least 8)')
    script = {
        'style': 'storybook', 'topic': short(raw.get('topic'), 80), 'title': short(raw.get('title'), LIMITS['title']),
        'name': '', 'series': raw.get('series') if raw.get('series') in SERIES else 'zindagi',
        'setting': re.sub(r'\s+', ' ', str(raw.get('setting') or '')).strip()[:LIMITS['setting']],
        'characters': people,
        'hook': hook['line'], **{f'hook_{k}': hook[k] for k in ('roman', 'image', 'cast', 'shot')},
        'scenes': beats,
        'lesson': moral['line'], **{f'lesson_{k}': moral[k] for k in ('roman', 'image', 'cast', 'shot')},
        'ask': short(raw.get('ask'), 110), 'ask_roman': roman_of(raw.get('ask_roman')),
        'cover_text': roman_of(raw.get('cover_text'), 30),
        'music': 'warm', 'other_voice': 'friend', 'part': '', 'title_b': '',
        'instagram_caption': str(raw.get('instagram_caption') or '').strip()[:1500],
    }
    if not stories.DEVANAGARI.search(script['title']):
        script['title'] = short(hook['line'], LIMITS['title'])
    if not stories.DEVANAGARI.search(script['ask']):
        script['ask'], script['ask_roman'] = 'आपको यह कहानी कैसी लगी? कमेंट में बताइए।', 'Aapko yeh kahani kaisi lagi? Comment mein bataiye.'
    tags = [re.sub(r'[^\wऀ-ॿ]', '', str(t)) for t in raw.get('hashtags') or []]
    script['hashtags'] = list(dict.fromkeys(f'#{t}' for t in tags if t))[:8]
    return script


def write(topic=None, theme='', source=''):
    from . import growth
    topic, _ = stories.choose_topic(topic, theme, source)
    recent = [h.get('title') for h in stories.history()[-15:] if h.get('title')]
    n = random.choice((14, 16, 18))
    prompt = WRITER.format(topic=topic, beats=n, rules=STORY_RULES, shots=', '.join(f'{k} ({v})' for k, v in SHOTS.items()),
                           series=', '.join(f'{k} = "{v}"' for k, v in SERIES.items()),
                           avoid='\n'.join(x for x in (f'- Do not repeat these recent titles or their story: {", ".join(recent)}'
                                                       if recent else '', growth.lessons_learned()) if x))
    last = None
    for _ in range(2):
        draft, model = gemini.json_call(prompt, SCHEMA, temperature=1.0)
        try:
            drafted = clean(draft)
        except ValueError as exc:
            last = exc
            print(f'Draft rejected ({exc}); asking again')
            continue
        try:
            edited, _ = gemini.json_call(EDITOR.format(draft=json.dumps(draft, ensure_ascii=False, indent=1), rules=STORY_RULES,
                                                       beats_min=12, beats_max=20), SCHEMA, temperature=0.6)
            script = clean(edited)
            script['directed'] = True
        except (ValueError, gemini.GeminiError) as exc:
            print(f'Story edit skipped ({exc}); using the draft')
            script, script['directed'] = drafted, False
        script.update(model=model, hero='boy')
        script['topic'] = script['topic'] or topic
        return script
    raise ValueError(f'Gemini could not write a usable storybook script: {last}')
