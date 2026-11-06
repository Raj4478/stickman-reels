"""Comic Reels: a cheeky, mischievous cartoon kid with a big head and huge eyes, full of naughty-kid cartoon
energy, talks about one relatable desi situation straight to the viewer, back-talks मम्मी and lands a punchline
(the bot's "😂 Comic" style). 6-9 lines and a camera cut every couple of seconds keep it lively.

The look and rhythm follow viral Hindi cartoon-meme Reels: a character whose eyes and eyebrows do the acting, a
short title strip with two emoji at the top, 15-25 seconds of talking, and a twist at the end. The picture follows
the words: each line has a visual (VISUALS), so the Reel cuts from the kid to the teacher being quoted, मम्मी in the
kitchen, calendar pages flying, the salary slip or the computer screen, with the kid still talking in a corner
bubble. The kid is our own character (not any TV cartoon), so nothing is copied.

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
    'cheeky': 'a naughty grin, eyebrows wiggling, eyes half-shut with mischief (up to something, a sly comeback)',
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
    'dance': 'a silly victory dance: arms waving, head bobbing (a small win, showing off, celebrating nonsense)',
    'panic': 'both hands flapping in the air, "no no no!" (caught out, mock drama)',
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
    'gym': 'a gym: dumbbell racks and a mirror behind, a bench with a dumbbell and a shaker in front',
    'street': 'a street corner: shop fronts behind, a chai stall counter with a kettle and glasses in front',
}
# Who may speak from off screen (one line at most); the kid looks at them
OTHERS = {k: v for k, v in stories.CAST.items() if k in ('none', 'mother', 'father', 'teacher', 'boss', 'friend')}
# What the picture shows on a line (remotion/src/comic/ComicReel.tsx and cutaways.tsx draw each one)
VISUALS = {
    'kid': 'the kid at the table, talking to the viewer (the default; always for the setup)',
    'person': 'the person in `who` on screen in their own room: they say the line themselves (speaker other), or it '
              'is a flashback of what they once said ("सर बोले थे...")',
    'dream': 'the kid daydreaming, with visual_text in a thought bubble (hopes, plans, "what I thought would happen")',
    'screen': 'close-up of the computer screen showing `screen` (music, video, jobs, search, error) with visual_text',
    'calendar': 'calendar pages flying off, stopping on visual_text (years or months passing, "4 साल")',
    'clock': 'a clock spinning fast, then visual_text ("घंटों बाद...", time wasted)',
    'money': 'a salary slip with the amount in visual_text, coins falling (salary, fees, prices)',
    'certificate': 'a framed certificate with visual_text as the course name, a spider web growing on it (useless degrees)',
    'chat': 'a phone chat: typing dots, then visual_text as the reply, then "Seen" (texts, replies, being ignored)',
    'result': 'an answer sheet with visual_text as the marks circled in red ("2/100")',
}
SCREENS = ('music', 'video', 'jobs', 'search', 'error')
EMOJI = {'sob': 'loudly crying face', 'joy': 'laughing with tears', 'skull': 'skull ("I am dead")',
         'facepalm': 'facepalm face', 'clown': 'clown face', 'none': 'no emoji'}
LIMITS = {'title': 32, 'title_b': 32, 'hook': 110, 'line': 120, 'lesson': 120, 'ask': 90, 'name': 16, 'visual_text': 24,
          'cover_text': 20}
PEOPLE = tuple(k for k in OTHERS if k != 'none')  # who can be on screen

LINE = {
    'type': 'object',
    'properties': {
        'line': {'type': 'string', 'description': 'One spoken Hindi line in Devanagari, at most 12 words'},
        'face': {'type': 'string', 'enum': list(FACES)},
        'gesture': {'type': 'string', 'enum': list(GESTURES)},
        'look': {'type': 'string', 'enum': list(LOOKS)},
        'speaker': {'type': 'string', 'enum': ['hero', 'other'], 'description': 'hero (the kid) on almost every line'},
        'visual': {'type': 'string', 'enum': list(VISUALS), 'description': 'What the picture shows on this line'},
        'visual_text': {'type': 'string', 'description': 'At most 3 words or a number drawn in the picture (₹15,000, 4 साल, '
                                                         'गाना.mp3), or "" for kid and person'},
        'screen': {'type': 'string', 'enum': list(SCREENS), 'description': 'What the computer shows (only for visual screen)'},
        'who': {'type': 'string', 'enum': list(PEOPLE), 'description': 'Who is on screen (only for visual person)'},
        'place': {'type': 'string', 'enum': list(ROOMS), 'description': 'Where the kid is on this line (kid and dream)'},
    },
    'required': ['line', 'face', 'gesture', 'look', 'speaker', 'visual', 'visual_text', 'screen', 'who', 'place'],
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
        'cover_text': {'type': 'string', 'description': 'The cover image text: 1-3 words that tease the twist without '
                                                        'giving it away ("95 नंबर?!"), different from the title'},
        'place': {'type': 'string', 'enum': list(ROOMS), 'description': 'Where the kid mostly is (each line may move)'},
        'other': {'type': 'string', 'enum': list(OTHERS), 'description': 'Who speaks from off screen, or none'},
        'hooks': {'type': 'array', 'items': {'type': 'string'}, 'minItems': 1, 'maxItems': 3,
                  'description': 'Three different Hindi setup lines (the first spoken line), at most 14 words each'},
        'hook': {'type': 'object', 'properties': LINE['properties'], 'required': LINE['required'],
                 'description': 'The chosen setup line with how the kid looks while saying it'},
        'lines': {'type': 'array', 'minItems': 4, 'maxItems': 8, 'items': LINE,
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
  - ENERGY: lively and playful like a classic naughty-kid cartoon (our own kid, never a TV character): cheeky,
    mischievous, quick-witted, a little shameless, with innocent-but-twisted kid logic. Reactions are big and
    switch fast (smug -> shock -> fake crying -> a silly dance). Mix that with a few dry deadpan lines; the
    contrast is the joke.
  - BANTER: the best bits are back-and-forth with the person in `other` (usually मम्मी): they scold or ask, the
    kid answers with a cheeky comeback that twists their words. Up to 3 of their lines, never two in a row.
  - ONE specific, painfully relatable situation from ordinary Indian life: a useless course, a relative asking
    about marks or salary, मम्मी's "बस पाँच मिनट", Monday at the office, an exam tomorrow, the WiFi, a wedding,
    a gym membership, online class, a group project. Real details make it funny: numbers, prices, years, names
    of everyday things ("पंद्रह हज़ार की नौकरी", "दो साल का कोर्स", "चार साल से घर पे").
  - The kid talks straight to the viewer, roasting their own life: cheeky, sarcastic, dramatic, confidently
    wrong. The joke is never on other people's looks, caste, religion,
    region or gender; the kid is the butt of the joke.
  - Structure: setup (states the situation in one breath) -> 5-7 short lines that escalate (expectation,
    reality, worse reality, a comeback, a mini-twist) -> the punchline: a twist that makes the viewer laugh and replay. The twist sits in
    the LAST words of the punchline ("...बस गाना और फिलम चलाना सीखा।").
  - Short lines, spoken rhythm, no explaining the joke, no moral at the end, no "दोस्तों", no "आज मैं बताऊँगा".
  - The setup must hook in the first 2 seconds: start mid-complaint, with the number or the situation."""

