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
    'shy': 'hands under the chin, blushing and swaying, little hearts rise (a crush, first love, butterflies)',
    'propose': 'kneels and holds out a rose; the other person gasps, then says yes (confessing love, a proposal)',
}
TWO_PERSON = ('handshake', 'argue', 'hug', 'help_up', 'propose')
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
    'teacher': 'टीचर',
}
PLACES = {
    'plain': 'plain paper (abstract, inner thoughts)',
    'home': 'a room with a window and a picture frame',
    'office': 'an office with a desk and a wall clock',
    'street': 'a city street with buildings and a lamp post',
    'night': 'night sky with the moon and stars',
    'park': 'a park with trees and a bench',
    'classroom': 'a classroom with a blackboard',
    'kitchen': 'a home kitchen with a stove and shelves',
    'bus': 'inside a city bus with windows and a hand rail',
    'hospital': 'a hospital room with a bed and a drip stand',
    'sunset': 'outdoors at sunset, orange sky (endings, hope, reflection)',
    'rain': 'a street in the rain (sadness, struggle)',
    'day_to_night': 'outdoors while day turns into night (time passing, long hours)',
}
SPEAKERS = {
    'narrator': 'the hero tells the story as a voice-over, in first person (most beats)',
    'hero': 'the hero says something out loud in the scene, as dialogue',
    'other': 'the person in `with` says their words to the hero, as dialogue',
}
STICKERS = ('none', 'fire', 'star', 'check', 'cross', 'lightning', 'money', 'heart', 'warning', 'hundred', 'question')
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
STYLES = ('story', 'comic')  # comic: a cartoon kid's deadpan rant with a punchline (reel/comic.py)
# Themes the bot offers (key: Hindi label, what the writer should pick a lesson about)
THEMES = {
    'love': ('प्यार', 'love: a first crush, one-sided love, waiting for a reply, a breakup, long distance, love that '
                      'lasts, love vs attention'),
    'family': ('परिवार', 'family: parents, siblings, children, respect and sacrifice at home'),
    'money': ('पैसा', 'money: saving, spending, debt, showing off and financial discipline'),
    'health': ('सेहत', 'health: sleep, food, exercise, phone addiction and mental peace'),
    'study': ('पढ़ाई', 'studies and exams: focus, consistency, failure and marks'),
    'friendship': ('दोस्ती', 'friendship: trust, true friends, fake friends and loyalty'),
    'work': ('काम', 'work and career: effort, bosses, colleagues, learning skills and patience'),
    'self_respect': ('आत्मसम्मान', 'self-respect: saying no, people pleasing, confidence and boundaries'),
    'relationships': ('रिश्ते', 'relationships: ego, anger, forgiveness, communication and time'),
    'habits': ('आदतें', 'habits: discipline, small daily actions, laziness and mornings'),
    'time': ('समय', 'time: wasting time, procrastination, priorities and regret'),
}
SOURCES = ('random', 'ideas', 'occasion')
LIMITS = {'title': 40, 'title_b': 40, 'hook': 110, 'line': 150, 'caption': 40, 'lesson': 110, 'ask': 110, 'name': 16}
DEVANAGARI = re.compile(r'[ऀ-ॿ]')

