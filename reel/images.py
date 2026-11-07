"""Paint the pictures of a storybook Reel (reel/storybook.py) with Cloudflare Workers AI, free tier.

1. A reference portrait of every character (one look, plain background, 496x496: FLUX.2 takes references under
   512x512).
2. Every line's picture, 768x1344 (9:16), with the portraits of the people in it attached as reference images, so
   each person keeps the same face, hair and clothes all the way through. The same story seed keeps the style steady.

Models: @cf/black-forest-labs/flux-2-klein-4b first (good storybook quality, up to 4 references, ~125 of the 10,000
free daily neurons a picture, so about three Reels a day), then @cf/black-forest-labs/flux-1-schnell (no references;
the written looks and the seed keep people close). Needs CLOUDFLARE_ACCOUNT_ID and a CLOUDFLARE_API_TOKEN with
"Workers AI: Read" and "Workers AI: Edit" (the same token the bot uses, with that permission added).
"""
import base64
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

API = 'https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}'
KLEIN = '@cf/black-forest-labs/flux-2-klein-4b'
SCHNELL = '@cf/black-forest-labs/flux-1-schnell'
SIZE = (768, 1344)  # 9:16, multiples of 16
REF = 496  # FLUX.2 references must be smaller than 512x512

# The channel's painted look, in every prompt (no copying any channel or artist: a generic description of the style)
STYLE = ('warm hand-painted Indian storybook illustration, soft gouache and watercolour texture, clean dark ink '
         'outlines, expressive friendly cartoon faces with big eyes, rich detailed background, golden warm light, '
         'cinematic composition, high detail, gentle film grain')
NO_TEXT = 'no text, no letters, no words, no captions, no watermark, no signature, no logo'
SHOT_WORDS = {'wide': 'wide establishing shot', 'medium': 'medium shot', 'close': 'close-up, emotional',
              'detail': 'close detail shot'}


class ImageError(Exception):
    pass


def configured():
    return bool(os.getenv('CLOUDFLARE_ACCOUNT_ID', '').strip() and os.getenv('CLOUDFLARE_API_TOKEN', '').strip())


def _multipart(fields, files):
    boundary = uuid.uuid4().hex
    body = b''
    for name, value in fields.items():
        body += f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode('utf-8')
    for name, data in files.items():
        body += (f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{name}.png"\r\n'
                 f'Content-Type: {kind(data)}\r\n\r\n').encode('utf-8') + data + b'\r\n'
    return body + f'--{boundary}--\r\n'.encode('utf-8'), f'multipart/form-data; boundary={boundary}'


def kind(data):
    return 'image/png' if data[:4] == b'\x89PNG' else 'image/jpeg'


def _image_of(raw, content_type):
    """The picture bytes from a Workers AI reply: a raw image, or JSON with a base64 `result.image`."""
    if content_type.startswith('image/'):
        return raw
    try:
        body = json.loads(raw)
    except ValueError:
        raise ImageError('Workers AI sent something that is neither an image nor JSON') from None
    if not body.get('success', True):
        raise ImageError('; '.join(f"{e.get('code')}: {e.get('message')}" for e in body.get('errors', [])) or 'request refused')
    image = (body.get('result') or {}).get('image') or body.get('image')
    if not image:
        raise ImageError('Workers AI answered without an image')
    return base64.b64decode(image)


def run(model, prompt, size, seed, refs=(), timeout=120):
    """One picture from Workers AI. FLUX.2 takes multipart (with up to 4 references); FLUX.1 schnell takes JSON."""
    url = API.format(account=os.environ['CLOUDFLARE_ACCOUNT_ID'].strip(), model=model)
    headers = {'Authorization': 'Bearer ' + os.environ['CLOUDFLARE_API_TOKEN'].strip()}
    if model == SCHNELL:
        data, headers['Content-Type'] = json.dumps({'prompt': prompt[:2048], 'steps': 8, 'seed': seed}).encode(), 'application/json'
    else:
        fields = {'prompt': prompt[:2048], 'width': size[0], 'height': size[1], 'seed': seed}
        data, headers['Content-Type'] = _multipart(fields, {f'input_image_{k}': r for k, r in enumerate(refs[:4])})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=timeout) as resp:
                return _image_of(resp.read(), resp.headers.get('Content-Type', ''))
        except urllib.error.HTTPError as exc:
            text = exc.read()[:400].decode('utf-8', 'replace')
            if exc.code in (401, 403):
                raise ImageError('the Cloudflare token cannot run Workers AI: add "Workers AI: Read" and "Workers AI: Edit" '
                                 'to CLOUDFLARE_API_TOKEN (My Profile > API Tokens > Edit)') from None
            if exc.code == 429 or 'neuron' in text.lower() or 'limit' in text.lower():
                raise ImageError(f'the free Workers AI allowance is used up for today ({exc.code})') from None
            if attempt == 2 or exc.code < 500:
                raise ImageError(f'Workers AI {model} failed ({exc.code}): {text}') from None
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == 2:
                raise ImageError(f'Workers AI could not be reached: {exc}') from None
        time.sleep(4 * (attempt + 1))
    raise ImageError('Workers AI failed')


