"""Gemini calls (free tier): JSON text for the script, speech for the Hindi narration and a look at frames.

Keys come from GEMINI_API_KEY, GEMINI_API_KEY_2 and GEMINI_API_KEY_3. When a key's daily quota is used
up (HTTP 429) the next key is tried, then the next model. When every Gemini key and model fails, text falls
back to free backups if their keys are set: Groq (GROQ_API_KEY) then OpenRouter's free models
(OPENROUTER_API_KEY). Speech falls back to free Microsoft Edge voices in reel/voice.py. Every backup used is
recorded in USED and shown in Telegram. Keys are never printed or written to disk.
"""
import base64
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

KEY_VARIABLES = ('GEMINI_API_KEY', 'GEMINI_API_KEY_2', 'GEMINI_API_KEY_3')
TEXT_MODELS = ('gemini-3.8-flash', 'gemini-3.5-flash-lite')
SPEECH_MODELS = ('gemini-3.8-flash-tts', 'gemini-3.8-flash-lite-tts')
URL = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'


# Free backups for text, tried in order after Gemini: (name, key variable, URL, default models).
# GROQ_MODEL / OPENROUTER_MODEL put another model first.
BACKUPS = (
    ('Groq', 'GROQ_API_KEY', 'https://api.groq.com/openai/v1/chat/completions', ('llama-3.3-70b-versatile', 'openai/gpt-oss-120b')),
    ('OpenRouter', 'OPENROUTER_API_KEY', 'https://openrouter.ai/api/v1/chat/completions',
     ('meta-llama/llama-3.3-70b-instruct:free', 'deepseek/deepseek-chat-v3.1:free')),
)
USED = []  # backups this run used: {'service', 'reason'}


class GeminiError(RuntimeError):
    pass


def note(service, reason):
    USED.append({'service': service, 'reason': str(reason)[:200]})
    print(f'::warning::Backup used: {service} ({reason})')


def keys():
    return [os.environ[name].strip() for name in KEY_VARIABLES if os.environ.get(name, '').strip()]


def models(kind):
    """The override from GEMINI_MODEL / GEMINI_TTS_MODEL first, then the built-in free models."""
    override = os.getenv('GEMINI_TTS_MODEL' if kind == 'speech' else 'GEMINI_MODEL', '').strip()
    return list(dict.fromkeys([m for m in [override, *(SPEECH_MODELS if kind == 'speech' else TEXT_MODELS)] if m]))


def post(model, key, body, timeout=180):
    request = urllib.request.Request(URL.format(model=model), data=json.dumps(body).encode(),
                                     headers={'x-goog-api-key': key, 'Content-Type': 'application/json'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code in (500, 502, 503, 504) and attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))


MAX_WAIT = 65  # seconds: the longest Gemini "try again in Ns" worth waiting for before moving on


def limit_info(exc):
    """(seconds to wait, whether the daily quota is used up) from a 429 answer."""
    try:
        error = json.loads(exc.read() or b'{}').get('error', {})
    except ValueError:
        return None, False
    daily = 'PerDay' in json.dumps(error) or 'per day' in error.get('message', '').lower()
    for item in error.get('details', []):
        found = re.match(r'([\d.]+)s', str(item.get('retryDelay', '')))
        if found:
            return float(found.group(1)), daily
    found = re.search(r'retry in ([\d.]+)\s*s', error.get('message', ''))
    return (float(found.group(1)) if found else None), daily


def refusal(exc):
    """Gemini's own words for a 400/404 answer, e.g. "Multi-speaker voice config is not supported"."""
    try:
        return str(json.loads(exc.read() or b'{}').get('error', {}).get('message', ''))[:300]
    except (ValueError, OSError):
        return ''


def call(kind, body):
    """Run `body` on the first model and key that answer. Returns (response, model).

    Gemini always comes first and gets every chance: each key on each model; a per-minute limit (429 with
    "retry in Ns") is waited out once per key when it is under MAX_WAIT; a daily limit moves on to the next
    key; brief outages (5xx, timeouts) move on to the next model. Only when all of that fails does the caller
    use a backup.
    """
    available = keys()
    if not available:
        raise GeminiError('No Gemini API key: add the GEMINI_API_KEY secret.')
    last = None
    wait_cap = float(os.getenv('GEMINI_MAX_WAIT', MAX_WAIT) or MAX_WAIT)
    for model in models(kind):
        for index, key in enumerate(available):
            waited = False
            while True:
                try:
                    return post(model, key, body), model
                except urllib.error.HTTPError as exc:
                    last = f'HTTP {exc.code} from {model}'
                    if exc.code == 429:
                        delay, daily = limit_info(exc)
                        if not daily and not waited and delay is not None and delay <= wait_cap:
                            print(f'Gemini {kind}: key {index + 1} hit the per-minute limit on {model}; waiting {delay:.0f}s')
                            time.sleep(delay + 1)
                            waited = True
                            continue
                        print(f'Gemini {kind}: key {index + 1} has used its {"daily " if daily else ""}quota on {model}; trying the next one')
                        break
                    if exc.code in (400, 404):
                        # this model does not take this request: say why (Gemini's message never holds the key)
                        reason = refusal(exc)
                        print(f'Gemini {kind}: {model} refused the request (HTTP {exc.code}): {reason}')
                        last += f': {reason[:160]}' if reason else ''
                        break
                    if exc.code in (500, 502, 503, 504):
                        break  # still failing after retries: try the next key or model
                    raise GeminiError(f'Gemini refused the {kind} request ({last}). Check the GEMINI_API_KEY secret.') from None
                except (urllib.error.URLError, TimeoutError) as exc:
                    last = f'{model}: {getattr(exc, "reason", exc)}'
                    break
            if last and last.startswith('HTTP 40') and not last.startswith('HTTP 429'):
                break  # 400/404 is about the model, not the key: skip its other keys
    raise GeminiError(f'Gemini {kind} failed on every key and model ({last}). Free quotas reset daily.')