BEAT = {
    'type': 'object',
    'properties': {
        'line': {'type': 'string', 'description': 'Hindi narration for this beat, at most 12 words'},
        'caption': {'type': 'string', 'description': 'Hindi on-screen words for this beat, at most 5 words'},
        'action': {'type': 'string', 'enum': list(ACTIONS)},
        'prop': {'type': 'string', 'enum': list(PROPS)},
        'mood': {'type': 'string', 'enum': list(MOODS)},
        'with': {'type': 'string', 'enum': list(CAST)},
        'place': {'type': 'string', 'enum': list(PLACES)},
        'shot': {'type': 'string', 'enum': list(SHOTS)},
        'transition': {'type': 'string', 'enum': list(TRANSITIONS)},
        'speaker': {'type': 'string', 'enum': list(SPEAKERS)},
        'keyword': {'type': 'string', 'description': 'The one word of the caption to animate (copied exactly), or ""'},
        'sticker': {'type': 'string', 'enum': list(STICKERS)},
    },
    'required': ['line', 'caption', 'action', 'prop', 'mood', 'with', 'place', 'shot', 'transition', 'speaker', 'keyword', 'sticker'],
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
        'title_b': {'type': 'string', 'description': 'A second on-screen hook text with a different angle, at most 5 words (for an A/B test)'},
        'hook_action': {'type': 'string', 'enum': list(ACTIONS), 'description': 'The most dramatic action of the story, shown during the hook'},
        'scenes': {'type': 'array', 'minItems': 5, 'maxItems': 8, 'items': BEAT},
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
  - The hero is speaking about their own life, so hooks are first person. Use one proven pattern: a confession
    ("तीन साल मैंने उसके एक मैसेज का इंतज़ार किया।"), a surprising number ("दस साल की दोस्ती, मैंने साठ सेकंड
    में खत्म कर दी।"), a mistake ("सुबह उठते ही मैं यही गलती करता था।"), a contrast ("मेरे पास सब था, सिवाय एक चीज़
    के।") or a mystery ("एक छोटी सी आदत ने मेरी पूरी ज़िंदगी बदल दी।").
  - Never start with generic openers like "रुकिए", "सुनिए", "क्या आप जानते हैं", "आज हम बात करेंगे".
  - title is the on-screen version: 2-5 punchy words that create curiosity (not the whole line)."""

WRITER = """You write scripts for a Hindi Instagram Reels channel where a simple stick figure acts out a short life lesson.

Lesson for this Reel: {topic}
{series}
Write one tiny story (40-50 seconds when spoken, about 110 words), told as {beats} short beats of at most 12
words each, about a real-feeling moment from ordinary Indian life (school, college, home, office, tiffin time, a
bus, a phone call). Many short beats, each with its own action and place or shot, keep the Reel moving.
- Tone: lively and funny like a cartoon, with naughty-kid energy: at least 2 comic moments (an over-the-top
  reaction, a cheeky comeback, a silly misunderstanding, a facepalm moment) on the way to the lesson. The comedy
  is gentle and on the hero, never on other people's looks, caste, religion, region or gender; the ending still
  lands the lesson with real feeling.
- FIRST PERSON: the hero ({hero}, named in `name`) tells their OWN story, like confiding in a friend. Every
  narration line uses मैं / मैंने / मेरा / मेरी / मुझे ("उस दिन मैंने पहली बार उसे देखा..."), never "वह", "उसने"
  or the hero's name for the hero. Other people are "वो", "माँ", "पापा", "टीचर". Use {forms} verb forms for the
  hero, every time.
- Love stories are the channel's favourites (a crush, waiting for a reply, a breakup, love that lasts). In a love
  story, use the actions shy, propose, hug, walk_away and the partner.
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
- speaker: make 1-2 beats DIALOGUE so it feels like a real story: the hero says something out loud in the
  scene (speaker "hero", e.g. "बस पाँच मिनट और...") or the person in `with` speaks to the hero (speaker "other",
  e.g. पापा: "बेटा, तुम्हारे सपनों का क्या हुआ?"). Write dialogue as the spoken words only (no "उसने कहा"). Only ONE other
  person may speak in the whole Reel. All other beats: "narrator".
{speakers}
- keyword: the single most important word of the caption (copied exactly); sticker: a small icon that
  punches up the beat ("none" most of the time): {stickers}.
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
   and a punchy `title`, plus `title_b`: a second on-screen title with a clearly different angle (for example a
   number vs a question), so both can be tested.
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
5. Tighten every spoken line (at most 12 words) so it sounds natural when read aloud; keep the story's meaning,
   its 2+ comic moments and its lively pace (5-8 beats).
   Keep 1-2 dialogue beats (speaker hero, or speaker other with `with` set; only ONE other person speaks in the
   Reel); dialogue is the spoken words only, in character. Pick each caption's `keyword` (copied exactly) and
   a sticker only where it adds punch.
6. Keep the lesson, ask, caption and hashtags unless they are weak; never add Roman script to spoken lines.
7. First person: the hero ({hero}) tells their own story. Rewrite any narration or hook that talks about the hero
   in the third person ("उसने", "वह", the hero's name) into first person (मैंने, मैं, मेरा), with {forms} verb
   forms."""


def history_path():
    return Path(os.getenv('REEL_HISTORY', ROOT / 'history.json'))


def history():
    try:
        return json.loads(history_path().read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return []


def remember(script):
    import datetime as dt
    entry = {'topic': script['topic'], 'title': script['title'], 'name': script.get('name', ''),
             'made': dt.date.today().isoformat()}
    if script.get('occasion'):
        entry['occasion'] = script['occasion']
    if script.get('style') == 'comic':
        entry['style'] = 'comic'
    items = history() + [entry]
    history_path().write_text(json.dumps(items[-200:], ensure_ascii=False, indent=1), encoding='utf-8')


def saved_ideas():
    """Lessons suggested by comments and trends (reel/growth.py), newest last."""
    try:
        return json.loads(history_path().with_name('ideas.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return []


def pick_topic(path=ROOT / 'topics.txt'):
    """A fresh idea from comments and trends when there is one, else a random topic; never the last 25 used."""
    topics = [t.strip() for t in path.read_text(encoding='utf-8').splitlines() if t.strip() and not t.startswith('#')]
    recent = {h.get('topic', '').strip().lower() for h in history()[-25:]}
    fresh_ideas = [t for t in reversed(saved_ideas()) if t.strip().lower() not in recent]
    if fresh_ideas:
        return fresh_ideas[0]
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
    scenes, last_shot, voice_of = [], None, None
    for beat in (raw.get('scenes') or [])[:8]:
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
        caption = short(beat.get('caption'), LIMITS['caption']) or line[:LIMITS['caption']]
        speaker = pick(beat.get('speaker'), SPEAKERS, 'narrator')
        if speaker == 'other' and cast == 'none':
            speaker = 'narrator'
        if speaker == 'other' and voice_of is None:
            voice_of = cast
        elif speaker == 'other' and cast != voice_of:
            speaker = 'narrator'  # one other voice per Reel (the speech model has two speakers)
        keyword = str(beat.get('keyword') or '').strip()
        scenes.append({
            'line': line, 'caption': caption,
            'speaker': speaker, 'keyword': keyword if keyword and keyword in caption else '',
            'sticker': pick(beat.get('sticker'), STICKERS, 'none'),
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
    if not DEVANAGARI.search(script.get('title_b', '')) or script.get('title_b') == script['title']:
        script['title_b'] = ''
    script['hook_action'] = pick(raw.get('hook_action'), ACTIONS, max(scenes, key=lambda s: s['mood'] == 'tense')['action'])
    if script['hook_action'] in TWO_PERSON:
        script['hook_with'] = next((s['with'] for s in scenes if s['action'] == script['hook_action']), 'friend')
    script['music'] = pick(raw.get('music'), MUSIC, 'warm')
    script['other_voice'] = voice_of or next((b['with'] for b in scenes if b['with'] != 'none'), 'friend')
    script['part'] = str(raw.get('part') or '')
    script['instagram_caption'] = str(raw.get('instagram_caption') or '').strip()[:1500]
    tags = [re.sub(r'[^\wऀ-ॿ]', '', str(t)) for t in raw.get('hashtags') or []]
    script['hashtags'] = list(dict.fromkeys(f'#{t}' for t in tags if t))[:8]
    return script


FIRST_PERSON = re.compile(r'(?<![ऀ-ॿ])(मैं|मैंने|मेरा|मेरी|मेरे|मुझे|मुझसे|मुझको|हम|हमने|हमारा|हमारी)(?![ऀ-ॿ])')


def first_person(script):
    """True when the hook and at least half of the narrated beats are told as "I" (मैं, मेरा...)."""
    told = [script['hook'], *(s['line'] for s in script['scenes'] if s.get('speaker', 'narrator') == 'narrator')]
    hits = sum(bool(FIRST_PERSON.search(line)) for line in told)
    return hits >= max(1, (len(told) + 1) // 2)


def hero():
    """The storyteller follows the narrator's voice: 'girl' for NARRATOR=female, else 'boy'."""
    return 'girl' if os.getenv('NARRATOR', '').strip().lower() == 'female' else 'boy'


HEROES = {'boy': ('a young man', 'masculine (मैं सोचता था, मैंने किया, मैं गया)'),
          'girl': ('a young woman', 'feminine (मैं सोचती थी, मैंने किया, मैं गई)')}


def love_turn():
    """Whether a Reel with no chosen topic should be a love story (LOVE_SHARE, default 0.4 of them)."""
    try:
        share = float(os.getenv('LOVE_SHARE', '') or 0.4)
    except ValueError:
        share = 0.4
    return random.random() < share


def spoken_lines(script):
    """What is said, in order: hook, every beat, the lesson, then the question."""
    return [script['hook'], *(s['line'] for s in script['scenes']), script['lesson'], script['ask']]


def spoken_turns(script):
    """(speaker, line) for every spoken line: the hook, lesson and question are always the narrator."""
    return [('narrator', script['hook']), *((s.get('speaker', 'narrator'), s['line']) for s in script['scenes']),
            ('narrator', script['lesson']), ('narrator', script['ask'])]


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


def choose_topic(topic='', theme='', source='', part=''):
    """(topic, occasion) for a new Reel: the given lesson, else the chosen theme or source, else the calendar's due
    occasion, else a fresh idea or random topic."""
    from . import occasions
    topic = (topic or '').strip()
    if topic or part == '2/2':
        return topic, None
    if theme in THEMES:
        return f'Choose one fresh, specific, relatable life lesson about {THEMES[theme][1]}', None
    if source == 'occasion':
        soon = occasions.upcoming_any(history=history())
        if soon:
            return soon['lesson'], soon
    if source == 'ideas':
        recent = {h.get('topic', '').strip().lower() for h in history()[-25:]}
        fresh = [t for t in reversed(saved_ideas()) if t.strip().lower() not in recent]
        if fresh:
            return fresh[0], None
    love = f'Choose one fresh, specific, relatable life lesson about {THEMES["love"][1]}'
    if source == 'random':
        return (love if love_turn() else pick_topic()), None
    occasion = occasions.due(history=history())
    if occasion:
        return occasion['lesson'], occasion
    return (love if love_turn() else pick_topic()), None


def write(topic=None, part='', previous=None, theme='', source=''):
    from . import growth, occasions
    topic, occasion = choose_topic(topic, theme, source, part)
    recent = [h.get('title') for h in history()[-15:] if h.get('title')]
    who = hero()
    person, forms = HEROES[who]
    prompt = WRITER.format(
        hero=person, forms=forms, topic=topic, beats=random.choice((6, 7)), hook_rules=HOOK_RULES, two=', '.join(TWO_PERSON),
        actions=catalog(ACTIONS), cast=catalog(CAST), props=catalog(PROPS), places=catalog(PLACES), shots=catalog(SHOTS),
        series=series_note(part, previous), speakers=catalog(SPEAKERS), stickers=', '.join(STICKERS),
        avoid='\n'.join(x for x in (f'- Do not repeat these recent titles or their angle: {", ".join(recent)}' if recent else '',
                                    growth.lessons_learned(), occasions.note(occasion) if occasion else '') if x))
    last = None
    for attempt in range(2):
        draft, model = gemini.json_call(prompt, SCHEMA)
        try:
            drafted = clean(draft)
        except ValueError as exc:
            last = exc
            print(f'Draft rejected ({exc}); asking again')
            continue
        if not first_person(drafted) and attempt == 0:
            print('Draft is not told in first person; asking again')
            continue
        try:
            directed, _ = gemini.json_call(DIRECTOR.format(
                draft=json.dumps(draft, ensure_ascii=False, indent=1), hook_rules=HOOK_RULES, actions=catalog(ACTIONS),
                two=', '.join(TWO_PERSON), shot_names=', '.join(SHOTS), place_names=', '.join(PLACES),
                hero=person, forms=forms), SCHEMA, temperature=0.6)
            script = clean(directed)
            script['directed'] = True
            if first_person(drafted) and not first_person(script):
                print('The director slipped out of first person; using the draft')
                script, script['directed'] = drafted, False
        except (ValueError, gemini.GeminiError) as exc:
            print(f'Director pass skipped ({exc}); using the draft')
            script = drafted
            script['directed'] = False
        script['hero'] = who
        script['model'] = model
        script['topic'] = script['topic'] or topic
        script['part'] = part
        if occasion:
            script['occasion'], script['occasion_name'] = occasion['tag'], occasion['name']
        return script
    raise ValueError(f'Gemini could not write a usable script: {last}')