WRITER = """You write comedy scripts for a Hindi Instagram/YouTube Reels channel. The star is {name_hint}: a cheeky
cartoon kid with a big round head, huge eyes and thick eyebrows, who sits at a table and rants to the viewer.

Situation for this Reel: {topic}

Write a 30-40 second scene: a setup line, {n} more lines, then the punchline; 75-100 spoken words in all
(count them), at most 12 words a line, plus a question of at most 8 words. Many short lines, each with its own
picture and reaction, keep the Reel moving.
{rules}
- FIRST PERSON: the kid ({hero}) talks about their own life (मैंने, मेरा, हम), with {forms} verb forms.
- Language: everyday spoken Hindi in Devanagari, the way people really talk at home; a light UP/Bihar flavour is
  welcome ("का बताएं", "हम", "बा", "ना") but every Hindi speaker must follow it. Common English words in
  Devanagari ("कोर्स", "जॉब", "सैलरी"). No Roman script, emoji or hashtags in the spoken lines.
- For every line pick how the kid acts it: face ({faces}), gesture ({gestures}) and look ({looks}). The comedy is
  in the eyes and the energy: a new face on almost every line, big switches (cheeky -> shock -> cry -> dance),
  deadpan or side_eye for the dry lines, and the most expressive face and gesture on the punchline.
  Faces:
{face_list}
  Gestures:
{gesture_list}
- Banter: up to 3 lines said by someone else (`other`: {others}), e.g. मम्मी shouting from the kitchen and the
  kid's cheeky reply; set those lines' speaker to "other" (never two in a row). Otherwise other is "none" and
  every speaker is "hero".
- MAKE THE PICTURE FOLLOW THE WORDS: for every line pick a `visual`, so the video shows what is being said:
{visuals}
  The setup's picture follows its words too: it is the first frame, so show the situation at once (the kid
  in the gym for a gym joke, a person, or a cutaway), never a default computer. At least half the lines show a
  character (kid, person or dream: the faces are the stars), and use 1-3 cutaways where a line names something
  you can show: a person quoted or speaking (person + who), a salary
  (money), years passing (calendar), the computer (screen), a degree (certificate), a reply (chat), marks
  (result), a hope (dream). The punchline may reveal its twist as a cutaway (e.g. the screen playing a song).
  visual_text is the 1-3 words or number drawn in that picture, taken from the line. The face is for whoever is
  on screen (the kid keeps reacting in a corner bubble during cutaways).
- place: where the kid is. Set the Reel's place to where the story mostly happens, and each line's place to
  where that line happens (the kid may move: bedroom, then gym). Only the bedroom, office and screen visuals
  show a computer, so pick the room that fits the words:
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
3. Keep it lively: 5-7 lines between the setup and the punchline, at most 12 words each, a cheeky comeback
   in the banter, and cut every word that does not earn its place; it must sound natural spoken aloud.
4. Acting: the face, gesture and look of each line must fit it; never the same face three lines in a row; the
   punchline gets the most expressive face of the Reel.
4b. Pictures: every line's visual must show what it says (a quoted person -> person, a salary -> money, years ->
   calendar...). The setup shows the situation at once (never a default computer), at least half the lines
   show a character (kid, person or dream), each kid line's place is where it happens, and visual_text is short
   and taken from the line. Visuals: {visual_names}.
5. Keep first person ({hero}, {forms} verb forms), Devanagari only in spoken lines, and at most three
   off-screen lines (never two in a row).
6. Keep the title short (1-3 words) and give title_b a clearly different angle."""


