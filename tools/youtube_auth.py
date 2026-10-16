"""One-time YouTube sign-in: prints (or saves to GitHub) the refresh token the pipeline uploads with.

Run on your own computer:
    python tools/youtube_auth.py                 # prints the token to copy into a GitHub secret
    python tools/youtube_auth.py --save-to-github  # stores YouTube secrets with the GitHub CLI (gh)
    python tools/youtube_auth.py --save-to-github --client-file client_secret_XXXX.json  # nothing to paste

It asks for the OAuth client ID and secret from Google Cloud (Desktop app type), opens your
browser to sign in with the YouTube channel's Google account, and receives the answer on a
local 127.0.0.1 port. Only "upload videos" and "view your YouTube account" (for the weekly report) are
requested. Sign in with the Google account of the stickman channel, not the infographic one. See README.md.
"""
import argparse
import base64
import getpass
import hashlib
import http.server
import json
import os
import re
import secrets
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

# Upload Shorts, and read the channel's own numbers for the weekly report.
SCOPE = 'https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly'
CLIENT_ID = re.compile(r'^[0-9]+-[a-z0-9]+\.apps\.googleusercontent\.com$')
PASTE_TIP = ('Tip: in this terminal, paste with right-click or Ctrl+Shift+V (plain Ctrl+V types ^V). '
             'Or use --client-file with the JSON downloaded from Google Cloud.')
SIGN_IN_MINUTES = 5


def clean(value):
    """Drop whitespace, quotes and control characters a paste can bring along."""
    return ''.join(c for c in value if c.isprintable()).strip().strip('"\'')


def ask(prompt, check, hidden=False):
    for _ in range(3):
        value = clean((getpass.getpass if hidden else input)(prompt))
        problem = check(value)
        if not problem:
            return value
        print(f'{problem} {PASTE_TIP}')
    raise SystemExit('Stopped after 3 tries. Nothing was saved.')


def check_id(value):
    if not CLIENT_ID.match(value):
        return 'That is not an OAuth client ID (it looks like 1234567890-abc123.apps.googleusercontent.com).'
    return ''


def check_secret(value):
    if len(value) < 20 or ' ' in value:
        return f'That does not look like a client secret (got {len(value)} characters; they usually start with GOCSPX-).'
    return ''


def from_file(path):
    """Client ID and secret from the JSON Google Cloud lets you download for a Desktop client."""
    data = json.loads(open(path, encoding='utf-8').read())
    client = data.get('installed') or data.get('web') or {}
    if 'web' in data:
        print('Note: this is a Web client. Create a Desktop app client instead if sign-in fails with redirect_uri_mismatch.')
    if not client.get('client_id') or not client.get('client_secret'):
        raise SystemExit('That file has no client_id/client_secret. Download the JSON of a Desktop app client.')
    return client['client_id'], client['client_secret']


def sign_in(client_id, client_secret):
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    state = secrets.token_urlsafe(16)
    result = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(self.path).query))
            if query.get('state') == state:
                result.update(query)
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            done = 'code' in result
            self.wfile.write(('<h2>' + ('Signed in. You can close this tab.' if done else 'Sign-in failed.') + '</h2>').encode())

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(('127.0.0.1', 0), Handler)
    server.timeout = 5
    redirect = f'http://127.0.0.1:{server.server_port}'
    url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode({
        'client_id': client_id, 'redirect_uri': redirect, 'response_type': 'code', 'scope': SCOPE,
        'access_type': 'offline', 'prompt': 'consent', 'state': state,
        'code_challenge': challenge, 'code_challenge_method': 'S256'})
    print('Opening your browser to sign in. If it does not open, visit:\n' + url)
    print(f'Waiting up to {SIGN_IN_MINUTES} minutes. If Google shows "OAuth client was not found" (invalid_client), '
          'the client ID is wrong: press Ctrl+C and run this again.')
    webbrowser.open(url)
    deadline = time.monotonic() + SIGN_IN_MINUTES * 60
    while 'code' not in result and 'error' not in result:
        if time.monotonic() > deadline:
            raise SystemExit('No answer from the browser sign-in. Nothing was saved; run this again.')
        server.handle_request()
    if 'error' in result:
        raise SystemExit(f"Sign-in was not completed: {result['error']}. Nothing was saved.")
    body = urllib.parse.urlencode({'code': result['code'], 'client_id': client_id, 'client_secret': client_secret,
                                   'redirect_uri': redirect, 'grant_type': 'authorization_code',
                                   'code_verifier': verifier}).encode()
    try:
        with urllib.request.urlopen('https://oauth2.googleapis.com/token', body, timeout=60) as response:
            token = json.load(response)
    except urllib.error.HTTPError as exc:
        reason = json.loads(exc.read() or b'{}').get('error', exc.code)
        hint = (' The client secret is wrong: copy it again (or add a new secret) on the client page in Google Cloud.'
                if reason in ('invalid_client', 'unauthorized_client') else '')
        raise SystemExit(f'Google refused the sign-in ({reason}).{hint} Nothing was saved.') from None
    if 'refresh_token' not in token:
        raise SystemExit('Google returned no refresh token. Remove the app at myaccount.google.com/permissions and try again.')
    left = token.get('refresh_token_expires_in')
    if str(left or '').isdigit():
        # Google only sets this for sign-ins that will end, most often because the app is still in "Testing".
        print(f'\nWARNING: Google says this sign-in ends in {int(left) // 86400} days. Your Google app is probably still in '
              '"Testing". Open https://console.cloud.google.com/auth/audience, tap "Publish app" (status "In production"), '
              'then run this again so the sign-in never ends.\n')
    return token['refresh_token']


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--save-to-github', action='store_true', help='store the three YouTube secrets with gh')
    parser.add_argument('--repo', default='Raj4478/stickman-reels')
    parser.add_argument('--client-file', help='JSON downloaded from Google Cloud for the Desktop app client')
    args = parser.parse_args()
    if args.client_file:
        client_id, client_secret = from_file(args.client_file)
    else:
        print(PASTE_TIP)
        client_id = clean(os.getenv('YOUTUBE_CLIENT_ID', '')) or ask('OAuth client ID: ', check_id)
        client_secret = clean(os.getenv('YOUTUBE_CLIENT_SECRET', '')) or ask('OAuth client secret (hidden): ', check_secret, hidden=True)
    for problem in (check_id(client_id), check_secret(client_secret)):
        if problem:
            raise SystemExit(problem + ' Nothing was saved.')
    print(f'Using client {client_id[:12]}... and a {len(client_secret)}-character secret starting {client_secret[:7]}...')
    refresh = sign_in(client_id, client_secret)
    if args.save_to_github:
        for name, value in (('YOUTUBE_CLIENT_ID', client_id), ('YOUTUBE_CLIENT_SECRET', client_secret),
                            ('YOUTUBE_REFRESH_TOKEN', refresh)):
            subprocess.run(['gh', 'secret', 'set', name, '--repo', args.repo], input=value.encode(), check=True)
        print('Saved YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET and YOUTUBE_REFRESH_TOKEN as GitHub secrets.')
        print('Reminder: keep the Google app "In production" (console.cloud.google.com/auth/audience); in "Testing" '
              'Google ends the sign-in after 7 days. A daily check warns you before that happens.')
    else:
        print('\nAdd this as the GitHub Actions secret YOUTUBE_REFRESH_TOKEN (keep it private):\n' + refresh)


if __name__ == '__main__':
    main()
