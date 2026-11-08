"""What makes a Reel travel on Instagram, shared by the writers, the captions and the end card.

Instagram ranks Reels on watch time, likes and sends (shares) per reach. So:
- Send-worthy endings: every Kahani and comic script names who the viewer would send it to (`send_target`: maa,
  papa, bhai, dost...) and a short relational `end_line` in Roman Hinglish ("Ye video apni Maa ko bhejo"). It is
  drawn on screen in the last seconds and opens the caption. Never "comment X" engagement bait: Instagram demotes it.
- Keyword captions: the caption's first line is the hook plus a search phrase in Roman Hinglish and Hindi
  ("Maa ki kahani | emotional Hindi story | माँ की कहानी"), because Instagram search reads captions now.
"""
import re

# id -> (Roman, Hindi, feminine: "apni" instead of "apne")
SEND_TARGETS = {
    'maa': ('Maa', 'माँ', True),
    'papa': ('Papa', 'पापा', False),
    'bhai': ('Bhai', 'भाई', False),
    'behen': ('Behen', 'बहन', True),
    'dost': ('dost', 'दोस्त', False),
    'best_friend': ('best friend', 'बेस्ट फ्रेंड', False),
    'dadi_nani': ('Dadi-Nani', 'दादी-नानी', True),
    'partner': ('partner', 'जीवनसाथी', False),
    'bachche': ('bachchon', 'बच्चों', False),
    'office_dost': ('office wale dost', 'ऑफिस वाले दोस्त', False),
    'teacher': ('teacher', 'टीचर', False),
}
GENRE = {'storybook': 'emotional Hindi story', 'comic': 'Hindi comedy', 'story': 'Hindi life lesson'}
END_LIMIT = 44  # characters: one short line on screen
SEND_SECONDS = 2.8  # the end line is on screen for the last seconds (SEND_SECONDS in remotion/src/StickReel.tsx)
GRID_34 = (240, 1680)  # the cover rows the profile grid's 3:4 crop shows (GRID in remotion/src/SafeZones.tsx)
# engagement bait Instagram demotes ("comment karo", "type YES", "like karo", "follow karo")
BAIT = re.compile(r'\b(comment|comments|type|likho|like|follow|subscribe|tag)\b', re.I)

SEND_RULES = """- send_target: who would a viewer SEND this Reel to after watching? Pick the one person it is really about
  ({targets}). The story should make the viewer think of that person (a mother's sacrifice -> maa).
- end_line: a short warm Roman Hinglish line (at most 7 words) shown on screen in the last seconds, asking the viewer
  to send it to that person, e.g. "Ye video apni Maa ko bhejo", "Apne us dost ko bhejo jo aisa hi hai". Never ask
  for comments, likes, follows or to type anything.
- keyword_roman / keyword_hindi: the 2-4 word search phrase someone would type to find this Reel, in Roman Hinglish
  and the same in Devanagari (e.g. "Maa ki kahani" / "माँ की कहानी", "Exam wali comedy" / "एग्ज़ाम वाली कॉमेडी")."""


def rules():
    return SEND_RULES.format(targets=', '.join(SEND_TARGETS))


def default_end_line(target):
    roman, _, feminine = SEND_TARGETS.get(target, SEND_TARGETS['dost'])
    return f"Ye video {'apni' if feminine else 'apne'} {roman} ko bhejo"


def roman(text, limit):
    text = re.sub(r'[^A-Za-z0-9 ,.!?\'-]', '', str(text or ''))
    return re.sub(r'\s+', ' ', text).strip()[:limit].strip()


def clean_send(raw, fallback='dost'):
    """(send_target, end_line) from a writer's answer: a known target and a short line that is not bait."""
    target = str(raw.get('send_target') or '').strip().lower()
    target = target if target in SEND_TARGETS else fallback
    line = roman(raw.get('end_line'), 80)
    if not line or len(line) > END_LIMIT or BAIT.search(line) or 'bhej' not in line.lower() and 'share' not in line.lower():
        line = default_end_line(target)
    return target, line


def clean_keyword(raw, target, kind='kahani'):
    """(Roman, Hindi) search phrase; falls back to "<person> ki kahani" (or "<person> wali comedy")."""
    kw_roman = roman(raw.get('keyword_roman'), 40)
    kw_hindi = re.sub(r'\s+', ' ', re.sub(r'[^ऀ-ॿ \-]', '', str(raw.get('keyword_hindi') or ''))).strip()[:40]
    if not kw_roman or not kw_hindi:
        r, h, _ = SEND_TARGETS.get(target, SEND_TARGETS['dost'])
        r = r[0].upper() + r[1:]
        kw_roman, kw_hindi = ((f'{r} wali comedy', f'{h} वाली कॉमेडी') if kind == 'comedy' else (f'{r} ki kahani', f'{h} की कहानी'))
    return kw_roman, kw_hindi


def part_label(story):
    return f" (Part {story['part']})" if story.get('part') else ''


def first_line(story):
    """The caption's first line: the hook title, then the search phrase in Roman Hinglish, English and Hindi."""
    style = story.get('style') or 'story'
    words = [story['title'] + part_label(story)]
    if story.get('keyword_roman'):
        words.append(story['keyword_roman'])
    words.append(GENRE.get(style, GENRE['story']))
    if story.get('keyword_hindi'):
        words.append(story['keyword_hindi'])
    return ' | '.join(dict.fromkeys(w for w in words if w))


def send_line(story):
    """The caption's send line ("👉 Ye video apni Maa ko bhejo"), or '' for a script without one."""
    return f"👉 {story['end_line']}" if story.get('end_line') else ''
