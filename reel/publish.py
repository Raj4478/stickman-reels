"""Post a finished Reel to Instagram (Reels, a carousel, a trial Reel), YouTube (Shorts) and Facebook (Reels),
each only when its secrets are set.

Instagram: INSTAGRAM_ACCESS_TOKEN (long-lived, 60 days) and optionally INSTAGRAM_USER_ID. The video is sent
with Instagram's resumable upload, so it needs no public hosting; the cover is the hook frame (thumb_offset).
YouTube: YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET and YOUTUBE_REFRESH_TOKEN from tools/youtube_auth.py.

Adapted from the infographic repo's publisher. A receipt (publish.json) records what went where, so a Reel is
never posted twice to the same place.
"""
import datetime as dt
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

GRAPH = 'https://graph.instagram.com/v23.0'
RUPLOAD = 'https://rupload.facebook.com/ig-api-upload/v23.0'
COVER_MS = 667  # the cover frame rendered by the workflow (frame 20 at 30 fps): the hook title over the action
FB_GRAPH = 'https://graph.facebook.com/v23.0'
FB_RUPLOAD = 'https://rupload.facebook.com/video-upload/v23.0'
NAMES = {'instagram': 'Instagram', 'youtube': 'YouTube Shorts', 'facebook': 'Facebook Reels', 'carousel': 'Instagram carousel',
         'instagram_trial': 'Instagram trial Reel (hook B)'}


class PublishError(RuntimeError):
    pass


def on(name):
    return os.getenv(name, '').strip().lower() == 'true'


def configured():
    """The platforms whose secrets (and switches) are set."""
    from . import media
    names = []
    instagram = bool(os.getenv('INSTAGRAM_ACCESS_TOKEN', '').strip())
    if instagram:
        names.append('instagram')
    if all(os.getenv(k, '').strip() for k in ('YOUTUBE_CLIENT_ID', 'YOUTUBE_CLIENT_SECRET', 'YOUTUBE_REFRESH_TOKEN')):
        names.append('youtube')
    if os.getenv('FACEBOOK_PAGE_ID', '').strip() and os.getenv('FACEBOOK_PAGE_TOKEN', '').strip():
        names.append('facebook')
    if instagram and on('CAROUSEL') and media.configured():
        names.append('carousel')
    if instagram and on('HOOK_TEST'):
        names.append('instagram_trial')
    return names


def request(url, data=None, headers=None, method=None, timeout=120, attempts=3):
    """JSON from `url`; 5xx answers and network errors are retried (`attempts=1` for calls that must not repeat)."""
    body = data if isinstance(data, (bytes, type(None))) else (
        json.dumps(data).encode() if headers and 'application/json' in headers.get('Content-Type', '')
        else urllib.parse.urlencode(data).encode())
    for attempt in range(attempts):
        req = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw = response.read()
                return (json.loads(raw) if raw.strip().startswith(b'{') else {}), response.headers
        except urllib.error.HTTPError as exc:
            if exc.code not in (500, 502, 503, 504) or attempt == attempts - 1:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == attempts - 1:
                raise
        time.sleep(3 * (attempt + 1))


def detail(exc):
    try:
        payload = json.loads(exc.read() or b'{}')
    except ValueError:
        payload = {}
    error = payload.get('error', payload)
    if isinstance(error, str):
        return error, payload.get('error_description', ''), payload
    reasons = [e.get('reason', '') for e in error.get('errors', [])]
    return (reasons[0] if reasons else str(error.get('code', ''))), error.get('message', ''), error


# Niche tags first: YouTube shows the first three hashtags above the title, and a few focused tags reach
# further than a long list (more than 15 makes YouTube ignore them all).
CHANNEL_TAGS = ['#hindikahani', '#lifelessons', '#seekhsketch']
SEARCH_PHRASE = 'ज़िंदगी की सीख'  # what people type when looking for this kind of video
# comic Reels (reel/comic.py) are found through comedy searches instead
COMIC_TAGS = ['#hindicomedy', '#desicomedy', '#seekhsketch']
COMIC_PHRASE = 'देसी कॉमेडी'


def comic(story):
    return story.get('style') == 'comic'


