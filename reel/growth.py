"""Growth: learn from the numbers, post at the best time, and find the next lessons.

- Best time: the weekly report records each post's reach by time slot (IST); `best_slot()` picks the slot
  whose posts did best (at least 2 posts there). Until then the evening window, 19:00-21:00 IST, is the default:
  with POST_AT_PEAK=true a Reel made in that window goes out at once, otherwise it waits for 19:00.
- Learning: the report stores a score for each Reel in the topic history; the writer is told which recent
  Reels did best and worst, so it leans toward what works.
- Measurement: `snapshot()` (daily, `python -m reel insights`) reads each Instagram Reel's insights 24 hours,
  72 hours and 7 days after posting (reach, shares, likes, saves, average watch time, skip rate) into its history
  entry. `rates()` turns them into shares, likes and saves per reach, watch time / length and skip rate; the
  weekly report compares them by style, series and hook, and `lessons_learned()` tells the writers which
  Reels people sent, watched to the end and did not skip.
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

from . import gemini, publish, reach, script

IST = dt.timezone(dt.timedelta(minutes=330))
SLOTS = (8, 13, 19, 21)  # posting slots, hour IST; the queue workflow runs at each
DEFAULT_SLOT = 19
DEFAULT_WINDOW = (19, 21)  # IST: the evening window used until the numbers pick a best slot


def slot_of(when):
    """The posting slot (hour IST) closest to a time."""
    hour = when.astimezone(IST).hour + when.astimezone(IST).minute / 60
    return min(SLOTS, key=lambda s: abs(s - hour))


def learned_slot(history=None):
    """The slot whose Reels reached the most people on average (needs 2+ posts there), else None."""
    scores = {}
    for item in history if history is not None else script.history():
        if item.get('slot') in SLOTS and item.get('score') is not None:
            scores.setdefault(item['slot'], []).append(item['score'])
    ranked = sorted(((sum(v) / len(v), s) for s, v in scores.items() if len(v) >= 2), reverse=True)
    return ranked[0][1] if ranked else None


def best_slot(history=None):
    """The learned best slot, else 19:00 (the start of the evening window)."""
    learned = learned_slot(history)
    return DEFAULT_SLOT if learned is None else learned


def next_time(slot, now=None):
    """The next time the clock shows `slot`:00 IST (today or tomorrow), in UTC."""
    now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(IST)
    at = now.replace(hour=slot, minute=0, second=0, microsecond=0)
    if at <= now + dt.timedelta(minutes=10):
        at += dt.timedelta(days=1)
    return at.astimezone(dt.timezone.utc)


def post_now(now=None, slot=None):
    """True when posting at once is fine: POST_AT_PEAK is off, the best slot is less than 45 minutes away, or it
    passed less than 2 hours ago (the next one is 22+ hours away: longer than Instagram keeps an upload, and
    posting now is still close to the best time)."""
    if os.getenv('POST_AT_PEAK', '').strip().lower() != 'true':
        return True
    now = now or dt.datetime.now(dt.timezone.utc)
    if slot is None and learned_slot() is None and DEFAULT_WINDOW[0] <= now.astimezone(IST).hour < DEFAULT_WINDOW[1]:
        return True  # nothing learned yet: anywhere in the evening window is the best time
    wait = next_time(slot or best_slot(), now) - now
    return wait <= dt.timedelta(minutes=45) or wait > dt.timedelta(hours=22)


# --- learning from the numbers --------------------------------------------------------------

def entry_for(history, caption):
    """The history entry of a posted Reel, from its caption's first line ("<title> (Part 1/2) | keywords...")."""
    head = (caption or '').split('\n')[0].split(' | ')[0].strip()
    if not head:
        return None
    for h in reversed(history):
        if h.get('title') and h['title'] + reach.part_label(h) == head:
            return h
    bare = head.split(' (भाग')[0].split(' (Part')[0].strip()
    return next((h for h in reversed(history) if h.get('title') == bare), None)


def record_scores(items):
    """Store each Reel's score (and the slot it went out at) in the topic history, matched by title."""
    history = script.history()
    for item in items:
        entry = entry_for(history, item.get('title'))
        if entry is None:
            continue
        entry['score'] = max(entry.get('score') or 0, int(item.get('score', 0)))
        if item.get('posted_at'):
            entry['slot'] = slot_of(item['posted_at'])
    script.history_path().write_text(json.dumps(history[-200:], ensure_ascii=False, indent=1), encoding='utf-8')
    return history