def short(text, limit):
    return stories.short(text, limit)


def pick(value, allowed, default):
    return value if value in allowed else default


def clean_line(raw, other, place='bedroom'):
    raw = raw if isinstance(raw, dict) else {'line': raw}
    line = short(raw.get('line'), LIMITS['line'])
    if not stories.DEVANAGARI.search(line):
        return None
    speaker = 'other' if raw.get('speaker') == 'other' and other != 'none' else 'narrator'
    visual = pick(raw.get('visual'), VISUALS, 'kid')
    who = other if speaker == 'other' else pick(raw.get('who'), PEOPLE, 'teacher')
    if speaker == 'other' and visual == 'kid':
        visual = 'person'  # show who is talking, in their own room
    text = short(raw.get('visual_text'), LIMITS['visual_text'])
    if visual in CUTAWAYS + ('dream',) and not text:
        visual = 'kid'  # a cutaway needs something to show
    return {'line': line, 'caption': '', 'keyword': '', 'sticker': 'none',
            'face': pick(raw.get('face'), FACES, 'deadpan'), 'gesture': pick(raw.get('gesture'), GESTURES, 'talk'),
            'look': pick(raw.get('look'), LOOKS, 'viewer'),
            'speaker': speaker, 'with': other if speaker == 'other' else 'none',
            'visual': visual, 'visual_text': text if visual not in ('kid', 'person') else '',
            'screen': pick(raw.get('screen'), SCREENS, 'music'), 'who': who if visual == 'person' else 'none',
            'place': pick(raw.get('place'), ROOMS, place)}