def hashtag_list(story, limit=6):
    """The channel's niche tags, then the story's own, without repeats or near-repeats."""
    seen, out = set(), []
    for tag in (COMIC_TAGS if comic(story) else CHANNEL_TAGS) + (story.get('hashtags') or []):
        key = tag.lower().lstrip('#').replace('_', '')
        if key and key not in seen:
            seen.add(key)
            out.append('#' + tag.lstrip('#'))
    return out[:limit]


def hashtags(story):
    """The hashtags as one line (for the caption and the copy button)."""
    return ' '.join(hashtag_list(story))


def copy_texts(story):
    """What you paste when posting by hand: the caption (title, text, question) and the hashtags, separately."""
    part = f" (भाग {story['part']})" if story.get('part') else ''
    caption = '\n\n'.join(x for x in (story['title'] + part, story.get('instagram_caption') or story['lesson'], story.get('ask', '')) if x)
    return {'caption': caption, 'hashtags': hashtags(story)}


def texts(story):
    """Caption, YouTube title, description and tags for a script, written for reach:
    - title: the hook title first (it decides the tap), then the search phrase, then #shorts; under 70
      characters where it can be, because the feed cuts long titles;
    - description: the spoken hook as the first line (search and previews show it), the story, the lesson,
      the question that invites comments, a subscribe line and 5-6 focused hashtags;
    - tags: the story's tags plus the channel's keywords.
    """
    tags = hashtag_list(story)
    part = f" (भाग {story['part']})" if story.get('part') else ''
    handle = os.getenv('REEL_HANDLE', '').strip()
    caption = '\n\n'.join(x for x in (story['title'] + part, story.get('instagram_caption') or story['lesson'],
                                      story.get('ask', ''), ' '.join(tags)) if x)
    title = f"{story['title']}{part} | {COMIC_PHRASE if comic(story) else SEARCH_PHRASE}"
    title = (title if len(title) <= 80 else (story['title'] + part)[:80]) + ' #shorts'
    subscribe = ('🔔 रोज़ हँसी के लिए Subscribe करें' if comic(story) else '🔔 रोज़ एक नई सीख के लिए Subscribe करें') + (f' {handle}' if handle else '')
    ending = story['lesson'] if comic(story) else 'सीख: ' + story['lesson']  # a comic Reel ends on its punchline
    description = '\n\n'.join(x for x in (story.get('hook', ''), story.get('instagram_caption') or '', ending,
                                          story.get('ask', ''), subscribe, ' '.join(tags + ['#shorts'])) if x)
    keywords = [t.lstrip('#') for t in tags] + (['hindi comedy', 'cartoon comedy', 'desi comedy', 'funny cartoon', 'हिंदी कॉमेडी']
                                                if comic(story) else ['stickman animation', 'hindi stories', 'life lessons', 'हिंदी कहानी', 'moral stories'])
    return {'caption': caption[:2200], 'title': title[:100], 'description': description[:4900],
            'tags': list(dict.fromkeys(keywords))[:20]}


# --- YouTube ---------------------------------------------------------------------------------

TOKEN_INFO = {}  # what Google said about the sign-in on the last token exchange


def youtube_token():
    try:
        token, _ = request('https://oauth2.googleapis.com/token', {
            'client_id': os.environ['YOUTUBE_CLIENT_ID'].strip(), 'client_secret': os.environ['YOUTUBE_CLIENT_SECRET'].strip(),
            'refresh_token': os.environ['YOUTUBE_REFRESH_TOKEN'].strip(), 'grant_type': 'refresh_token'})
    except urllib.error.HTTPError as exc:
        reason, message, _ = detail(exc)
        if reason == 'invalid_grant':
            raise PublishError('YouTube sign-in has expired or was revoked. Keep the Google app "In production" '
                               '(console.cloud.google.com/auth/audience), then run: python tools/youtube_auth.py --save-to-github') from None
        raise PublishError(f'YouTube sign-in failed ({reason or exc.code}): {message}') from None
    TOKEN_INFO.clear()
    # Google sends a new refresh token only rarely (rotation); the keepalive workflow saves it back.
    if token.get('refresh_token') and token['refresh_token'] != os.environ['YOUTUBE_REFRESH_TOKEN'].strip():
        TOKEN_INFO['new_refresh_token'] = token['refresh_token']
    # Only sign-ins that will end carry this (most often: the Google app is still in "Testing", 7 days).
    if str(token.get('refresh_token_expires_in', '')).isdigit():
        TOKEN_INFO['expires_days'] = int(token['refresh_token_expires_in']) // 86400
    return token['access_token']


