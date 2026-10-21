"""Comic Reels: a cheeky cartoon kid with a big head and huge eyes rants about one relatable desi situation,
deadpan, straight to the viewer, and the last line is the punchline (the bot's "😂 Comic" style).

The look and rhythm follow viral Hindi cartoon-meme Reels: one room, one character who barely moves but whose
eyes and eyebrows do the acting, a short title strip with two emoji at the top, 15-25 seconds of talking, and a
twist at the end. The kid is our own character (not any TV cartoon), so nothing is copied.

Two Gemini passes, both answering in SCHEMA: the comedy writer drafts the rant, then a comedy editor punches it
up (a sharper setup, a punchline whose last words carry the twist, shorter lines). `clean()` turns the answer
into the same script shape as a story Reel, so voice, timing, posting and the weekly report work unchanged:
  hook = the setup line, scenes = the rant lines, lesson = the punchline, ask = the question for the comments.
"""
import json
import random
import re

from . import gemini
from . import script as stories

# Expressions of the kid (remotion/src/comic/Kid.tsx draws each one)
FACES = {
    'deadpan': 'half-closed eyes, flat mouth, bored and done with life (the default for a dry rant)',
    'side_eye': 'eyes slide to the side with heavy lids, unimpressed, judging',
    'smug': 'one eyebrow up, a smirk, proud of something silly',
    'shock': 'eyes wide with tiny pupils, mouth an O, eyebrows up',
    'eye_roll': 'eyes roll up, "here we go again"',
    'angry': 'eyebrows down, teeth showing, fed up',
    'cry': 'tears streaming, wobbly mouth (fake or real despair, for comedy)',
    'happy': 'a big smile, innocent and pleased',
    'nervous': 'wavy mouth, a sweat drop, caught out',
    'sad': 'droopy eyebrows, small frown',
}
# What the hands do (also in Kid.tsx)
GESTURES = {
    'type': 'types on the keyboard or writes, not looking up',
    'talk': 'one hand moves while talking, explaining',
    'shrug': 'both hands up, "what can I do"',
    'facepalm': 'hand over the face',
    'point_self': 'points at own chest ("me", "I did this")',
    'point_viewer': 'points straight at the viewer ("you too")',
    'arms_crossed': 'arms folded, stubborn',
    'slam': 'slams both fists on the table',
    'phone': 'holds a phone and looks at it',
    'chai': 'sips tea from a small cup',
    'think': 'hand on the chin',
    'scratch_head': 'scratches the head, confused',
}
# Where the kid looks (the pupils): at the viewer, at the person off screen, at the screen or book, up, down
LOOKS = ('viewer', 'side', 'screen', 'up', 'down')
# One room for the whole Reel; the kid sits behind its table (remotion/src/comic/rooms.tsx)
ROOMS = {
    'bedroom': 'his bedroom: bed, window with curtains, a poster; a computer desk in front',
    'classroom': 'a classroom: blackboard behind, a school bench with a notebook in front',
    'kitchen': 'the home kitchen: shelves and a stove behind, a dining table with a plate and a glass',
    'office': 'an office: window blinds, a plant and a wall clock behind, a desk with a laptop',
    'living_room': 'the living room: a sofa, a TV and a wall clock behind, a small table in front',
}
# Who may speak from off screen (one line at most); the kid looks at them
OTHERS = {k: v for k, v in stories.CAST.items() if k in ('none', 'mother', 'father', 'teacher', 'boss', 'friend')}
EMOJI = {'sob': 'loudly crying face', 'joy': 'laughing with tears', 'skull': 'skull ("I am dead")',
         'facepalm': 'facepalm face', 'clown': 'clown face', 'none': 'no emoji'}
LIMITS = {'title': 32, 'title_b': 32, 'hook': 110, 'line': 120, 'lesson': 120, 'ask': 90, 'name': 16}