def lessons_learned(history=None, n=3):
    """Prompt lines naming the recent Reels that did best and worst (empty until there are scores), and, once
    Instagram insights are in, the Reels people sent most, watched longest and skipped least."""
    items = (history if history is not None else script.history())[-40:]
    lines = []
    scored = [h for h in items if h.get('score') is not None]
    if len(scored) >= 4:
        scored.sort(key=lambda h: -h['score'])
        best = ', '.join(f"\"{h['title']}\" ({h.get('topic', '')})" for h in scored[:n])
        worst = ', '.join(f"\"{h['title']}\"" for h in scored[-n:])
        lines.append(f'- Our audience loved these recent Reels: {best}. Lean toward what made them work (the kind of lesson, '
                     f'the hook, the emotion), without copying them. These did worst: {worst}; avoid their angle.')
    measured = [(h, rates(latest(h), h.get('duration'))) for h in items if latest(h)]
    if len(measured) >= 3:
        def top(key, low=False):
            ranked = sorted((m for m in measured if m[1].get(key) is not None), key=lambda m: m[1][key], reverse=not low)
            return ranked[0] if ranked else None
        sent, watched, kept = top('shares'), top('watch'), top('skip', low=True)
        if sent:
            h = sent[0]
            lines.append(f"- Most SENT on Instagram (shares per reach, the strongest signal): \"{h['title']}\""
                         + (f" (sent to: {h['send_target']})" if h.get('send_target') else '')
                         + '. Write endings people want to send to someone like that.')
        if watched:
            lines.append(f"- Watched longest: \"{watched[0]['title']}\" ({watched[1]['watch']:.0%} of its length on average); "
                         'keep that pace and length.')
        if kept and kept[0].get('hook'):
            lines.append(f"- The hook fewest people skipped: \"{kept[0]['hook']}\" ({kept[1]['skip']:.0%} skipped). "
                         'Open as strongly: a contrast, a mystery or a number in the first words.')
    return '\n'.join(lines)


# --- measuring each Reel on Instagram (24 h, 72 h and 7 days after posting) --------------------

CHECKPOINTS = (('24h', 24), ('72h', 72), ('7d', 168))
METRICS = ('reach', 'views', 'likes', 'comments', 'saved', 'shares', 'ig_reels_avg_watch_time', 'reels_skip_rate')
RECENT_DAYS = 10  # how far back the daily snapshot looks (a missed day is caught up later)


def metric_value(item):
    values = item.get('values') or [{}]
    value = values[0].get('value') if values and 'value' in values[0] else item.get('total_value', {}).get('value')
    return value if isinstance(value, (int, float)) else None


def media_insights(media_id):
    """The Reel's insights. Instagram refuses the whole call when one metric is not available (some, like
    reels_skip_rate, are still "in development"), so then each metric is asked for on its own and the missing
    ones are left out."""
    def ask(metrics):
        data = publish.instagram_call(f'{media_id}/insights', {'metric': ','.join(metrics)}, 'GET').get('data', [])
        return {i['name']: metric_value(i) for i in data if metric_value(i) is not None}
    try:
        return ask(METRICS)
    except publish.PublishError:
        pass
    found = {}
    for metric in METRICS:
        try:
            found.update(ask([metric]))
        except publish.PublishError:
            continue  # not available for this account or this Reel (yet)
    return found


def when(text):
    return dt.datetime.fromisoformat(text.replace('Z', '+00:00').replace('+0000', '+00:00'))


def snapshot(now=None, history=None):
    """Store the insights of each recent Instagram Reel whose 24 h, 72 h or 7 d checkpoint has passed (once each).
    Returns [(entry, checkpoint, numbers)] for the new snapshots."""
    now = now or dt.datetime.now(dt.timezone.utc)
    items = history if history is not None else script.history()
    user = publish.instagram_user()
    media = publish.instagram_call(f'{user}/media', {
        'fields': 'id,caption,timestamp,media_product_type,like_count,comments_count', 'limit': '30'}, 'GET').get('data', [])
    taken = []
    for m in media:
        if m.get('media_product_type') not in (None, 'REELS'):
            continue
        posted = when(m['timestamp'])
        age = (now - posted).total_seconds() / 3600
        if age > RECENT_DAYS * 24:
            continue
        entry = entry_for(items, m.get('caption'))
        if entry is None:
            continue
        done = entry.setdefault('insights', {})
        due = [name for name, hours in CHECKPOINTS if age >= hours and name not in done]
        if not due:
            continue
        numbers = media_insights(m['id'])
        numbers.setdefault('likes', m.get('like_count', 0))
        numbers.setdefault('comments', m.get('comments_count', 0))
        numbers['age_h'] = round(age)
        entry['ig_media'] = m['id']
        entry.setdefault('slot', slot_of(posted))
        for name in due[-1:]:  # a late run takes only the newest checkpoint it reached
            done[name] = numbers
            taken.append((entry, name, numbers))
    if history is None and taken:
        script.history_path().write_text(json.dumps(items[-200:], ensure_ascii=False, indent=1), encoding='utf-8')
    return taken


