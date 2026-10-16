"""The story script: a short Hindi life lesson, told in 4-6 beats that a stick figure acts out.

Gemini writes it as JSON against SCHEMA; `clean()` then enforces the rules the template depends on
(known actions and props only, Devanagari narration, length limits), so a sloppy answer can never
break the render.
"""
import random
import re
from pathlib import Path

from . import gemini

# Every action has an animation in remotion/src/actions.ts; every prop a drawing in remotion/src/engine/props.tsx.
ACTIONS = {
    'walk_in': 'walks in and stops (start of a journey, a normal day)',
    'think': 'hand on chin, thinking (doubt, a question, a decision)',
    'idea': 'a light bulb pops above the head (realisation, a new idea)',
    'sad': 'head down, shoulders low (failure, loneliness, regret)',
    'cheer': 'both arms up, celebrating (success, joy, reward)',
    'point': 'points at the caption (the key point, advice to the viewer)',
    'shrug': 'shrugs (excuses, confusion, "who cares")',
    'facepalm': 'facepalm (a silly mistake, wasted time)',
    'shock': 'jumps back in shock (a surprising truth)',
    'run': 'runs fast on the spot with speed lines (hurry, rat race, chasing goals)',
    'scroll_phone': 'sits and scrolls a phone (distraction, wasting time)',
    'fall_getup': 'trips and falls, then gets back up (failure and resilience)',
    'carry_burden': 'carries a heavy box overhead and wobbles (stress, responsibilities, overthinking)',
    'climb': 'climbs steps one by one (slow progress, consistency, discipline)',
    'handshake': 'shakes hands with a second figure (friendship, trust, helping someone)',
    'read': 'reads a book (learning, self-improvement)',
}
PROPS = {
    'none': 'nothing extra',
    'clock': 'a ticking clock (time)',
    'coin': 'a rupee coin (money)',
    'heart': 'a heart (love, family, kindness)',
    'trophy': 'a trophy (success, a goal)',
    'rain_cloud': 'a rain cloud (sadness, a bad phase)',
    'plant': 'a small plant that grows (growth, patience)',
    'mountain': 'a mountain with a flag (a big goal)',
}
MOODS = ('calm', 'happy', 'sad', 'tense')
LIMITS = {'title': 40, 'hook': 110, 'line': 150, 'caption': 40, 'lesson': 110, 'ask': 110}
DEVANAGARI = re.compile(r'[ऀ-ॿ]')

SCHEMA = {
    'type': 'object',
    'properties': {
        'topic': {'type': 'string', 'description': 'The life lesson in English, a few words'},
        'title': {'type': 'string', 'description': 'Hindi on-screen title, at most 5 words'},
        'hook': {'type': 'string', 'description': 'Hindi spoken opening line, at most 14 words'},
        'scenes': {'type': 'array', 'minItems': 4, 'maxItems': 6, 'items': {
            'type': 'object',
            'properties': {
                'line': {'type': 'string', 'description': 'Hindi narration for this beat, at most 20 words'},
                'caption': {'type': 'string', 'description': 'Hindi on-screen words for this beat, at most 5 words'},
                'action': {'type': 'string', 'enum': list(ACTIONS)},
                'prop': {'type': 'string', 'enum': list(PROPS)},
                'mood': {'type': 'string', 'enum': list(MOODS)},
            },
            'required': ['line', 'caption', 'action', 'prop', 'mood'],
        }},
        'lesson': {'type': 'string', 'description': 'Hindi spoken and on-screen takeaway, at most 12 words'},
        'ask': {'type': 'string', 'description': 'Hindi question to the viewer for the comments, at most 10 words'},
        'instagram_caption': {'type': 'string', 'description': 'Hindi Instagram caption, 2-3 short lines'},
        'hashtags': {'type': 'array', 'items': {'type': 'string'}, 'maxItems': 8},
    },
    'required': ['topic', 'title', 'hook', 'scenes', 'lesson', 'ask', 'instagram_caption', 'hashtags'],
}