LINE = {
    'type': 'object',
    'properties': {
        'line': {'type': 'string', 'description': 'One spoken Hindi line in Devanagari, at most 14 words'},
        'face': {'type': 'string', 'enum': list(FACES)},
        'gesture': {'type': 'string', 'enum': list(GESTURES)},
        'look': {'type': 'string', 'enum': list(LOOKS)},
        'speaker': {'type': 'string', 'enum': ['hero', 'other'], 'description': 'hero (the kid) on almost every line'},
    },
    'required': ['line', 'face', 'gesture', 'look', 'speaker'],
}
SCHEMA = {
    'type': 'object',
    'properties': {
        'topic': {'type': 'string', 'description': 'The situation in English, a few words'},
        'name': {'type': 'string', 'description': "The kid's Hindi nickname in Devanagari, e.g. गोलू"},
        'title': {'type': 'string', 'description': 'The title strip: 1-3 words naming the situation, Hinglish in Roman '
                                                   'letters is fine (e.g. "Computer Course", "Monday Office", "बोर्ड एग्ज़ाम")'},
        'title_b': {'type': 'string', 'description': 'A second title strip with a different angle (for an A/B test)'},
        'emoji': {'type': 'string', 'enum': list(EMOJI), 'description': 'Shown twice after the title'},
        'place': {'type': 'string', 'enum': list(ROOMS)},
        'other': {'type': 'string', 'enum': list(OTHERS), 'description': 'Who speaks from off screen, or none'},
        'hooks': {'type': 'array', 'items': {'type': 'string'}, 'minItems': 1, 'maxItems': 3,
                  'description': 'Three different Hindi setup lines (the first spoken line), at most 14 words each'},
        'hook': {'type': 'object', 'properties': LINE['properties'], 'required': LINE['required'],
                 'description': 'The chosen setup line with how the kid looks while saying it'},
        'lines': {'type': 'array', 'minItems': 2, 'maxItems': 5, 'items': LINE,
                  'description': 'The rant, building up to the punchline'},
        'punchline': {'type': 'object', 'properties': LINE['properties'], 'required': LINE['required'],
                      'description': 'The last line: the twist'},
        'ask': {'type': 'string', 'description': 'A short Hindi question for the comments, in character, at most 10 words'},
        'instagram_caption': {'type': 'string', 'description': 'Hindi Instagram caption, 1-2 short funny lines'},
        'hashtags': {'type': 'array', 'items': {'type': 'string'}, 'maxItems': 8},
    },
    'required': ['topic', 'name', 'title', 'emoji', 'place', 'other', 'hooks', 'hook', 'lines', 'punchline', 'ask',
                 'instagram_caption', 'hashtags'],
}

COMEDY_RULES = """Comedy rules (this is what makes cartoon-meme Reels go viral in India):
  - ONE specific, painfully relatable situation from ordinary Indian life: a useless course, a relative asking
    about marks or salary, मम्मी's "बस पाँच मिनट", Monday at the office, an exam tomorrow, the WiFi, a wedding,
    a gym membership, online class, a group project. Real details make it funny: numbers, prices, years, names
    of everyday things ("पंद्रह हज़ार की नौकरी", "दो साल का कोर्स", "चार साल से घर पे").
  - The kid talks straight to the viewer like a tired, deadpan desi adult roasting their own life: cheeky,
    sarcastic, a bit dramatic, confidently wrong. The joke is never on other people's looks, caste, religion,
    region or gender; the kid is the butt of the joke.
  - Structure: setup (states the situation in one breath) -> 1-3 lines that escalate (rule of three: expectation,
    reality, worse reality) -> the punchline: a twist that makes the viewer laugh and replay. The twist sits in
    the LAST words of the punchline ("...बस गाना और फिलम चलाना सीखा।").
  - Short lines, spoken rhythm, no explaining the joke, no moral at the end, no "दोस्तों", no "आज मैं बताऊँगा".
  - The setup must hook in the first 2 seconds: start mid-complaint, with the number or the situation."""

