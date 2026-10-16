"""Growth: learn from the numbers, post at the best time, and find the next lessons.

- Best time: the weekly report records each post's reach by time slot (IST); `best_slot()` picks the slot
  whose posts did best (at least 2 posts there), else 19:00. With POST_AT_PEAK=true, posting waits for it.
- Learning: the report stores a score for each Reel in the topic history; the writer is told which recent
  Reels did best and worst, so it leans toward what works.
- Ideas: Gemini turns viewers' comments and what India is searching for into 5 new lessons, sent to
  Telegram with a "Make" button for each.
- Instagram token: `refresh_token()` renews the 60-day token; the monthly workflow saves it back.
"""
import datetime as dt
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from . import gemini, publish, script

IST = dt.timezone(dt.timedelta(minutes=330))
SLOTS = (8, 13, 19, 21)  # posting slots, hour IST; the queue workflow runs at each
DEFAULT_SLOT = 19


def slot_of(when):
    """The posting slot (hour IST) closest to a time."""
    hour = when.astimezone(IST).hour + when.astimezone(IST).minute / 60
    return min(SLOTS, key=lambda s: abs(s - hour))


def best_slot(history=None):
    """The slot whose Reels reached the most people on average (needs 2+ posts there), else 19:00."""
    scores = {}
    for item in history if history is not None else script.history():
        if item.get('slot') in SLOTS and item.get('score') is not None:
            scores.setdefault(item['slot'], []).append(item['score'])
    ranked = sorted(((sum(v) / len(v), s) for s, v in scores.items() if len(v) >= 2), reverse=True)
    return ranked[0][1] if ranked else DEFAULT_SLOT


def next_time(slot, now=None):
    """The next time the clock shows `slot`:00 IST (today or tomorrow), in UTC."""
    now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(IST)
    at = now.replace(hour=slot, minute=0, second=0, microsecond=0)
    if at <= now + dt.timedelta(minutes=10):
        at += dt.timedelta(days=1)
    return at.astimezone(dt.timezone.utc)


def post_now(now=None, slot=None):
    """True when posting at once is fine: POST_AT_PEAK is off, or the best slot is less than 45 minutes away."""
    if os.getenv('POST_AT_PEAK', '').strip().lower() != 'true':
        return True
    wait = next_time(slot or best_slot(), now) - (now or dt.datetime.now(dt.timezone.utc))
    return wait <= dt.timedelta(minutes=45)


# --- learning from the numbers --------------------------------------------------------------

def record_scores(items):
    """Store each Reel's score (and the slot it went out at) in the topic history, matched by title."""
    history = script.history()
    by_title = {h.get('title', ''): h for h in history if h.get('title')}
    for item in items:
        title = (item.get('title') or '').split(' (भाग')[0].split(' | ')[0].strip()
        entry = by_title.get(title)
        if entry is None:
            continue
        entry['score'] = max(entry.get('score') or 0, int(item.get('score', 0)))
        if item.get('posted_at'):
            entry['slot'] = slot_of(item['posted_at'])
    script.history_path().write_text(json.dumps(history[-200:], ensure_ascii=False, indent=1), encoding='utf-8')
    return history


def lessons_learned(history=None, n=3):
    """Prompt lines naming the recent Reels that did best and worst (empty until there are scores)."""
    scored = [h for h in (history if history is not None else script.history())[-40:] if h.get('score') is not None]
    if len(scored) < 4:
        return ''
    scored.sort(key=lambda h: -h['score'])
    best = ', '.join(f"\"{h['title']}\" ({h.get('topic', '')})" for h in scored[:n])
    worst = ', '.join(f"\"{h['title']}\"" for h in scored[-n:])
    return (f'- Our audience loved these recent Reels: {best}. Lean toward what made them work (the kind of lesson, '
            f'the hook, the emotion), without copying them. These did worst: {worst}; avoid their angle.')


# --- ideas from comments and trends ---------------------------------------------------------