PROMPT = """You write scripts for a Hindi Instagram Reels channel where a simple stick figure acts out a short life lesson.

Lesson for this Reel: {topic}

Write one tiny story (35-45 seconds when spoken) about an ordinary Indian person, told as {beats} beats.
- Language: natural spoken Hindi in Devanagari, the way a friend talks (simple words, common English words like
  "phone" or "goal" are fine in Devanagari). No Roman script, no emoji, no hashtags in the spoken lines.
- hook: the first spoken line. It must make people stop scrolling with something specific and a little surprising
  about the lesson. Never start with generic openers like "रुकिए", "सुनिए", "क्या आप जानते हैं".
- scenes: each beat is one spoken line plus 2-5 on-screen words, and ONE action the stick figure performs.
  Pick the action whose meaning matches the line:
{actions}
  Optionally add one prop next to the figure (use "none" most of the time):
{props}
  mood sets the colours: calm, happy, sad or tense. Use at least 3 different actions; the story should
  move from a problem to a turning point to a better place.
- lesson: the takeaway in one short memorable line (it closes the Reel on screen).
- ask: one question that viewers can answer in the comments.
- instagram_caption: 2-3 short Hindi lines; hashtags: up to 8, mixing Hindi and English tags.
- Keep it kind and real: no medical, legal or money promises, no real people, no religion or politics."""


def pick_topic(path=Path(__file__).resolve().parents[1] / 'topics.txt'):
    topics = [t.strip() for t in path.read_text(encoding='utf-8').splitlines() if t.strip() and not t.startswith('#')]
    return random.choice(topics)


def short(text, limit):
    text = re.sub(r'\s+', ' ', str(text or '')).strip()
    text = re.sub(r'[\U0001f000-\U0001faff☀-➿#*_`]', '', text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(' ', 1)[0]
    return cut.rstrip(',;:-') + ('।' if not cut.endswith(('।', '?', '!')) else '')


def clean(raw):
    """Return a script the template can always render, or raise ValueError if it is unusable."""
    script = {key: short(raw.get(key), limit) for key, limit in LIMITS.items() if key not in ('line', 'caption')}
    script['topic'] = short(raw.get('topic'), 80)
    scenes, used = [], set()
    for beat in (raw.get('scenes') or [])[:6]:
        line = short(beat.get('line'), LIMITS['line'])
        if not DEVANAGARI.search(line):
            continue
        action = beat.get('action') if beat.get('action') in ACTIONS else 'point'
        scenes.append({'line': line, 'caption': short(beat.get('caption'), LIMITS['caption']) or line[:LIMITS['caption']],
                       'action': action, 'prop': beat.get('prop') if beat.get('prop') in PROPS else 'none',
                       'mood': beat.get('mood') if beat.get('mood') in MOODS else 'calm'})
        used.add(action)
    if len(scenes) < 3:
        raise ValueError(f'the script has only {len(scenes)} usable Hindi beats (need at least 3)')
    for key in ('title', 'hook', 'lesson'):
        if not DEVANAGARI.search(script[key]):
            raise ValueError(f'the {key} is not in Hindi: {script[key]!r}')
    script['scenes'] = scenes
    script['instagram_caption'] = str(raw.get('instagram_caption') or '').strip()[:1500]
    tags = [re.sub(r'[^\wऀ-ॿ]', '', str(t)) for t in raw.get('hashtags') or []]
    script['hashtags'] = list(dict.fromkeys(f'#{t}' for t in tags if t))[:8]
    return script


def spoken_lines(script):
    """What the narrator says, in order: hook, every beat, the lesson, then the question."""
    return [script['hook'], *(s['line'] for s in script['scenes']), script['lesson'], script['ask']]


def write(topic=None):
    topic = (topic or '').strip() or pick_topic()
    prompt = PROMPT.format(
        topic=topic, beats=random.choice((4, 5)),
        actions='\n'.join(f'  - {k}: {v}' for k, v in ACTIONS.items()),
        props='\n'.join(f'  - {k}: {v}' for k, v in PROPS.items()))
    last = None
    for _ in range(2):
        raw, model = gemini.json_call(prompt, SCHEMA)
        try:
            script = clean(raw)
        except ValueError as exc:
            last = exc
            print(f'Script rejected ({exc}); asking again')
            continue
        script['model'] = model
        script['topic'] = script['topic'] or topic
        return script
    raise ValueError(f'Gemini could not write a usable script: {last}')
