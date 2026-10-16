"""Post a finished Reel to Instagram (Reels) and YouTube (Shorts), each only when its secrets are set.

Instagram: INSTAGRAM_ACCESS_TOKEN (long-lived, 60 days) and optionally INSTAGRAM_USER_ID. The video is sent
with Instagram's resumable upload, so it needs no public hosting; the cover is the hook frame (thumb_offset).
YouTube: YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET and YOUTUBE_REFRESH_TOKEN from tools/youtube_auth.py.

Adapted from the infographic repo's publisher. A receipt (publish.json) records what went where, so a Reel is
never posted twice to the same place.
"""
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
NAMES = {'instagram': 'Instagram', 'youtube': 'YouTube Shorts'}


class PublishError(RuntimeError):
    pass


def configured():
    names = []
    if os.getenv('INSTAGRAM_ACCESS_TOKEN', '').strip():
        names.append('instagram')
    if all(os.getenv(k, '').strip() for k in ('YOUTUBE_CLIENT_ID', 'YOUTUBE_CLIENT_SECRET', 'YOUTUBE_REFRESH_TOKEN')):
        names.append('youtube')
    return names


def request(url, data=None, headers=None, method=None, timeout=120):
    body = data if isinstance(data, (bytes, type(None))) else (
        json.dumps(data).encode() if headers and 'application/json' in headers.get('Content-Type', '')
        else urllib.parse.urlencode(data).encode())
    for attempt in range(3):
        req = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw = response.read()
                return (json.loads(raw) if raw.strip().startswith(b'{') else {}), response.headers
        except urllib.error.HTTPError as exc:
            if exc.code not in (500, 502, 503, 504) or attempt == 2:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == 2:
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


def texts(story):
    """Caption, YouTube title, description and tags for a script."""
    tags = story.get('hashtags') or []
    part = f" (भाग {story['part']})" if story.get('part') else ''
    caption = '\n\n'.join(x for x in (story['title'] + part, story.get('instagram_caption') or story['lesson'],
                                      story.get('ask', ''), ' '.join(tags + ['#stickman', '#hindi'])) if x)
    title = f"{story['title']}{part} | {story['lesson']}"
    title = (title if len(title) <= 90 else story['title'] + part)[:90] + ' #shorts'
    description = '\n\n'.join(x for x in (story.get('instagram_caption') or '', 'सीख: ' + story['lesson'], story.get('ask', ''),
                                          ' '.join(tags + ['#shorts', '#stickman'])) if x)
    return {'caption': caption[:2200], 'title': title, 'description': description[:4900],
            'tags': [t.lstrip('#') for t in tags][:15] + ['stickman', 'hindi', 'life lessons']}


# --- YouTube ---------------------------------------------------------------------------------

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
    return token['access_token']


def youtube_upload(video, story):
    token = youtube_token()
    meta = texts(story)
    privacy = os.getenv('YOUTUBE_PRIVACY', '').strip() or 'public'
    body = {'snippet': {'title': meta['title'], 'description': meta['description'], 'tags': meta['tags'], 'categoryId': '22',
                        'defaultLanguage': 'hi', 'defaultAudioLanguage': 'hi'},
            'status': {'privacyStatus': privacy, 'selfDeclaredMadeForKids': False, 'embeddable': True}}
    size = video.stat().st_size
    try:
        _, headers = request('https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status',
                             body, {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json; charset=UTF-8',
                                    'X-Upload-Content-Type': 'video/mp4', 'X-Upload-Content-Length': str(size)})
        result, _ = request(headers['Location'], video.read_bytes(),
                            {'Authorization': 'Bearer ' + token, 'Content-Type': 'video/mp4'}, method='PUT', timeout=600)
    except urllib.error.HTTPError as exc:
        reason, message, _ = detail(exc)
        if reason in ('quotaExceeded', 'rateLimitExceeded', 'userRateLimitExceeded', 'uploadLimitExceeded'):
            raise PublishError(f'YouTube limit reached ({reason}); it resets daily. Tap Post again tomorrow.') from None
        if reason == 'youtubeSignupRequired':
            raise PublishError('This Google account has no YouTube channel yet: create it at youtube.com, then post again.') from None
        raise PublishError(f'YouTube refused the upload ({reason or exc.code}): {message}') from None
    if not result.get('id'):
        raise PublishError('YouTube accepted the upload but returned no video ID')
    actual = result.get('status', {}).get('privacyStatus', privacy)
    note = ('YouTube kept it private: uploads from an unaudited Google Cloud project stay private until it passes the free '
            'API audit. Make it public in YouTube Studio meanwhile.') if actual != privacy else ''
    return {'id': result['id'], 'url': f"https://youtube.com/shorts/{result['id']}", 'privacy': actual, 'note': note}