CUTAWAYS = ('screen', 'calendar', 'clock', 'money', 'certificate', 'chat', 'result')
OTHER_LINES = 3  # how many lines the other person may say


def keep_the_kid(lines):
    """At least half of the lines show a character (the kid, a person or the kid's daydream): the last extra
    cutaways go back to the kid."""
    for line in reversed(lines):
        if sum(x['visual'] not in CUTAWAYS for x in lines) * 2 >= len(lines):
            break
        if line['visual'] in CUTAWAYS:
            line['visual'], line['visual_text'], line['who'] = 'kid', '', 'none'
    return lines


# How a line is acted and shown (the setup and punchline keep these as hook_<key> and punch_<key>)
ACTED = ('face', 'gesture', 'look', 'visual', 'visual_text', 'screen', 'who', 'place')


def clean(raw):
    """A comic script in the story-script shape (see the module docstring), or ValueError if it is unusable."""
    other = pick(raw.get('other'), OTHERS, 'none')
    script = {'style': 'comic', 'topic': short(raw.get('topic'), 80), 'name': short(raw.get('name'), LIMITS['name']),
              'title': short(raw.get('title'), LIMITS['title']), 'title_b': short(raw.get('title_b'), LIMITS['title_b']),
              'emoji': pick(raw.get('emoji'), EMOJI, 'sob'), 'place': pick(raw.get('place'), ROOMS, 'bedroom')}
    if not stories.DEVANAGARI.search(script['name']):
        script['name'] = ''
    place = script['place']
    hook = clean_line(raw.get('hook') or {}, 'none', place)
    if hook is None:
        first = next((h for h in raw.get('hooks') or [] if stories.DEVANAGARI.search(str(h))), '')
        hook = clean_line({'line': first, 'face': 'deadpan', 'gesture': 'talk', 'look': 'viewer'}, 'none', place)
    punch = clean_line(raw.get('punchline') or {}, 'none', place)
    if hook is None or punch is None:
        raise ValueError('the setup or the punchline is not in Hindi')
    lines, spoken = [], 0
    for item in (raw.get('lines') or [])[:8]:
        line = clean_line(item, other, place)
        if line is None:
            continue
        if line['speaker'] == 'other' and (spoken >= OTHER_LINES or (lines and lines[-1]['speaker'] == 'other')):
            continue  # banter: a few off-screen lines, each answered by the kid
        spoken += line['speaker'] == 'other'
        lines.append(line)
    if not lines:
        raise ValueError('the rant has no usable Hindi lines between the setup and the punchline')
    keep_the_kid([hook, *lines, punch])
    if not script['title']:
        raise ValueError('the title strip is empty')
    if script['title_b'] == script['title']:
        script['title_b'] = ''
    script.update({
        'hook': hook['line'], **{f'hook_{k}': hook[k] for k in ACTED},
        'scenes': lines,
        'lesson': punch['line'], **{f'punch_{k}': punch[k] for k in ACTED},
        'cover_text': short(raw.get('cover_text'), LIMITS['cover_text']),
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
        name_hint=name_hint, topic=topic, n=random.choice((5, 6)), rules=COMEDY_RULES, hero=person, forms=forms,
        faces=', '.join(FACES), gestures=', '.join(GESTURES), looks=', '.join(LOOKS), face_list=stories.catalog(FACES),
        gesture_list=stories.catalog(GESTURES), others=', '.join(k for k in OTHERS if k != 'none'),
        rooms=stories.catalog(ROOMS), emoji=', '.join(EMOJI), visuals=stories.catalog(VISUALS),
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
                                                       hero=person, forms=forms, visual_names=', '.join(VISUALS)),
                                        SCHEMA, temperature=0.7)
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