def youtube_check():
    """The daily sign-in check: {'ok', 'channel', 'expires_days', 'new_refresh_token', 'problem'}."""
    try:
        token = youtube_token()
    except PublishError as exc:
        return {'ok': False, 'problem': str(exc)}
    result = {'ok': True, **TOKEN_INFO}
    try:
        channel = request('https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true',
                          headers={'Authorization': 'Bearer ' + token})[0].get('items', [])
        result['channel'] = channel[0]['snippet']['title'] if channel else ''
        if not channel:
            result.update(ok=False, problem='This Google account has no YouTube channel yet: create it at youtube.com.')
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            result['note'] = 'The sign-in may upload but not read the channel (sign in again to allow reading stats).'
        else:
            result.update(ok=False, problem=f'YouTube answered HTTP {exc.code} to the channel check.')
    return result


def youtube_upload(video, story, ctx=None, title=None, description=None, shorts=True):
    """Upload a video. With ctx['publish_at'] it is uploaded private and YouTube makes it public then."""
    ctx = ctx or {}
    token = youtube_token()
    meta = texts(story)
    privacy = os.getenv('YOUTUBE_PRIVACY', '').strip() or 'public'
    at = ctx.get('publish_at') if privacy == 'public' else None
    body = {'snippet': {'title': title or meta['title'], 'description': description or meta['description'], 'tags': meta['tags'],
                        'categoryId': '22', 'defaultLanguage': 'hi', 'defaultAudioLanguage': 'hi'},
            # Made for kids only when the Reel was written for the kids audience (COPPA: comments and personalised ads
            # turn off). Family and adult Reels are general-audience. Clearly animated with a clearly synthetic voice,
            # so not "altered or synthetic" realistic content under YouTube's disclosure rule.
            'status': {'privacyStatus': 'private' if at else privacy,
                       'selfDeclaredMadeForKids': story.get('audience') == 'kids', 'embeddable': True,
                       'containsSyntheticMedia': False,
                       **({'publishAt': at.strftime('%Y-%m-%dT%H:%M:%SZ')} if at else {})}}
    size = video.stat().st_size
    try:
        _, headers = request('https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status',
                             body, {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json; charset=UTF-8',
                                    'X-Upload-Content-Type': 'video/mp4', 'X-Upload-Content-Length': str(size)})
        result, _ = request(headers['Location'], video.read_bytes(),
                            {'Authorization': 'Bearer ' + token, 'Content-Type': 'video/mp4'}, method='PUT', timeout=900)
    except urllib.error.HTTPError as exc:
        reason, message, _ = detail(exc)
        if reason in ('quotaExceeded', 'rateLimitExceeded', 'userRateLimitExceeded', 'uploadLimitExceeded'):
            raise PublishError(f'YouTube limit reached ({reason}); it resets daily. Tap Post again tomorrow.') from None
        if reason == 'youtubeSignupRequired':
            raise PublishError('This Google account has no YouTube channel yet: create it at youtube.com, then post again.') from None
        raise PublishError(f'YouTube refused the upload ({reason or exc.code}): {message}') from None
    if not result.get('id'):
        raise PublishError('YouTube accepted the upload but returned no video ID')
    url = f"https://youtube.com/{'shorts/' if shorts else 'watch?v='}{result['id']}"
    if at:
        return {'id': result['id'], 'url': url, 'status': 'scheduled', 'publish_at': at.isoformat()}
    actual = result.get('status', {}).get('privacyStatus', privacy)
    note = ('YouTube kept it private: uploads from an unaudited Google Cloud project stay private until it passes the free '
            'API audit. Make it public in YouTube Studio meanwhile.') if actual != privacy else ''
    return {'id': result['id'], 'url': url, 'privacy': actual, 'note': note}