def seed_of(text):
    return int(hashlib.sha256(text.encode('utf-8')).hexdigest()[:8], 16) % 2_000_000_000


def portrait_prompt(person, setting):
    return (f"{STYLE}. Character reference portrait of {person['look']}. Upper body, facing the viewer, a calm friendly "
            f"expression, plain soft warm background. Setting of the story: {setting}. {NO_TEXT}.")


def scene_prompt(line, people, setting, refs):
    """The picture prompt: the style, the shot, what happens, who is who (by reference image), the world."""
    cast = [p for p in people if p['id'] in line.get('cast', [])][:4]
    who = '; '.join(f"{p['id']} is {p['look']}" + (f" (looks exactly like reference image {k})" if k < refs else '')
                    for k, p in enumerate(cast))
    text = line['image']
    for p in cast:  # the ids in the prompt become descriptions the model understands
        text = text.replace(p['id'], f"{p['id']} ({p['look'].split(',')[0]})")
    return (f"{text}. {SHOT_WORDS.get(line.get('shot'), 'medium shot')}, vertical 9:16 frame, a natural pose and action "
            "that fits the moment. "
            + (f"People: {who}. Keep each person's face, hair and clothes exactly as described"
               + ("; take only that from the reference images, never their pose, framing or background. " if refs else ". ")
               if who else '')
            + f"{STYLE}. World of the story (region, era, colours): {setting}. {NO_TEXT}.")


def paint(script, folder):
    """Paint every picture of `script` into folder/img/; returns (relative file names for the hook, every scene and the
    moral, a record). Raises ImageError when no picture at all could be made."""
    folder = Path(folder) / 'img'
    folder.mkdir(parents=True, exist_ok=True)
    if not configured():
        raise ImageError('CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN are needed to paint the pictures')
    people, setting = script.get('characters', []), script.get('setting', '')
    base = seed_of(script.get('title', '') + script.get('topic', ''))
    record = {'model': KLEIN, 'pictures': 0, 'fallback': 0}
    refs = {}
    for k, person in enumerate(people):
        try:
            refs[person['id']] = run(KLEIN, portrait_prompt(person, setting), (REF, REF), base + 7 * k)
            (folder / f"ref-{person['id']}.{ext(refs[person['id']])}").write_bytes(refs[person['id']])
        except ImageError as exc:
            if 'allowance' in str(exc) or 'token' in str(exc):
                raise
            print(f"::warning::No reference portrait for {person['id']}: {exc}")
    lines = [{'image': script['hook_image'], 'cast': script.get('hook_cast', []), 'shot': script.get('hook_shot')},
             *script['scenes'],
             {'image': script['lesson_image'], 'cast': script.get('lesson_cast', []), 'shot': script.get('lesson_shot')}]
    names = []
    for i, line in enumerate(lines):
        mine = [refs[c] for c in line.get('cast', []) if c in refs][:4]
        try:
            data = run(KLEIN, scene_prompt(line, people, setting, len(mine)), SIZE, base + 101 + i, mine)
        except ImageError as exc:
            if 'token' in str(exc):
                raise
            print(f'::warning::Picture {i} with FLUX.2 failed ({exc}); trying FLUX.1 schnell')
            try:
                data = run(SCHNELL, scene_prompt(line, people, setting, 0), SIZE, base + 101 + i)
                record['fallback'] += 1
            except ImageError as again:
                print(f'::warning::Picture {i} failed again ({again}); the line keeps the previous picture')
                names.append(None)
                continue
        name = f'img/{i:02d}.{ext(data)}'
        (folder.parent / name).write_bytes(data)
        names.append(name)
        record['pictures'] += 1
    if not record['pictures']:
        raise ImageError('no picture could be painted')
    if names[0] is None:  # the opening must have a picture: borrow the first one that worked
        names[0] = next(n for n in names if n)
    return names, record


def ext(data):
    return 'png' if data[:4] == b'\x89PNG' else 'jpg'
