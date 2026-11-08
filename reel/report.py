"""Weekly numbers for the stickman channel: views, likes, saves, shares and comments of the last 7 days on
Instagram and YouTube, the best Reels, and which topics did best, sent to Telegram. The Instagram section adds
shares, likes and saves per person reached, watch time and skip rate by style, series and hook (reel/growth.py).

Each platform is skipped (with a note) when its secrets are not set or the token cannot read statistics.
"""
import datetime as dt
import urllib.error
import urllib.parse

from . import publish

DAYS = 7


def since(days=DAYS, now=None):
    return (now or dt.datetime.now(dt.timezone.utc)) - dt.timedelta(days=days)


def when(text):
    return dt.datetime.fromisoformat(text.replace('Z', '+00:00').replace('+0000', '+00:00'))


def instagram(start):
    user = publish.instagram_user()
    media = publish.instagram_call(f'{user}/media', {
        'fields': 'id,caption,timestamp,permalink,like_count,comments_count,media_product_type', 'limit': '40'}, 'GET').get('data', [])
    items = []
    for m in media:
        if when(m['timestamp']) < start:
            continue
        stats = {'likes': m.get('like_count', 0), 'comments': m.get('comments_count', 0)}
        try:
            insights = publish.instagram_call(f"{m['id']}/insights", {'metric': 'views,reach,saved,shares'}, 'GET').get('data', [])
            stats.update({i['name']: (i.get('values') or [{}])[0].get('value', i.get('total_value', {}).get('value', 0)) for i in insights})
        except publish.PublishError:
            pass  # insights need a professional account and a day or two of data
        items.append({'title': (m.get('caption') or '').split('\n')[0][:90], 'url': m.get('permalink', ''), 'posted_at': when(m['timestamp']),
                      'views': stats.get('views', 0), 'likes': stats['likes'], 'comments': stats['comments'],
                      'saves': stats.get('saved', 0), 'shares': stats.get('shares', 0)})
    return items


def youtube(start):
    token = publish.youtube_token()
    auth = {'Authorization': 'Bearer ' + token}
    api = 'https://www.googleapis.com/youtube/v3/'
    channel = publish.request(api + 'channels?part=contentDetails,statistics&mine=true', headers=auth)[0]['items'][0]
    uploads = channel['contentDetails']['relatedPlaylists']['uploads']
    listed = publish.request(api + 'playlistItems?' + urllib.parse.urlencode(
        {'part': 'contentDetails', 'playlistId': uploads, 'maxResults': 25}), headers=auth)[0].get('items', [])
    ids = [i['contentDetails']['videoId'] for i in listed]
    videos = publish.request(api + 'videos?' + urllib.parse.urlencode(
        {'part': 'snippet,statistics', 'id': ','.join(ids)}), headers=auth)[0].get('items', []) if ids else []
    items = []
    for v in videos:
        if when(v['snippet']['publishedAt']) < start:
            continue
        s = v.get('statistics', {})
        items.append({'title': v['snippet']['title'][:60], 'url': f"https://youtube.com/shorts/{v['id']}", 'posted_at': when(v['snippet']['publishedAt']),
                      'views': int(s.get('viewCount', 0)), 'likes': int(s.get('likeCount', 0)),
                      'comments': int(s.get('commentCount', 0)), 'saves': 0, 'shares': 0})
    return items, int(channel.get('statistics', {}).get('subscriberCount', 0))


def totals(items):
    keys = ('views', 'likes', 'comments', 'saves', 'shares')
    return {k: sum(int(i.get(k) or 0) for i in items) for k in keys}


def score(item):
    """Engagement that predicts reach: shares and saves count most, then comments and likes."""
    return int(item['views']) + 10 * int(item['likes']) + 20 * int(item['comments']) + 40 * (int(item['saves']) + int(item['shares']))


def message(platforms, notes, now=None, extra=''):
    end = (now or dt.datetime.now(dt.timezone.utc)) + dt.timedelta(minutes=330)
    lines = [f"📊 Stickman Reels: last {DAYS} days (to {end:%d %b})"]
    best = []
    for name, (items, extra) in platforms.items():
        t = totals(items)
        lines.append(f"\n{name}: {len(items)} Reels · 👁 {t['views']:,} · ❤️ {t['likes']:,} · 💬 {t['comments']:,}"
                     + (f" · 🔖 {t['saves']:,} · 📤 {t['shares']:,}" if name == 'Instagram' else '') + (f' · {extra}' if extra else ''))
        best += [(score(i), name, i) for i in items]
    best.sort(key=lambda x: -x[0])
    if best:
        lines.append('\n🏆 Best Reels')
        for _, name, item in best[:3]:
            lines.append(f"• {item['title']} ({name}, 👁 {int(item['views']):,}, ❤️ {item['likes']})\n  {item['url']}")
        lines.append('\nTip: make more Reels like the top one (same kind of lesson and hook). Shares and saves matter most.')
    if extra:
        lines.append(extra)
    lines += [f'\nℹ️ {n}' for n in notes]
    return '\n'.join(lines)


def weekly():
    start = since()
    platforms, notes = {}, []
    names = publish.configured()
    from . import growth
    if 'instagram' in names:
        try:
            growth.snapshot()  # catch up on any 24 h / 72 h / 7 d insights the daily run missed
        except (publish.PublishError, urllib.error.URLError, KeyError, ValueError) as exc:
            notes.append(f'Instagram insights unavailable: {exc}')
        try:
            platforms['Instagram'] = (instagram(start), '')
        except (publish.PublishError, urllib.error.URLError, KeyError) as exc:
            notes.append(f'Instagram numbers unavailable: {exc}')
    else:
        notes.append('Instagram is not connected yet (INSTAGRAM_ACCESS_TOKEN).')
    if 'youtube' in names:
        try:
            items, subs = youtube(start)
            platforms['YouTube'] = (items, f'{subs:,} subscribers')
        except urllib.error.HTTPError as exc:
            notes.append('YouTube numbers unavailable (HTTP %s). If it says 403, sign in again so the bot may read stats: '
                         'python tools/youtube_auth.py --save-to-github' % exc.code)
        except (publish.PublishError, urllib.error.URLError, KeyError, IndexError) as exc:
            notes.append(f'YouTube numbers unavailable: {exc}')
    else:
        notes.append('YouTube is not connected yet (YOUTUBE_ secrets).')
    scored = [{**i, 'score': score(i)} for items, _ in platforms.values() for i in items]
    if scored:
        growth.record_scores(scored)  # teaches the writer and the best-time picker (saved in the topic history)
        learned = growth.learned_slot()
        notes.append(f'Best posting time so far: {learned}:00 IST' if learned is not None else
                     'Best posting time: not learned yet, so Reels go out 7-9 pm IST. Aim for 3-5 Reels a week.')
    return message(platforms, notes, extra=growth.insights_message())
