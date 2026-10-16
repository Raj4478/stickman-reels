"""Send a finished Reel to the owner's Telegram chat (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)."""
import json
import os
import uuid
import urllib.request
from pathlib import Path


def send_video(path, caption):
    token, chat = os.getenv('TELEGRAM_BOT_TOKEN', '').strip(), os.getenv('TELEGRAM_CHAT_ID', '').strip()
    if not token or not chat:
        print('Telegram is not set up (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID); skipping delivery')
        return False
    boundary = uuid.uuid4().hex
    fields = {'chat_id': chat, 'caption': caption[:1000], 'supports_streaming': 'true'}
    body = b''.join(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
                    for k, v in fields.items())
    body += (f'--{boundary}\r\nContent-Disposition: form-data; name="video"; filename="{Path(path).name}"\r\n'
             'Content-Type: video/mp4\r\n\r\n').encode() + Path(path).read_bytes() + f'\r\n--{boundary}--\r\n'.encode()
    request = urllib.request.Request(f'https://api.telegram.org/bot{token}/sendVideo', data=body,
                                     headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    with urllib.request.urlopen(request, timeout=300) as response:
        ok = json.load(response).get('ok')
    print('Sent to Telegram' if ok else 'Telegram did not accept the video')
    return bool(ok)