# --- Instagram -------------------------------------------------------------------------------

def instagram_call(path, fields=None, method='POST', attempts=3):
    params = {**(fields or {}), 'access_token': os.environ['INSTAGRAM_ACCESS_TOKEN'].strip()}
    try:
        if method == 'GET':
            return request(f'{GRAPH}/{path}?' + urllib.parse.urlencode(params), attempts=attempts)[0]
        return request(f'{GRAPH}/{path}', params, attempts=attempts)[0]
    except urllib.error.HTTPError as exc:
        _, message, error = detail(exc)
        if error.get('code') == 190:
            raise PublishError('Instagram token expired or invalid: create a new long-lived token (60 days) and replace '
                               'the INSTAGRAM_ACCESS_TOKEN secret.') from None
        raise PublishError(f"Instagram refused ({error.get('code')}/{error.get('error_subcode')}): {message}") from None


def instagram_user():
    return os.getenv('INSTAGRAM_USER_ID', '').strip() or str(instagram_call('me', {'fields': 'user_id'}, 'GET')['user_id'])


def instagram_wait(container, wait=10, attempts=36):
    for _ in range(attempts):
        status = instagram_call(container, {'fields': 'status_code,status'}, 'GET')
        if status.get('status_code') == 'FINISHED':
            return
        if status.get('status_code') in ('ERROR', 'EXPIRED'):
            raise PublishError(f"Instagram could not process it: {status.get('status', status.get('status_code'))}")
        time.sleep(wait)
    raise PublishError('Instagram was still processing after 6 minutes; nothing was published. Tap Post again later.')


# Instagram keeps a processed upload for 24 hours; a Reel is only held for its best time when that is sooner
INSTAGRAM_HOLD = dt.timedelta(hours=23)


def container_status(container):
    try:
        return instagram_call(container, {'fields': 'status_code'}, 'GET').get('status_code', '')
    except (PublishError, urllib.error.URLError, TimeoutError, OSError):
        return ''


def instagram_finish(container, user=None):
    """Publish a processed container; returns its id and link.

    The publish call is never repeated (a retry could post the Reel twice), and once it has gone through the Reel
    counts as published even if the link cannot be fetched, so a failure is only reported when it is not live.
    """
    user = user or instagram_user()
    try:
        media = instagram_call(f'{user}/media_publish', {'creation_id': container}, attempts=1)['id']
    except (PublishError, urllib.error.URLError, TimeoutError, OSError):
        if container_status(container) == 'PUBLISHED':  # it went through; only the answer was lost
            return {'id': '', 'url': '', 'note': 'Published (Instagram did not send the link back)'}
        raise
    try:
        link = instagram_call(media, {'fields': 'permalink'}, 'GET').get('permalink', '')
    except (PublishError, urllib.error.URLError, TimeoutError, OSError):
        link = ''  # it is live: only the link is missing
    return {'id': media, 'url': link}


def hold_until(ctx):
    """When to publish an Instagram upload: ctx['publish_at'], unless that is too far away for Instagram to keep the
    upload (then it is published at once)."""
    at = ctx.get('publish_at')
    if at and at - dt.datetime.now(dt.timezone.utc) > INSTAGRAM_HOLD:
        print(f'Instagram keeps an upload for 24 hours only: publishing now instead of {at.isoformat()}')
        return None
    return at


def instagram_reel(video, story, ctx, trial=False):
    """Upload a Reel (or a trial Reel, shown to non-followers first). Queued when ctx['publish_at'] is set."""
    user = instagram_user()
    fields = {'media_type': 'REELS', 'upload_type': 'resumable', 'caption': texts(story)['caption'], 'thumb_offset': str(COVER_MS)}
    if trial:
        fields['trial_params'] = json.dumps({'graduation_strategy': 'SS_PERFORMANCE'})
    else:
        fields['share_to_feed'] = 'true'
    container = instagram_call(f'{user}/media', fields)['id']
    data = video.read_bytes()
    try:
        request(f'{RUPLOAD}/{container}', data, {'Authorization': 'OAuth ' + os.environ['INSTAGRAM_ACCESS_TOKEN'].strip(),
                                                 'offset': '0', 'file_size': str(len(data))}, timeout=600)
    except urllib.error.HTTPError as exc:
        raise PublishError(f'Instagram upload failed (HTTP {exc.code})') from None
    instagram_wait(container)
    at = hold_until(ctx)
    if at and not trial:
        # Instagram keeps a processed upload for 24 hours: the queue workflow publishes it at the best time
        return {'status': 'queued', 'container': container, 'publish_at': at.isoformat()}
    return instagram_finish(container, user)


