"""Public links for carousel images, which Instagram fetches by URL (Reels upload directly; images cannot).

Images are stored for 2 days in a Cloudflare Workers KV namespace ("stickman-media", made by the bot's
deploy) and served by the bot Worker at /m/<random key>. Free tier; needs CLOUDFLARE_ACCOUNT_ID and a
CLOUDFLARE_API_TOKEN that may edit Workers KV.
"""
import json
import os
import secrets
import urllib.error
import urllib.request

NAMESPACE = 'stickman-media'
WORKER = 'stickman-reels-bot'
API = 'https://api.cloudflare.com/client/v4/accounts/{account}/'
TTL = 2 * 24 * 3600


class MediaError(RuntimeError):
    pass


def configured():
    return bool(os.getenv('CLOUDFLARE_ACCOUNT_ID', '').strip() and os.getenv('CLOUDFLARE_API_TOKEN', '').strip())


def call(path, data=None, method=None, content_type='application/json'):
    url = API.format(account=os.environ['CLOUDFLARE_ACCOUNT_ID'].strip()) + path
    request = urllib.request.Request(url, data=data, method=method, headers={
        'Authorization': 'Bearer ' + os.environ['CLOUDFLARE_API_TOKEN'].strip(), 'Content-Type': content_type})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.load(response)
    except urllib.error.HTTPError as exc:
        raise MediaError(f'Cloudflare refused {path.split("?")[0]} (HTTP {exc.code}); the token needs Workers KV Storage: Edit') from None
    if not body.get('success', True):
        raise MediaError(f'Cloudflare: {body.get("errors")}')
    return body.get('result')


def namespace_id():
    for ns in call('storage/kv/namespaces?per_page=100') or []:
        if ns.get('title') == NAMESPACE:
            return ns['id']
    raise MediaError('No "stickman-media" storage yet: run the Deploy bot workflow once (it creates it).')


def base_url():
    sub = (call('workers/subdomain') or {}).get('subdomain')
    if not sub:
        raise MediaError('No workers.dev subdomain on this Cloudflare account')
    return f'https://{WORKER}.{sub}.workers.dev'


def host(paths):
    """Upload JPEG files and return their public URLs (valid for 2 days)."""
    ns, base = namespace_id(), base_url()
    urls = []
    for path in paths:
        key = secrets.token_hex(16) + '.jpg'
        call(f'storage/kv/namespaces/{ns}/values/{key}?expiration_ttl={TTL}', data=open(path, 'rb').read(), method='PUT',
             content_type='application/octet-stream')
        urls.append(f'{base}/m/{key}')
    return urls
