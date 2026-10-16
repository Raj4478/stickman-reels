"""The story script: a short Hindi life lesson, told in 4-6 beats that a stick figure acts out.

Two Gemini passes, both answering in SCHEMA:
1. The writer drafts the story and three hook options.
2. The director (a Reels motion director and editor) picks and sharpens the best hook, checks that every
   action matches its line, and plans the shots: camera angle, transition, place and who else is in frame.
`clean()` then enforces the rules the template depends on (known names only, Devanagari narration, length
limits, no shot used twice in a row), so a sloppy answer can never break the render.
"""
import json
import os
import random
import re
from pathlib import Path

from . import gemini

ROOT = Path(__file__).resolve().parents[1]

# Every action has an animation in remotion/src/actions.tsx; every prop a drawing in remotion/src/engine/props.tsx.
ACTIONS = {
    'walk_in': 'walks in and stops (start of a journey, a normal day)',
    'think': 'hand on chin, thinking (doubt, a question, a decision)',
    'idea': 'a light bulb pops above the head (realisation, a new idea)',
    'sad': 'head down, shoulders low (failure, loneliness, regret)',
    'cry': 'sits with knees up, tears falling (deep hurt, grief)',
    'cheer': 'jumps with both arms up (success, joy, reward)',
    'point': 'points at the caption (the key point, advice to the viewer)',
    'shrug': 'shrugs (excuses, confusion, "who cares")',
    'facepalm': 'facepalm (a silly mistake, wasted time)',
    'shock': 'jumps back in shock (a surprising truth)',
    'angry': 'stomps and shouts, steam and a jagged shout bubble (anger, frustration)',
    'run': 'runs fast on the spot with speed lines (hurry, rat race, chasing goals)',
    'scroll_phone': 'sits and scrolls a phone (distraction, wasting time)',
    'sleep_alarm': 'sleeps, the alarm rings, snoozes or jumps up (laziness, discipline, mornings)',
    'workout': 'does squats with a dumbbell (health, effort, discipline)',
    'work_late': 'types at a desk under a lamp at night (hard work, burnout, sacrifice)',
    'count_money': 'counts a growing stack of coins (saving, money, greed)',
    'fall_getup': 'trips and falls, then gets back up (failure and resilience)',
    'carry_burden': 'carries a heavy box overhead and wobbles (stress, responsibilities, overthinking)',
    'climb': 'climbs steps one by one (slow progress, consistency, discipline)',
    'read': 'reads a book (learning, self-improvement)',
    'walk_away': 'turns and walks away, then looks back (leaving, letting go, regret)',
    'handshake': 'shakes hands with the other person (friendship, trust, a deal)',
    'argue': 'shouts at the other person, who shouts back (a fight, ego, misunderstanding)',
    'hug': 'hugs the other person (love, forgiveness, family)',
    'help_up': 'the other person lies fallen; the hero pulls them up (helping, kindness, support)',
}
TWO_PERSON = ('handshake', 'argue', 'hug', 'help_up')
PROPS = {
    'none': 'nothing extra',
    'clock': 'a ticking clock (time)',
    'coin': 'a rupee coin (money)',
    'heart': 'a heart (love, family, kindness)',
    'trophy': 'a trophy (success, a goal)',
    'rain_cloud': 'a rain cloud over the head (sadness, a bad phase)',
    'plant': 'a small plant that grows (growth, patience)',
    'mountain': 'a mountain with a flag (a big goal)',
}
# The other person in frame. Two-person actions need one; for the rest they watch and react from the side.
CAST = {
    'none': 'nobody else',
    'friend': 'दोस्त',
    'mother': 'माँ',
    'father': 'पापा',
    'boss': 'बॉस',
    'partner': 'पार्टनर',
    'child': 'बच्चा',
    'stranger': 'अजनबी',
}
PLACES = {
    'plain': 'plain paper (abstract, inner thoughts)',
    'home': 'a room with a window and a picture frame',
    'office': 'an office with a desk and a wall clock',
    'street': 'a city street with buildings and a lamp post',
    'night': 'night sky with the moon and stars',
    'park': 'a park with trees and a bench',
    'classroom': 'a classroom with a blackboard',
}
SHOTS = {
    'wide': 'wide establishing shot, whole scene visible',
    'medium': 'medium shot, the figure fills the frame',
    'close': 'close-up on the face and upper body (emotion)',
    'extreme_close': 'extreme close-up on the face (shock, tears, a key realisation)',
    'low_angle': 'low angle looking up: the figure feels strong (triumph, confidence)',
    'high_angle': 'high angle looking down: the figure feels small (defeat, pressure)',
    'dutch': 'tilted frame (tension, anger, chaos)',
    'push_in': 'slow push in towards the face (realisation, building emotion)',
    'pull_out': 'slow pull back revealing the scene (aftermath, loneliness, perspective)',
    'pan': 'camera tracks sideways with the movement (journey, time passing)',
    'two_shot': 'both people framed side by side (relationship beats)',
}
TRANSITIONS = ('cut', 'whip', 'zoom', 'flash')
MOODS = ('calm', 'happy', 'sad', 'tense')
MUSIC = ('warm', 'tense')
LIMITS = {'title': 40, 'hook': 110, 'line': 150, 'caption': 40, 'lesson': 110, 'ask': 110, 'name': 16}
DEVANAGARI = re.compile(r'[ऀ-ॿ]')