IDEAS_SCHEMA = {
    'type': 'object',
    'properties': {
        'ideas': {'type': 'array', 'minItems': 1, 'maxItems': 5, 'items': {
            'type': 'object',
            'properties': {
                'title': {'type': 'string', 'description': 'Hindi working title, at most 6 words'},
                'topic': {'type': 'string', 'description': 'The life lesson in English, a few words'},
                'why': {'type': 'string', 'description': 'Where the idea came from, in a few English words'},
            },
            'required': ['title', 'topic', 'why'],
        }},
        'replies': {'type': 'array', 'maxItems': 3, 'items': {
            'type': 'object',
            'properties': {'comment': {'type': 'string'}, 'reply': {'type': 'string', 'description': 'Warm Hindi reply, one line'}},
            'required': ['comment', 'reply'],
        }},
    },
    'required': ['ideas', 'replies'],
}
IDEAS_PROMPT = """You plan content for a Hindi Instagram/YouTube channel of short stick-figure life-lesson stories.

Viewers' recent comments:
{comments}

What people in India are searching for this week:
{trends}

Recent Reels (do not repeat): {recent}

1. ideas: 5 new life lessons for Reels, each a single clear lesson an ordinary Indian viewer relates to (family,
   friends, work, money habits, health, time, self-respect, studies...). Prefer what commenters ask about or
   struggle with, then searches that can carry a life lesson. Never news, politics, religion, celebrities,
   medical or money promises.
2. replies: warm one-line Hindi replies to up to 3 comments worth answering (questions or personal stories)."""

SEEDS = ('life lesson hindi', 'motivation hindi', 'रिश्ते', 'दोस्ती', 'पैसे बचाने', 'आदत', 'सफलता', 'माँ बाप')


def youtube_suggestions(seed):
    url = 'https://suggestqueries.google.com/complete/search?' + urllib.parse.urlencode({'client': 'firefox', 'ds': 'yt', 'hl': 'hi', 'q': seed})
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=20) as response:
        return json.loads(response.read().decode('utf-8', 'replace'))[1][:6]


def google_trends():
    with urllib.request.urlopen(urllib.request.Request('https://trends.google.com/trending/rss?geo=IN',
                                                       headers={'User-Agent': 'Mozilla/5.0'}), timeout=20) as response:
        root = ET.fromstring(response.read())
    return [item.findtext('title') for item in root.iter('item')][:15]


def trends():
    found = []
    for seed in SEEDS:
        try:
            found += youtube_suggestions(seed)
        except (urllib.error.URLError, TimeoutError, ValueError, IndexError):
            pass
    try:
        found += google_trends()
    except (urllib.error.URLError, TimeoutError, ET.ParseError):
        pass
    return list(dict.fromkeys(t for t in found if t))[:50]


def instagram_comments(limit=10):
    user = publish.instagram_user()
    media = publish.instagram_call(f'{user}/media', {'fields': 'id', 'limit': str(limit)}, 'GET').get('data', [])
    comments = []
    for m in media:
        try:
            comments += [c.get('text', '') for c in publish.instagram_call(
                f"{m['id']}/comments", {'fields': 'text', 'limit': '25'}, 'GET').get('data', [])]
        except publish.PublishError:
            pass
    return comments


def youtube_comments(limit=10):
    token = publish.youtube_token()
    auth = {'Authorization': 'Bearer ' + token}
    api = 'https://www.googleapis.com/youtube/v3/'
    channel = publish.request(api + 'channels?part=contentDetails&mine=true', headers=auth)[0]['items'][0]
    uploads = channel['contentDetails']['relatedPlaylists']['uploads']
    items = publish.request(api + 'playlistItems?' + urllib.parse.urlencode(
        {'part': 'contentDetails', 'playlistId': uploads, 'maxResults': limit}), headers=auth)[0].get('items', [])
    comments = []
    for item in items:
        try:
            threads = publish.request(api + 'commentThreads?' + urllib.parse.urlencode(
                {'part': 'snippet', 'videoId': item['contentDetails']['videoId'], 'maxResults': 20, 'textFormat': 'plainText'}),
                headers=auth)[0].get('items', [])
        except urllib.error.HTTPError:
            continue
        comments += [t['snippet']['topLevelComment']['snippet'].get('textDisplay', '') for t in threads]
    return comments