def instagram_upload(video, story, ctx=None):
    return instagram_reel(video, story, ctx or {})


def instagram_trial_upload(video, story, ctx=None):
    """The hook test: the same Reel with the other hook, as a trial Reel. Instagram shares it with followers too
    when it does well with non-followers (SS_PERFORMANCE); compare both in the weekly report."""
    ctx = ctx or {}
    video_b = ctx.get('video_b')
    if not video_b or not Path(video_b).exists():
        return {'status': 'skipped', 'note': 'no second hook version was rendered (set HOOK_TEST=true)'}
    try:
        return {**instagram_reel(Path(video_b), story, ctx, trial=True), 'hook': story.get('title_b', '')}
    except PublishError as exc:
        if 'trial' in str(exc).lower() or '(100/' in str(exc):
            return {'status': 'skipped', 'note': 'Instagram has not turned on trial Reels for this account yet (often from about 1,000 followers)'}
        raise


def carousel_upload(video, story, ctx=None):
    """5 slides (from the Reel) as an Instagram carousel: carousels get the most saves."""
    from . import media
    ctx = ctx or {}
    slides = sorted((Path(ctx.get('folder', '.')) / 'slides').glob('*.jpg'))
    if len(slides) < 2:
        return {'status': 'skipped', 'note': 'no carousel slides were made'}
    try:
        urls = media.host(slides)
    except media.MediaError as exc:
        raise PublishError(f'carousel images could not be hosted: {exc}') from None
    user = instagram_user()
    children = [instagram_call(f'{user}/media', {'image_url': u, 'is_carousel_item': 'true'})['id'] for u in urls]
    for child in children:
        instagram_wait(child, wait=4, attempts=30)
    container = instagram_call(f'{user}/media', {'media_type': 'CAROUSEL', 'children': ','.join(children),
                                                 'caption': texts(story)['caption']})['id']
    instagram_wait(container, wait=4, attempts=30)
    at = hold_until(ctx)
    if at:
        return {'status': 'queued', 'container': container, 'publish_at': at.isoformat()}
    return instagram_finish(container, user)


# --- Facebook ---------------------------------------------------------------------------------

def facebook_upload(video, story, ctx=None):
    """A Facebook Reel on the Page (FACEBOOK_PAGE_ID, FACEBOOK_PAGE_TOKEN); scheduled when ctx['publish_at']."""
    ctx = ctx or {}
    page, token = os.environ['FACEBOOK_PAGE_ID'].strip(), os.environ['FACEBOOK_PAGE_TOKEN'].strip()
    try:
        start, _ = request(f'{FB_GRAPH}/{page}/video_reels', {'upload_phase': 'start', 'access_token': token})
        data = video.read_bytes()
        request(f"{FB_RUPLOAD}/{start['video_id']}", data, {'Authorization': 'OAuth ' + token, 'offset': '0',
                                                            'file_size': str(len(data))}, timeout=600)
        fields = {'upload_phase': 'finish', 'video_id': start['video_id'], 'description': texts(story)['caption'],
                  'access_token': token}
        if ctx.get('publish_at'):
            fields.update(video_state='SCHEDULED', scheduled_publish_time=str(int(ctx['publish_at'].timestamp())))
        else:
            fields['video_state'] = 'PUBLISHED'
        request(f'{FB_GRAPH}/{page}/video_reels', fields)
    except urllib.error.HTTPError as exc:
        _, message, error = detail(exc)
        raise PublishError(f"Facebook refused ({error.get('code')}): {message}") from None
    url = f"https://www.facebook.com/reel/{start['video_id']}"
    return ({'id': start['video_id'], 'url': url, 'status': 'scheduled', 'publish_at': ctx['publish_at'].isoformat()}
            if ctx.get('publish_at') else {'id': start['video_id'], 'url': url})