BEAT = {
    'type': 'object',
    'properties': {
        'line': {'type': 'string', 'description': 'Hindi narration for this beat, at most 20 words'},
        'caption': {'type': 'string', 'description': 'Hindi on-screen words for this beat, at most 5 words'},
        'action': {'type': 'string', 'enum': list(ACTIONS)},
        'prop': {'type': 'string', 'enum': list(PROPS)},
        'mood': {'type': 'string', 'enum': list(MOODS)},
        'with': {'type': 'string', 'enum': list(CAST)},
        'place': {'type': 'string', 'enum': list(PLACES)},
        'shot': {'type': 'string', 'enum': list(SHOTS)},
        'transition': {'type': 'string', 'enum': list(TRANSITIONS)},
    },
    'required': ['line', 'caption', 'action', 'prop', 'mood', 'with', 'place', 'shot', 'transition'],
}
SCHEMA = {
    'type': 'object',
    'properties': {
        'topic': {'type': 'string', 'description': 'The life lesson in English, a few words'},
        'name': {'type': 'string', 'description': 'The hero\'s Hindi first name in Devanagari, e.g. राहुल'},
        'hooks': {'type': 'array', 'items': {'type': 'string'}, 'minItems': 1, 'maxItems': 3,
                  'description': 'Hindi spoken opening line options, at most 14 words each'},
        'hook': {'type': 'string', 'description': 'The chosen Hindi spoken opening line'},
        'title': {'type': 'string', 'description': 'Hindi on-screen hook text shown from the first frame, at most 5 words'},
        'hook_action': {'type': 'string', 'enum': list(ACTIONS), 'description': 'The most dramatic action of the story, shown during the hook'},
        'scenes': {'type': 'array', 'minItems': 4, 'maxItems': 6, 'items': BEAT},
        'lesson': {'type': 'string', 'description': 'Hindi spoken and on-screen takeaway, at most 12 words'},
        'ask': {'type': 'string', 'description': 'Hindi question to the viewer for the comments, at most 10 words'},
        'music': {'type': 'string', 'enum': list(MUSIC)},
        'instagram_caption': {'type': 'string', 'description': 'Hindi Instagram caption, 2-3 short lines'},
        'hashtags': {'type': 'array', 'items': {'type': 'string'}, 'maxItems': 8},
    },
    'required': ['topic', 'name', 'hooks', 'hook', 'title', 'hook_action', 'scenes', 'lesson', 'ask', 'music',
                 'instagram_caption', 'hashtags'],
}

HOOK_RULES = """Hook rules (the first 2 seconds decide if people keep watching):
  - Be specific and concrete: a number, a time, a person, a moment. Never vague or preachy.
  - Use one proven pattern: a surprising number ("दस साल की दोस्ती, साठ सेकंड में खत्म।"), a mistake the viewer
    makes ("आप भी सुबह उठते ही ये गलती करते हैं।"), a contrast ("उसके पास सब था, सिवाय एक चीज़ के।"),
    a mystery ("एक छोटी सी आदत ने उसकी पूरी ज़िंदगी बदल दी।") or a direct "you" challenge.
  - Never start with generic openers like "रुकिए", "सुनिए", "क्या आप जानते हैं", "आज हम बात करेंगे".
  - title is the on-screen version: 2-5 punchy words that create curiosity (not the whole line)."""

