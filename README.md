# Stickman Reels

Hindi life-lesson Reels for Instagram, acted out by a stick figure. Each Reel is written, narrated and rendered on GitHub Actions for free, then sent to Telegram for review.

**How a Reel is made:**
1. **Story:** Gemini (free tier) writes a tiny Hindi story about one life lesson: a hook, 4–5 beats, the lesson and a question for the comments. Each beat names one stickman action and an optional prop.
2. **Voice:** Gemini's speech model reads the whole story in one warm Hindi voice. Each beat starts when its line is spoken (FFmpeg finds the pauses).
3. **Animation:** [Remotion](https://www.remotion.dev) renders a 1080×1920 Reel:
   - a cursor draws the hero, and the title slams in;
   - the figure acts out each beat, and the background colour follows the mood;
   - Hindi subtitles highlight the word being spoken;
   - the lesson appears on a card, then the question and a "फ़ॉलो करें" button.
4. **Review:** the video arrives in your Telegram chat. Nothing is posted yet.

## Make a Reel

- **From GitHub:** go to Actions → **Make a Reel** → Run workflow. Type a lesson, or leave it empty for a random line of [`topics.txt`](topics.txt). It takes about 5 minutes.
- **Every day:** set the repository variable `DAILY_REEL` to `true`. A Reel is then made at 09:00 IST.
- **Test the template without Gemini:** tick **sample** when you run the workflow. That renders [`examples/sample.json`](examples/sample.json).

## Setup

**Secrets** (Settings → Secrets and variables → Actions):

| Secret | What |
| --- | --- |
| `GEMINI_API_KEY` | Free key from [Google AI Studio](https://aistudio.google.com/apikey). Optional `GEMINI_API_KEY_2` and `GEMINI_API_KEY_3` add more free daily quota. |
| `TELEGRAM_BOT_TOKEN` | Bot token. The same bot as the infographic page is fine. |
| `TELEGRAM_CHAT_ID` | Your chat with the bot. |

**Variables** (all optional):

| Variable | What |
| --- | --- |
| `REEL_HANDLE` | The channel handle shown on the Reel, e.g. `@stick.seekh` |
| `DAILY_REEL` | `true` makes a Reel every day at 09:00 IST |
| `REEL_VOICE` | Gemini voice name (default `Achird`; try `Sulafat`, `Charon`, `Kore`) |
| `GEMINI_MODEL`, `GEMINI_TTS_MODEL` | Override the text or speech model |

## Work on it locally

```bash
python -m reel make --sample examples/sample.json --silent
cd remotion
npm ci
npm run studio
npx remotion render src/index.ts StickReel out/reel-1080x1920.mp4 --props=public/props.json
python -m unittest discover -s tests -t .
```

- `npm run studio` opens Remotion Studio with sample timing, so you can tweak the animation live.
- Without `--silent` (and with `GEMINI_API_KEY` set), `make` writes a new story and records the voice.

## Files

| File | Role |
| --- | --- |
| `reel/script.py` | The story prompt, the list of actions, props and moods, and the checks on Gemini's answer |
| `reel/voice.py` | Hindi narration, and when each line starts |
| `reel/build.py` | Writes `props.json`: every segment with its start and end |
| `remotion/src/StickReel.tsx` | The Reel: captions, subtitles, lesson card, follow card, mood colours |
| `remotion/src/actions.tsx` | The 16 stickman actions and 7 props, and where they go on stage |
| `remotion/src/engine/` | Stick-figure rig and effects (adapted from nispa/stickman-video, MIT) |
| `topics.txt` | Life lessons to pick from |

**Adding an action:**
1. Add it to `ACTIONS` in `reel/script.py`.
2. Add a `case` for it in `remotion/src/actions.tsx`.

A test checks that the two lists match.

## Licence and cost

- **Remotion:** free for individuals and companies of up to 3 people ([licence](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md)).
- **Gemini:** free tier.
- **GitHub Actions:** a private repository gets 2,000 free minutes a month. One Reel takes about 5 minutes.
- **Third-party code and fonts:** see [THIRD_PARTY.md](THIRD_PARTY.md).