WRITER = """You write comedy scripts for a Hindi Instagram/YouTube Reels channel. The star is {name_hint}: a cheeky
cartoon kid with a big round head, huge eyes and thick eyebrows, who sits at a table and rants to the viewer.

Situation for this Reel: {topic}

Write a 15-25 second rant: a setup line, {n} more lines, then the punchline; 40-55 spoken words in all (count
them), plus a question of at most 8 words.
{rules}
- FIRST PERSON: the kid ({hero}) talks about their own life (मैंने, मेरा, हम), with {forms} verb forms.
- Language: everyday spoken Hindi in Devanagari, the way people really talk at home; a light UP/Bihar flavour is
  welcome ("का बताएं", "हम", "बा", "ना") but every Hindi speaker must follow it. Common English words in
  Devanagari ("कोर्स", "जॉब", "सैलरी"). No Roman script, emoji or hashtags in the spoken lines.
- For every line pick how the kid acts it: face ({faces}), gesture ({gestures}) and look ({looks}). The comedy is
  in the eyes: deadpan and side_eye most of the time, a sudden shock or cry only where it is funny, and a
  different face or gesture on the punchline.
  Faces:
{face_list}
  Gestures:
{gesture_list}
- Optional: ONE line from someone off screen (`other`: {others}), e.g. मम्मी shouting from the kitchen; set that
  line's speaker to "other" and the kid's look to "side". Otherwise other is "none" and every speaker is "hero".
- place: the one room where the kid sits for the whole Reel:
{rooms}
- title: the strip at the top, 1-3 words that name the situation ("Computer Course"), plus an emoji: {emoji}.
- ask: one short question in character that viewers will answer in the comments ("तुमने कौन सा कोर्स किया था?").
- instagram_caption: 1-2 short funny Hindi lines; hashtags: up to 8, Hindi and English (comedy, relatable, desi).
- Keep it clean and kind: no vulgarity, no insults to groups, no real people or brands, no politics or religion,
  no medical, legal or money promises.
{avoid}"""

EDITOR = """You are the comedy editor of a Hindi cartoon-meme Reels channel. Make this rant funnier and tighter,
then return the full script in the same JSON shape.

Draft:
{draft}

{rules}
Do all of this:
1. Hook: pick the funniest of the setup options and sharpen it; it must make sense with zero context.
2. Punchline: rewrite it so the twist lands in the last 2-4 words and is a real surprise. If the draft explains
   the joke, cut the explanation.
3. Cut every word that does not earn its place; at most 14 words a line; it must sound natural spoken aloud.
4. Acting: the face, gesture and look of each line must fit it; never the same face three lines in a row; the
   punchline gets the most expressive face of the Reel.
5. Keep first person ({hero}, {forms} verb forms), Devanagari only in spoken lines, and at most one off-screen line.
6. Keep the title short (1-3 words) and give title_b a clearly different angle."""


def short(text, limit):
    return stories.short(text, limit)


def pick(value, allowed, default):
    return value if value in allowed else default


def clean_line(raw, other):
    raw = raw if isinstance(raw, dict) else {'line': raw}
    line = short(raw.get('line'), LIMITS['line'])
    if not stories.DEVANAGARI.search(line):
        return None
    speaker = 'other' if raw.get('speaker') == 'other' and other != 'none' else 'narrator'
    return {'line': line, 'caption': '', 'keyword': '', 'sticker': 'none',
            'face': pick(raw.get('face'), FACES, 'deadpan'), 'gesture': pick(raw.get('gesture'), GESTURES, 'talk'),
            'look': 'side' if speaker == 'other' else pick(raw.get('look'), LOOKS, 'viewer'),
            'speaker': speaker, 'with': other if speaker == 'other' else 'none'}


def clean(raw):
    """A comic script in the story-script shape (see the module docstring), or ValueError if it is unusable."""
    other = pick(raw.get('other'), OTHERS, 'none')
    script = {'style': 'comic', 'topic': short(raw.get('topic'), 80), 'name': short(raw.get('name'), LIMITS['name']),
              'title': short(raw.get('title'), LIMITS['title']), 'title_b': short(raw.get('title_b'), LIMITS['title_b']),
              'emoji': pick(raw.get('emoji'), EMOJI, 'sob'), 'place': pick(raw.get('place'), ROOMS, 'bedroom')}
    if not stories.DEVANAGARI.search(script['name']):
        script['name'] = ''
    hook = clean_line(raw.get('hook') or {}, 'none')
    if hook is None:
        first = next((h for h in raw.get('hooks') or [] if stories.DEVANAGARI.search(str(h))), '')
        hook = clean_line({'line': first, 'face': 'deadpan', 'gesture': 'type', 'look': 'viewer'}, 'none')
    punch = clean_line(raw.get('punchline') or {}, 'none')
    if hook is None or punch is None:
        raise ValueError('the setup or the punchline is not in Hindi')
    lines, spoken = [], 0
    for item in (raw.get('lines') or [])[:5]:
        line = clean_line(item, other)
        if line is None or (line['speaker'] == 'other' and spoken):
            continue  # one off-screen line per Reel
        spoken += line['speaker'] == 'other'
        lines.append(line)
    if not lines:
        raise ValueError('the rant has no usable Hindi lines between the setup and the punchline')
    if not script['title']:
        raise ValueError('the title strip is empty')
    if script['title_b'] == script['title']:
        script['title_b'] = ''
    script.update({
        'hook': hook['line'], 'hook_face': hook['face'], 'hook_gesture': hook['gesture'], 'hook_look': hook['look'],
        'scenes': [{**line, 'place': script['place']} for line in lines],
        'lesson': punch['line'], 'punch_face': punch['face'], 'punch_gesture': punch['gesture'], 'punch_look': punch['look'],
        'ask': short(raw.get('ask'), LIMITS['ask']), 'music': 'comic', 'other_voice': other if spoken else 'friend',
        'part': '', 'instagram_caption': str(raw.get('instagram_caption') or '').strip()[:1500],
    })
    if not stories.DEVANAGARI.search(script['ask']):
        script['ask'] = 'आपके साथ भी ऐसा हुआ है? कमेंट में बताओ।'
    tags = [re.sub(r'[^\wऀ-ॿ]', '', str(t)) for t in raw.get('hashtags') or []]
    script['hashtags'] = list(dict.fromkeys(f'#{t}' for t in tags if t))[:8]
    return script


