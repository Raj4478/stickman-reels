"""Send a finished Reel to the owner's Telegram chat (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)."""
import json
import os
import uuid
import urllib.request
from pathlib import Path


def send_file(method, field, path, content_type, caption, extra=None):
    """Upload one file with `method` (sendVideo, sendPhoto...). Returns the API result or None."""
    token, chat = os.getenv('TELEGRAM_BOT_TOKEN', '').strip(), os.getenv('TELEGRAM_CHAT_ID', '').strip()
    if not token or not chat:
        print('Telegram is not set up (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID); skipping delivery')
        return None
    boundary = uuid.uuid4().hex
    fields = {'chat_id': chat, 'caption': caption[:1000], **(extra or {})}
    if method == 'sendVideo':
        fields['supports_streaming'] = 'true'
    body = b''.join(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
                    for k, v in fields.items())
    body += (f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{Path(path).name}"\r\n'
             f'Content-Type: {content_type}\r\n\r\n').encode() + Path(path).read_bytes() + f'\r\n--{boundary}--\r\n'.encode()
    request = urllib.request.Request(f'https://api.telegram.org/bot{token}/{method}', data=body,
                                     headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    with urllib.request.urlopen(request, timeout=300) as response:
        reply = json.load(response)
    print(f'Sent {Path(path).name} to Telegram' if reply.get('ok') else f'Telegram refused {Path(path).name}')
    return reply.get('result') if reply.get('ok') else None


def send_video(path, caption):
    return send_file('sendVideo', 'video', path, 'video/mp4', caption) is not None