WRITER = """You write scripts for a Hindi Instagram Reels channel where a simple stick figure acts out a short life lesson.

Lesson for this Reel: {topic}
{series}
Write one tiny story (30-40 seconds when spoken) about an ordinary Indian person named in `name`, told as {beats} beats.
- Language: natural spoken Hindi in Devanagari, the way a friend talks (simple words, common English words like
  "phone" or "goal" are fine in Devanagari). No Roman script, no emoji, no hashtags in the spoken lines.
- hooks: three different opening lines; hook: the strongest of them.
{hook_rules}
- scenes: each beat is one spoken line plus 2-5 on-screen words, and ONE action the stick figure performs.
  The action must SHOW what the line says (shouting -> angry or argue, not carry_burden):
{actions}
  Two-person actions ({two}) need `with` set to who the other person is; otherwise `with` may add a person who
  watches and reacts, or "none":
{cast}
  Optionally add one prop (use "none" most of the time):
{props}
  place is where the beat happens:
{places}
  mood sets the colours. The story must move from a problem to a turning point to a better place, and use at
  least 3 different actions.
- shot and transition: plan them like a film director (see the list below); the director pass will refine them.
{shots}
  transition into this beat: cut (default), whip (fast pan for energy or time jumps), zoom (into a realisation),
  flash (a shock or a sudden memory).
- hook_action: the most dramatic action of the story; it is shown while the hook is spoken.
- lesson: the takeaway in one short memorable line (it closes the Reel on screen).
- ask: one question that viewers can answer in the comments.
- music: warm (most stories) or tense (anger, fear, conflict-heavy stories).
- instagram_caption: 2-3 short Hindi lines; hashtags: up to 8, mixing Hindi and English tags.
- Keep it kind and real: no medical, legal or money promises, no real people, no religion or politics.
{avoid}"""

DIRECTOR = """You are the motion director and editor of a Hindi stickman Reels channel. Your job: make this Reel
impossible to scroll past and visually cinematic, then return the full improved script in the same JSON shape.

Draft script:
{draft}

Do all of this:
1. Hook: judge the three hooks against the rules below, then write the final `hook` (you may sharpen the best one)
   and a punchy `title`.
{hook_rules}
2. Actions: every beat's action must visibly SHOW its line. Fix any mismatch using only these actions:
{actions}
   Two-person actions ({two}) must have `with` set to a person.
3. Shots: plan the camera like a film. Rules:
   - Never use the same shot twice in a row. Open wide or medium, go closer as emotion rises, use low_angle
     for the triumph beat, high_angle or pull_out for defeat or loneliness, dutch for anger, extreme_close or
     push_in for the realisation, two_shot for beats with two people, pan for movement or time passing.
   - Transitions: cut by default; whip for energy or "months later"; zoom into a realisation; flash for a shock.
   Shots: {shot_names}
4. Places: keep a believable continuity (the same place for beats that happen together), from: {place_names}.
5. Tighten every spoken line (at most 20 words) so it sounds natural when read aloud; keep the story's meaning.
6. Keep the lesson, ask, caption and hashtags unless they are weak; never add Roman script to spoken lines."""


def history_path():
    return Path(os.getenv('REEL_HISTORY', ROOT / 'history.json'))


