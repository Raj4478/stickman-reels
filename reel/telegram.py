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


def buttons(rows):
    """reply_markup form value for an inline keyboard: rows of (label, callback data)."""
    return json.dumps({'inline_keyboard': [[{'text': t, 'callback_data': d} for t, d in row] for row in rows]}, ensure_ascii=False)


COPY_LIMIT = 256  # Telegram's limit for the text a copy button holds


def copy_row(copy):
    """Buttons that copy the caption and the hashtags to the clipboard (Telegram does it; no bot needed)."""
    row = []
    if copy and 0 < len(copy['caption']) <= COPY_LIMIT:
        row.append({'text': '📋 Copy caption', 'copy_text': {'text': copy['caption']}})
    if copy and 0 < len(copy['hashtags']) <= COPY_LIMIT:
        row.append({'text': '#️⃣ Copy hashtags', 'copy_text': {'text': copy['hashtags']}})
    return row


def review_buttons(run, n, copy=None, actions=True):
    """Under each Reel: post it, make it again (same lesson) or skip it (the bot, bot/src.js, handles those taps),
    and copy its caption and hashtags. `actions=False` (AUTO_POST) keeps only the copy buttons."""
    rows = []
    if run and actions:
        rows += [[{'text': '✅ Post', 'callback_data': f'post:{run}:{n}'}, {'text': '🔁 Make again', 'callback_data': f'again:{run}:{n}'}],
                 [{'text': '🗑 Skip', 'callback_data': f'skip:{run}:{n}'}]]
    if copy_row(copy):
        rows.append(copy_row(copy))
    return json.dumps({'inline_keyboard': rows}, ensure_ascii=False) if rows else None


def copy_message(copy):
    """For a caption longer than a copy button holds: the caption and hashtags as tap-to-copy blocks."""
    from html import escape
    if not copy or len(copy['caption']) <= COPY_LIMIT:
        return None
    return ('📋 Tap a block to copy it\n\n<b>Caption</b>\n<pre>' + escape(copy['caption']) + '</pre>\n\n<b>Hashtags</b>\n<pre>'
            + escape(copy['hashtags']) + '</pre>')


def send_message(text, reply_markup=None, html=False):
    token, chat = os.getenv('TELEGRAM_BOT_TOKEN', '').strip(), os.getenv('TELEGRAM_CHAT_ID', '').strip()
    if not token or not chat:
        print(text)
        return None
    body = json.dumps({'chat_id': chat, 'text': text[:4000], 'disable_web_page_preview': True, **({'parse_mode': 'HTML'} if html else {}),
                       **({'reply_markup': json.loads(reply_markup)} if reply_markup else {})}).encode()
    request = urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMessage', data=body,
                                     headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response).get('ok')