def parts(response):
    return response.get('candidates', [{}])[0].get('content', {}).get('parts', [])


def json_call(prompt, schema, temperature=1.0):
    """JSON answer to `prompt` following `schema`: Gemini first, then the free text backups."""
    body = {'contents': [{'parts': [{'text': prompt}]}],
            'generationConfig': {'temperature': temperature, 'responseMimeType': 'application/json',
                                 'responseJsonSchema': schema}}
    try:
        response, model = call('text', body)
        text = ''.join(p.get('text', '') for p in parts(response))
        try:
            return json.loads(text), model
        except json.JSONDecodeError:
            raise GeminiError(f'{model} returned text that is not JSON.') from None
    except (GeminiError, urllib.error.URLError, TimeoutError) as exc:
        return backup_json(prompt, schema, temperature, exc)


def loose_json(text):
    """The JSON object inside a model's answer (some wrap it in code fences or a sentence)."""
    text = text.strip()
    start, end = text.find('{'), text.rfind('}')
    return json.loads(text[start:end + 1] if start >= 0 and end > start else text)


def backup_json(prompt, schema, temperature, reason):
    instruction = (prompt + '\n\nAnswer with ONE JSON object only (no prose, no code fences) that matches this JSON '
                   'schema exactly; use only the enum values it lists:\n' + json.dumps(schema, ensure_ascii=False))
    last = reason
    for name, variable, url, defaults in BACKUPS:
        key = os.getenv(variable, '').strip()
        if not key:
            continue
        override = os.getenv(variable.replace('API_KEY', 'MODEL'), '').strip()
        for model in dict.fromkeys([m for m in (override, *defaults) if m]):
            body = {'model': model, 'temperature': min(temperature, 1.0), 'response_format': {'type': 'json_object'},
                    'messages': [{'role': 'user', 'content': instruction}]}
            request = urllib.request.Request(url, data=json.dumps(body).encode(), headers={
                'Authorization': f'Bearer {key}', 'Content-Type': 'application/json', 'User-Agent': 'stickman-reels'})
            try:
                with urllib.request.urlopen(request, timeout=180) as response:
                    answer = json.load(response)
                result = loose_json(answer['choices'][0]['message']['content'])
            except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError) as exc:
                last = f'{name} {model}: {getattr(exc, "code", exc)}'
                continue
            note(f'{name} ({model})', f'Gemini text failed: {reason}')
            return result, f'{name.lower()}:{model}'
    raise GeminiError(f'Gemini and every text backup failed ({last}). Add GROQ_API_KEY or OPENROUTER_API_KEY for free backups.')


def vision_json(prompt, images, schema):
    """JSON answer about some JPEG frames (Gemini only; callers treat a failure as "not checked")."""
    image_parts = [{'inlineData': {'mimeType': 'image/jpeg', 'data': base64.b64encode(Path(i).read_bytes()).decode()}}
                   for i in images]
    body = {'contents': [{'parts': [*image_parts, {'text': prompt}]}],
            'generationConfig': {'temperature': 0.2, 'responseMimeType': 'application/json', 'responseJsonSchema': schema}}
    response, model = call('text', body)
    return json.loads(''.join(p.get('text', '') for p in parts(response))), model


def speech_call(prompt, voice, speakers=None):
    """Audio for `prompt`: one `voice`, or {speaker name: voice} (at most two) for a dialogue.

    A dialogue's `prompt` is a list of (speaker, line, style) turns: the 3.8 speech models only take a
    dialogue as one part per turn, each tagged with its speaker (and an optional delivery style).
    """
    config = ({'multiSpeakerVoiceConfig': {'speakerVoiceConfigs': [
        {'speaker': name, 'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': v}}} for name, v in speakers.items()]}}
        if speakers else {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': voice}}})
    if speakers:
        content = [{'text': line, 'speechMetadata': {'speaker': who, **({'style': style} if style else {})}}
                   for who, line, style in prompt]
    else:
        content = [{'text': prompt}]
    body = {'contents': [{'parts': content}],
            'generationConfig': {'responseModalities': ['AUDIO'], 'speechConfig': config}}
    response, model = call('speech', body)
    audio = next((p['inlineData'] for p in parts(response) if 'inlineData' in p), None)
    if not audio:
        raise GeminiError(f'{model} returned no audio.')
    return audio, model