def comments():
    found, notes = [], []
    names = publish.configured()
    for name, fetch in (('instagram', instagram_comments), ('youtube', youtube_comments)):
        if name not in names:
            continue
        try:
            found += fetch()
        except (publish.PublishError, urllib.error.URLError, KeyError, IndexError) as exc:
            notes.append(f'{name} comments unavailable: {exc}')
    clean = [re.sub(r'\s+', ' ', c).strip()[:200] for c in found if c and len(c.strip()) > 3]
    return list(dict.fromkeys(clean))[:60], notes


def ideas():
    """{'ideas': [...], 'replies': [...], 'notes': [...]} from comments and trends."""
    said, notes = comments()
    searched = trends()
    recent = [h.get('title') for h in script.history()[-20:] if h.get('title')]
    answer, _ = gemini.json_call(IDEAS_PROMPT.format(
        comments='\n'.join(f'- {c}' for c in said) or '(no comments yet)',
        trends='\n'.join(f'- {t}' for t in searched) or '(unavailable)', recent=', '.join(recent) or '(none)'), IDEAS_SCHEMA, 0.8)
    out = {'ideas': [{k: str(i.get(k, ''))[:120] for k in ('title', 'topic', 'why')} for i in answer.get('ideas', []) if i.get('topic')][:5],
           'replies': answer.get('replies', [])[:3], 'notes': notes, 'comments': len(said), 'trends': len(searched)}
    return out


def ideas_message(found):
    lines = [f"💡 Next lessons (from {found['comments']} comments and {found['trends']} searches)"]
    lines += [f"{n}. {i['title']} ({i['topic']}) · {i['why']}" for n, i in enumerate(found['ideas'], 1)]
    if found.get('replies'):
        lines.append('\n💬 Replies you could post (copy and paste):')
        lines += [f"• \"{r.get('comment', '')[:80]}\"\n  ↳ {r.get('reply', '')}" for r in found['replies']]
    from . import occasions
    soon = occasions.coming_up()
    if soon:
        lines.append('\n' + soon + ' (Reels for these are made automatically a few days ahead)')
    lines += [f"ℹ️ {n}" for n in found.get('notes', [])]
    lines.append('\nTap a number to make that Reel.')
    return '\n'.join(lines)


def remember_ideas(found):
    """Save the ideas so plain /reel picks them first (fresh, audience-driven lessons)."""
    path = script.history_path().with_name('ideas.json')
    old = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    path.write_text(json.dumps((old + [i['topic'] for i in found['ideas']])[-30:], ensure_ascii=False, indent=1), encoding='utf-8')


# --- Instagram token ------------------------------------------------------------------------

def refresh_token():
    """A fresh 60-day Instagram token from the current one (it must be at least a day old and still valid)."""
    token = os.environ['INSTAGRAM_ACCESS_TOKEN'].strip()
    url = f'{publish.GRAPH.rsplit("/", 1)[0]}/refresh_access_token?' + urllib.parse.urlencode(
        {'grant_type': 'ig_refresh_token', 'access_token': token})
    try:
        answer, _ = publish.request(url)
    except urllib.error.HTTPError as exc:
        _, message, _ = publish.detail(exc)
        raise publish.PublishError(f'Instagram did not renew the token: {message}. If it already expired, create a new '
                                   'long-lived token and replace the INSTAGRAM_ACCESS_TOKEN secret.') from None
    if not answer.get('access_token'):
        raise publish.PublishError('Instagram returned no new token')
    return answer['access_token'], int(answer.get('expires_in', 0)) // 86400