UPLOADERS = {'instagram': instagram_upload, 'youtube': youtube_upload, 'facebook': facebook_upload,
             'carousel': carousel_upload, 'instagram_trial': instagram_trial_upload}


def publish(folder, video, platforms=None, video_b=None, publish_at=None):
    """Post `video` (the Reel of `folder`) to each platform once. Returns the receipt.

    `publish_at` (UTC) schedules it: YouTube and Facebook schedule natively; Instagram uploads now and is
    published by the queue workflow then. A receipt (publish.json) makes sure nothing is posted twice.
    """
    folder, video = Path(folder), Path(video)
    receipt_path = folder / 'publish.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else {'platforms': {}}
    story = json.loads((folder / 'script.json').read_text(encoding='utf-8'))
    wanted = [p for p in (platforms or configured()) if p in UPLOADERS]
    if not wanted:
        receipt['skipped'] = ('Nothing to post to yet: add INSTAGRAM_ACCESS_TOKEN (Instagram) or the three YOUTUBE_ '
                              'secrets (YouTube) to the stickman-reels repository.')
    ctx = {'folder': folder, 'video_b': video_b, 'publish_at': publish_at}
    for name in wanted:
        if receipt['platforms'].get(name, {}).get('status') in ('published', 'queued', 'scheduled'):
            continue  # never post the same Reel twice
        try:
            result = UPLOADERS[name](video, story, ctx)
            receipt['platforms'][name] = {'status': 'published', **result}
            print(f"{NAMES[name]}: {receipt['platforms'][name]['status']} {result.get('url', '')}")
        except (PublishError, urllib.error.URLError, OSError, KeyError) as exc:
            print(f'{NAMES[name]} failed: {exc}')
            receipt['platforms'][name] = {'status': 'failed', 'error': str(exc)[:500]}
        receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
    return receipt


def publish_queued(folder, now=None):
    """Publish the Instagram uploads of `folder` that were waiting for their time.

    Returns (receipt, names published, names that failed).
    """
    folder = Path(folder)
    receipt_path = folder / 'publish.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    now = now or dt.datetime.now(dt.timezone.utc)
    done, failed = [], []
    for name, result in receipt['platforms'].items():
        if result.get('status') != 'queued' or dt.datetime.fromisoformat(result['publish_at']) > now + dt.timedelta(minutes=10):
            continue
        try:
            receipt['platforms'][name] = {'status': 'published', **instagram_finish(result['container'])}
            done.append(name)
        except (PublishError, urllib.error.URLError, TimeoutError, OSError, KeyError) as exc:
            receipt['platforms'][name] = {**result, 'status': 'failed', 'error': str(exc)[:500]}
            failed.append(name)
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
    return receipt, done, failed


def posted(receipt):
    """True when the Reel went out (or is scheduled to) on at least one platform: for the weekly compilation."""
    return any(r.get('status') in ('published', 'queued', 'scheduled') for r in receipt.get('platforms', {}).values())


def waiting(receipt):
    return any(r.get('status') == 'queued' for r in receipt.get('platforms', {}).values())


def summary(story, receipt):
    ist = dt.timezone(dt.timedelta(minutes=330))
    lines = [f"📢 {story['title']}"]
    if receipt.get('skipped'):
        lines.append(receipt['skipped'])
    for name, result in receipt.get('platforms', {}).items():
        status = result.get('status')
        if status in ('queued', 'scheduled'):
            when = dt.datetime.fromisoformat(result['publish_at']).astimezone(ist).strftime('%d %b %I:%M %p')
            lines.append(f"⏰ {NAMES[name]}: goes live {when} IST (your best time)")
        elif status == 'published':
            lines.append(f"✅ {NAMES[name]}: {result.get('url', '')}" + (f"\n   {result['note']}" if result.get('note') else ''))
        elif status == 'skipped':
            lines.append(f"⏭ {NAMES[name]}: {result.get('note', 'skipped')}")
        else:
            lines.append(f"❌ {NAMES[name]}: {result.get('error', 'failed')}")
    return '\n'.join(lines)