def latest(entry):
    """The newest snapshot of a history entry (7 d, else 72 h, else 24 h), or None."""
    shots = (entry or {}).get('insights') or {}
    return next((shots[name] for name, _ in reversed(CHECKPOINTS) if name in shots), None)


def rates(numbers, duration=None):
    """Per-reach rates and watch numbers: shares, likes and saves per reach, watch time / length, skip rate."""
    numbers = numbers or {}
    reach_ = numbers.get('reach') or 0
    out = {'reach': reach_}
    for key, metric in (('shares', 'shares'), ('likes', 'likes'), ('saves', 'saved')):
        out[key] = numbers[metric] / reach_ if reach_ and numbers.get(metric) is not None else None
    watch = numbers.get('ig_reels_avg_watch_time')  # milliseconds
    out['watch'] = min(1.5, watch / 1000 / float(duration)) if watch and duration else None
    skip = numbers.get('reels_skip_rate')
    out['skip'] = (skip / 100 if skip > 1 else skip) if isinstance(skip, (int, float)) else None
    return out


def average(group):
    """The mean of each rate over the Reels that have it."""
    out = {}
    for key in ('shares', 'likes', 'saves', 'watch', 'skip'):
        values = [g[key] for g in group if g.get(key) is not None]
        out[key] = sum(values) / len(values) if values else None
    out['n'] = len(group)
    return out


def rate_text(r):
    parts = [f"📤 {r['shares']:.1%}" if r.get('shares') is not None else '',
             f"❤️ {r['likes']:.1%}" if r.get('likes') is not None else '',
             f"🔖 {r['saves']:.1%}" if r.get('saves') is not None else '',
             f"⏱ {r['watch']:.0%} watched" if r.get('watch') is not None else '',
             f"⏭ {r['skip']:.0%} skipped" if r.get('skip') is not None else '']
    return ' · '.join(x for x in parts if x)


def breakdown(history=None):
    """{'style': {...}, 'series': {...}, 'send_target': {...}} of average rates, and the hooks by skip rate."""
    items = [h for h in (history if history is not None else script.history())[-60:] if latest(h)]
    groups = {'style': {}, 'series': {}, 'send_target': {}}
    hooks = []
    for h in items:
        r = rates(latest(h), h.get('duration'))
        for key in groups:
            groups[key].setdefault(h.get(key) or ('story' if key == 'style' else '-'), []).append(r)
        if h.get('hook'):
            hooks.append((h['hook'], r))
    out = {key: {name: average(rs) for name, rs in by.items() if name != '-'} for key, by in groups.items()}
    out['hooks'] = sorted((x for x in hooks if x[1].get('skip') is not None), key=lambda x: x[1]['skip'])
    return out


def insights_message(history=None):
    """The weekly report's Instagram section: rates by style, series and who it is sent to, and the best and
    worst hooks (empty until there are snapshots)."""
    found = breakdown(history)
    if not any(found[k] for k in ('style', 'series', 'send_target')):
        return ''
    lines = ['\n📈 What works on Instagram (per person reached)']
    for key, label in (('style', 'Style'), ('series', 'Series'), ('send_target', 'Sent to')):
        for name, r in sorted(found[key].items(), key=lambda x: -(x[1].get('shares') or 0)):
            lines.append(f"• {label} {name} ({r['n']}): {rate_text(r)}")
    if found['hooks']:
        best, worst = found['hooks'][0], found['hooks'][-1]
        lines.append(f"🪝 Hook fewest skipped: \"{best[0][:70]}\" ({best[1]['skip']:.0%})")
        if worst is not best:
            lines.append(f"🪝 Most skipped: \"{worst[0][:70]}\" ({worst[1]['skip']:.0%})")
    return '\n'.join(lines)


def snapshot_message(taken):
    """A short Telegram note for new snapshots ("after 24h: reach 1,200 · 📤 3.1% ...")."""
    lines = ['📈 Instagram check-in']
    for entry, name, numbers in taken:
        r = rates(numbers, entry.get('duration'))
        lines.append(f"• {entry['title']}{reach.part_label(entry)} after {name}: reach {int(r['reach']):,}"
                     + (f" · {rate_text(r)}" if rate_text(r) else ''))
    return '\n'.join(lines)


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