def history():
    try:
        return json.loads(history_path().read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return []


def remember(script):
    items = history() + [{'topic': script['topic'], 'title': script['title'], 'name': script.get('name', '')}]
    history_path().write_text(json.dumps(items[-200:], ensure_ascii=False, indent=1), encoding='utf-8')


def pick_topic(path=ROOT / 'topics.txt'):
    """A random topic, avoiding the last 25 used."""
    topics = [t.strip() for t in path.read_text(encoding='utf-8').splitlines() if t.strip() and not t.startswith('#')]
    recent = {h.get('topic', '').strip().lower() for h in history()[-25:]}
    fresh = [t for t in topics if t.lower() not in recent]
    return random.choice(fresh or topics)


def short(text, limit):
    text = re.sub(r'\s+', ' ', str(text or '')).strip()
    text = re.sub(r'[\U0001f000-\U0001faff☀-➿#*_`]', '', text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(' ', 1)[0]
    return cut.rstrip(',;:-') + ('।' if not cut.endswith(('।', '?', '!')) else '')


def pick(value, allowed, default):
    return value if value in allowed else default


def clean(raw):
    """Return a script the template can always render, or raise ValueError if it is unusable."""
    script = {key: short(raw.get(key), limit) for key, limit in LIMITS.items() if key not in ('line', 'caption')}
    script['topic'] = short(raw.get('topic'), 80)
    if not DEVANAGARI.search(script['name']):
        script['name'] = ''
    scenes, last_shot = [], None
    for beat in (raw.get('scenes') or [])[:6]:
        line = short(beat.get('line'), LIMITS['line'])
        if not DEVANAGARI.search(line):
            continue
        action = pick(beat.get('action'), ACTIONS, 'point')
        cast = pick(beat.get('with'), CAST, 'none')
        if action in TWO_PERSON and cast == 'none':
            cast = 'friend'
        shot = pick(beat.get('shot'), SHOTS, 'medium')
        if action in TWO_PERSON and shot in ('close', 'extreme_close'):
            shot = 'two_shot'  # a close-up would cut the other person out
        if shot == last_shot:
            shot = 'medium' if shot != 'medium' else 'wide'
        last_shot = shot
        scenes.append({
            'line': line, 'caption': short(beat.get('caption'), LIMITS['caption']) or line[:LIMITS['caption']],
            'action': action, 'prop': pick(beat.get('prop'), PROPS, 'none'), 'mood': pick(beat.get('mood'), MOODS, 'calm'),
            'with': cast, 'place': pick(beat.get('place'), PLACES, 'plain'), 'shot': shot,
            'transition': pick(beat.get('transition'), TRANSITIONS, 'cut'),
        })
    if len(scenes) < 3:
        raise ValueError(f'the script has only {len(scenes)} usable Hindi beats (need at least 3)')
    if not script['hook']:
        script['hook'] = short(next((h for h in raw.get('hooks') or [] if DEVANAGARI.search(str(h))), ''), LIMITS['hook'])
    for key in ('title', 'hook', 'lesson'):
        if not DEVANAGARI.search(script[key]):
            raise ValueError(f'the {key} is not in Hindi: {script[key]!r}')
    script['scenes'] = scenes
    script['hook_action'] = pick(raw.get('hook_action'), ACTIONS, max(scenes, key=lambda s: s['mood'] == 'tense')['action'])
    if script['hook_action'] in TWO_PERSON:
        script['hook_with'] = next((s['with'] for s in scenes if s['action'] == script['hook_action']), 'friend')
    script['music'] = pick(raw.get('music'), MUSIC, 'warm')
    script['part'] = str(raw.get('part') or '')
    script['instagram_caption'] = str(raw.get('instagram_caption') or '').strip()[:1500]
    tags = [re.sub(r'[^\wऀ-ॿ]', '', str(t)) for t in raw.get('hashtags') or []]
    script['hashtags'] = list(dict.fromkeys(f'#{t}' for t in tags if t))[:8]
    return script


def spoken_lines(script):
    """What the narrator says, in order: hook, every beat, the lesson, then the question."""
    return [script['hook'], *(s['line'] for s in script['scenes']), script['lesson'], script['ask']]


def catalog(items):
    return '\n'.join(f'  - {k}: {v}' for k, v in items.items())


def series_note(part, previous):
    if not part:
        return ''
    if part == '1/2':
        return ('This is PART 1 of a 2-part story. End on a cliffhanger: the last beat leaves the problem unsolved, '
                'and `ask` must tease part 2 (e.g. "भाग 2 में देखिए उसने क्या किया।").')
    return (f'This is PART 2 of a 2-part story. Part 1 was: {json.dumps(previous, ensure_ascii=False)}\n'
            'Keep the same hero name, continue from the cliffhanger, and the hook must remind viewers in a few words.')


def write(topic=None, part='', previous=None):
    topic = (topic or '').strip() or pick_topic()
    recent = [h.get('title') for h in history()[-15:] if h.get('title')]
    prompt = WRITER.format(
        topic=topic, beats=random.choice((4, 5)), hook_rules=HOOK_RULES, two=', '.join(TWO_PERSON),
        actions=catalog(ACTIONS), cast=catalog(CAST), props=catalog(PROPS), places=catalog(PLACES), shots=catalog(SHOTS),
        series=series_note(part, previous),
        avoid=f'- Do not repeat these recent titles or their angle: {", ".join(recent)}' if recent else '')
    last = None
    for _ in range(2):
        draft, model = gemini.json_call(prompt, SCHEMA)
        try:
            clean(draft)
        except ValueError as exc:
            last = exc
            print(f'Draft rejected ({exc}); asking again')
            continue
        try:
            directed, _ = gemini.json_call(DIRECTOR.format(
                draft=json.dumps(draft, ensure_ascii=False, indent=1), hook_rules=HOOK_RULES, actions=catalog(ACTIONS),
                two=', '.join(TWO_PERSON), shot_names=', '.join(SHOTS), place_names=', '.join(PLACES)), SCHEMA, temperature=0.6)
            script = clean(directed)
            script['directed'] = True
        except (ValueError, gemini.GeminiError) as exc:
            print(f'Director pass skipped ({exc}); using the draft')
            script = clean(draft)
            script['directed'] = False
        script['model'] = model
        script['topic'] = script['topic'] or topic
        script['part'] = part
        return script
    raise ValueError(f'Gemini could not write a usable script: {last}')