# --- Instagram -------------------------------------------------------------------------------

def instagram_call(path, fields=None, method='POST'):
    params = {**(fields or {}), 'access_token': os.environ['INSTAGRAM_ACCESS_TOKEN'].strip()}
    try:
        if method == 'GET':
            return request(f'{GRAPH}/{path}?' + urllib.parse.urlencode(params))[0]
        return request(f'{GRAPH}/{path}', params)[0]
    except urllib.error.HTTPError as exc:
        _, message, error = detail(exc)
        if error.get('code') == 190:
            raise PublishError('Instagram token expired or invalid: create a new long-lived token (60 days) and replace '
                               'the INSTAGRAM_ACCESS_TOKEN secret.') from None
        raise PublishError(f"Instagram refused ({error.get('code')}/{error.get('error_subcode')}): {message}") from None


def instagram_user():
    return os.getenv('INSTAGRAM_USER_ID', '').strip() or str(instagram_call('me', {'fields': 'user_id'}, 'GET')['user_id'])


def instagram_upload(video, story, wait=10, attempts=36):
    user = instagram_user()
    container = instagram_call(f'{user}/media', {'media_type': 'REELS', 'upload_type': 'resumable', 'share_to_feed': 'true',
                                                 'caption': texts(story)['caption'], 'thumb_offset': str(COVER_MS)})['id']
    data = video.read_bytes()
    try:
        request(f'{RUPLOAD}/{container}', data, {'Authorization': 'OAuth ' + os.environ['INSTAGRAM_ACCESS_TOKEN'].strip(),
                                                 'offset': '0', 'file_size': str(len(data))}, timeout=600)
    except urllib.error.HTTPError as exc:
        raise PublishError(f'Instagram upload failed (HTTP {exc.code})') from None
    for _ in range(attempts):
        status = instagram_call(container, {'fields': 'status_code,status'}, 'GET')
        if status.get('status_code') == 'FINISHED':
            break
        if status.get('status_code') in ('ERROR', 'EXPIRED'):
            raise PublishError(f"Instagram could not process the video: {status.get('status', status.get('status_code'))}")
        time.sleep(wait)
    else:
        raise PublishError('Instagram was still processing the video after 6 minutes; nothing was published. Tap Post again later.')
    media = instagram_call(f'{user}/media_publish', {'creation_id': container})['id']
    link = instagram_call(media, {'fields': 'permalink'}, 'GET').get('permalink', '')
    return {'id': media, 'url': link}


UPLOADERS = {'instagram': instagram_upload, 'youtube': youtube_upload}


def publish(folder, video, platforms=None):
    """Post `video` (the Reel of `folder`) to each configured platform once. Returns the receipt."""
    folder, video = Path(folder), Path(video)
    receipt_path = folder / 'publish.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else {'platforms': {}}
    story = json.loads((folder / 'script.json').read_text(encoding='utf-8'))
    wanted = [p for p in (platforms or configured()) if p in UPLOADERS]
    if not wanted:
        receipt['skipped'] = ('Nothing to post to yet: add INSTAGRAM_ACCESS_TOKEN (Instagram) or the three YOUTUBE_ '
                              'secrets (YouTube) to the stickman-reels repository.')
    for name in wanted:
        if receipt['platforms'].get(name, {}).get('status') == 'published':
            continue  # never post the same Reel twice
        try:
            receipt['platforms'][name] = {'status': 'published', **UPLOADERS[name](video, story)}
            print(f"Published to {NAMES[name]}: {receipt['platforms'][name].get('url', '')}")
        except (PublishError, urllib.error.URLError, OSError, KeyError) as exc:
            print(f'{NAMES[name]} failed: {exc}')
            receipt['platforms'][name] = {'status': 'failed', 'error': str(exc)[:500]}
        receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
    return receipt


def summary(story, receipt):
    lines = [f"📢 {story['title']}"]
    if receipt.get('skipped'):
        lines.append(receipt['skipped'])
    for name, result in receipt.get('platforms', {}).items():
        if result.get('status') == 'published':
            lines.append(f"✅ {NAMES[name]}: {result.get('url', '')}" + (f"\n   {result['note']}" if result.get('note') else ''))
        else:
            lines.append(f"❌ {NAMES[name]}: {result.get('error', 'failed')}")
    return '\n'.join(lines)
