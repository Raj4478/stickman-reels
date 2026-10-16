"""Gemini calls (free tier): JSON text for the script and speech for the Hindi narration.

Keys come from GEMINI_API_KEY, GEMINI_API_KEY_2 and GEMINI_API_KEY_3. When a key's daily quota is used
up (HTTP 429) the next key is tried, then the next model. Keys are never printed or written to disk.
"""
import json
import os
import time
import urllib.error
import urllib.request

KEY_VARIABLES = ('GEMINI_API_KEY', 'GEMINI_API_KEY_2', 'GEMINI_API_KEY_3')
TEXT_MODELS = ('gemini-3.8-flash', 'gemini-3.5-flash-lite')
SPEECH_MODELS = ('gemini-3.8-flash-tts', 'gemini-3.8-flash-lite-tts')
URL = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'


class GeminiError(RuntimeError):
    pass


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


def call(kind, body):
    """Run `body` on the first model and key that answer. Returns (response, model)."""
    available = keys()
    if not available:
        raise GeminiError('No Gemini API key: add the GEMINI_API_KEY secret.')
    last = None
    for model in models(kind):
        for index, key in enumerate(available):
            try:
                return post(model, key, body), model
            except urllib.error.HTTPError as exc:
                last = f'HTTP {exc.code} from {model}'
                if exc.code == 429:
                    print(f'Gemini {kind}: key {index + 1} has used its daily quota on {model}; trying the next one')
                    continue
                if exc.code in (400, 404):
                    break  # this model is not offered to the key: try the next model
                raise GeminiError(f'Gemini refused the {kind} request ({last}). Check the GEMINI_API_KEY secret.') from None
    raise GeminiError(f'Gemini {kind} failed on every key and model ({last}). Free quotas reset daily.')


def parts(response):
    return response.get('candidates', [{}])[0].get('content', {}).get('parts', [])


def json_call(prompt, schema, temperature=1.0):
    body = {'contents': [{'parts': [{'text': prompt}]}],
            'generationConfig': {'temperature': temperature, 'responseMimeType': 'application/json',
                                 'responseJsonSchema': schema}}
    response, model = call('text', body)
    text = ''.join(p.get('text', '') for p in parts(response))
    try:
        return json.loads(text), model
    except json.JSONDecodeError:
        raise GeminiError(f'{model} returned text that is not JSON.') from None


def speech_call(prompt, voice):
    body = {'contents': [{'parts': [{'text': prompt}]}],
            'generationConfig': {'responseModalities': ['AUDIO'],
                                 'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': voice}}}}}
    response, model = call('speech', body)
    audio = next((p['inlineData'] for p in parts(response) if 'inlineData' in p), None)
    if not audio:
        raise GeminiError(f'{model} returned no audio.')
    return audio, model