def topic_for(topic='', theme='', source=''):
    """(situation, occasion): the given one, else a theme, festival or idea turned funny, else comic_topics.txt."""
    from . import occasions
    topic = (topic or '').strip()
    if topic:
        return topic, None
    if theme in stories.THEMES:
        return f'Choose one fresh, specific, relatable funny situation about {stories.THEMES[theme][1]}', None
    if source == 'occasion' or not source:
        soon = occasions.upcoming_any(history=stories.history()) if source == 'occasion' else occasions.due(history=stories.history())
        if soon:
            return f"A funny, relatable situation around {soon['name']} at home (cleaning, guests, sweets, relatives)", soon
    if source == 'ideas':
        recent = {h.get('topic', '').strip().lower() for h in stories.history()[-25:]}
        fresh = [t for t in reversed(stories.saved_ideas()) if t.strip().lower() not in recent]
        if fresh:
            return f'The funny side of: {fresh[0]}', None
    return stories.pick_topic(stories.ROOT / 'comic_topics.txt'), None


def write(topic=None, theme='', source=''):
    from . import growth, occasions
    topic, occasion = topic_for(topic, theme, source)
    recent = [h.get('title') for h in stories.history()[-15:] if h.get('title')]
    who = stories.hero()
    person, forms = stories.HEROES[who]
    person = person.replace('a young man', 'a cheeky boy').replace('a young woman', 'a cheeky girl')
    name_hint = 'a girl with a ponytail and a bow' if who == 'girl' else 'a boy with a spiky tuft of hair'
    prompt = WRITER.format(
        name_hint=name_hint, topic=topic, n=random.choice((2, 3)), rules=COMEDY_RULES, hero=person, forms=forms,
        faces=', '.join(FACES), gestures=', '.join(GESTURES), looks=', '.join(LOOKS), face_list=stories.catalog(FACES),
        gesture_list=stories.catalog(GESTURES), others=', '.join(k for k in OTHERS if k != 'none'),
        rooms=stories.catalog(ROOMS), emoji=', '.join(EMOJI),
        avoid='\n'.join(x for x in (f'- Do not repeat these recent titles or their angle: {", ".join(recent)}' if recent else '',
                                    growth.lessons_learned(), occasions.note(occasion) if occasion else '') if x))
    # no first-person check here: a rant often drops the "मैं" ("दो साल का कोर्स किया...") and is still the kid's own
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
            edited, _ = gemini.json_call(EDITOR.format(draft=json.dumps(draft, ensure_ascii=False, indent=1), rules=COMEDY_RULES,
                                                       hero=person, forms=forms), SCHEMA, temperature=0.7)
            script = clean(edited)
            script['directed'] = True
        except (ValueError, gemini.GeminiError) as exc:
            print(f'Comedy edit skipped ({exc}); using the draft')
            script, script['directed'] = drafted, False
        script.update(hero=who, model=model, part='')
        script['topic'] = script['topic'] or topic
        if occasion:
            script['occasion'], script['occasion_name'] = occasion['tag'], occasion['name']
        return script
    raise ValueError(f'Gemini could not write a usable comic script: {last}')
