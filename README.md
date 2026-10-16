# Stickman Reels

Hindi life-lesson Reels for Instagram, acted out by a stick figure and filmed like a short film. Each Reel is written, directed, narrated and rendered on GitHub Actions for free, then sent to Telegram for review.

**How a Reel is made:**
1. **Writer:** Gemini (free tier) drafts a tiny Hindi story about one life lesson. It includes three hook options, 4–6 beats, the lesson and a question for the comments. Each beat names an action, the place, who else is in frame and a prop.
2. **Director:** a second Gemini pass acts as a Reels motion director.
   - It picks and sharpens the strongest hook, using proven patterns: a surprising number, a mistake you make, a contrast, a mystery.
   - It checks that every action shows its line.
   - It plans the camera: a different shot for each beat (wide, close, extreme close, low or high angle, tilted, push-in, pull-out, pan, two-shot) and the transition into it (cut, whip pan, zoom, flash).
3. **Voice:**
   - Gemini's speech model reads the story in a warm Hindi voice.
   - FFmpeg finds the pauses between lines.
   - Whisper (`small` model, given the script as a hint) times every word, so the subtitle highlight lands on the word being spoken.
4. **Animation:** [Remotion](https://www.remotion.dev) renders a 1080×1920 Reel with:
   - **The hook:** on screen from the very first frame, over the story's most dramatic action and a push-in.
   - **The hero:** the same capped figure every time, named in the hook.
   - **26 actions:** for example walk in, think, idea, sad, cry, cheer, angry, run, scroll the phone, sleep and alarm, workout, work late, count money, fall and get up, carry a burden, climb, read, walk away, handshake, argue, hug, help up.
   - **Characters:** माँ, पापा, दोस्त, बॉस, पार्टनर, बच्चा and अजनबी, each with its own colour and accessory. They join two-person beats or watch and react.
   - **Places:** home, office, street, night, park and classroom, drawn in layers that move at different speeds, so camera moves have depth.
   - **Camera:** handheld drift, a punch-in and shake on impacts, and a 3D tilt for low and high angles.
   - **Sound:** effects made in code (whoosh, pop, thud, ding, ta-da, alarm, heartbeat…) and a lo-fi music bed made for each Reel. The music sits under the voice and rises at the end.
   - **The ending:** the lesson card, then the question and a follow button. The last frames dissolve into the opening, so the Reel loops.
5. **Review:** each video and its cover image arrive in your Telegram chat. Nothing is posted yet.

## Make Reels

- **From GitHub:** go to Actions → **Make a Reel** → Run workflow.
  - Type a lesson, or leave it empty for a fresh random line of [`topics.txt`](topics.txt). The last 25 topics are skipped.
  - **count** makes up to 5 Reels on different topics in one run.
  - **series** makes a two-part story. Part 1 ends on a cliffhanger.
  - **sample** renders [`examples/sample.json`](examples/sample.json) without Gemini, to test the template.
- **Every day:** set the repository variable `DAILY_REEL` to `true`. A Reel is then made at 09:00 IST.

A Reel takes about 6–8 minutes, including installing everything.

## Setup

**Secrets** (Settings → Secrets and variables → Actions):

| Secret | What |
| --- | --- |
| `GEMINI_API_KEY` | Free key from [Google AI Studio](https://aistudio.google.com/apikey). Optional `GEMINI_API_KEY_2` and `GEMINI_API_KEY_3` add more free daily quota. |
| `TELEGRAM_BOT_TOKEN` | Bot token |
| `TELEGRAM_CHAT_ID` | Your chat with the bot |

**Variables** (all optional):

| Variable | What |
| --- | --- |
| `REEL_HANDLE` | The channel handle shown on the Reel, e.g. `@stick.seekh` |
| `DAILY_REEL` | `true` makes a Reel every day at 09:00 IST |
| `REEL_VOICE` | Gemini voice name (default `Achird`; try `Sulafat`, `Charon`, `Kore`) |
| `GEMINI_MODEL`, `GEMINI_TTS_MODEL` | Override the text or speech model |

## Work on it locally

```bash
pip install -r requirements.txt
python -m reel make --sample examples/sample.json --silent
cd remotion
npm ci
npm run studio
npx remotion render src/index.ts StickReel out/reel-1.mp4 --props=public/reels/1/props.json
python -m unittest discover -s tests -t .
```

- `npm run studio` opens Remotion Studio with sample timing.
- Without `--silent` (and with `GEMINI_API_KEY` set), `make` writes a new story and records the voice.
- `python -m reel sounds` rewrites the sound effects.

## Files

| File | Role |
| --- | --- |
| `reel/script.py` | The writer and director prompts, and the lists of actions, props, characters, places, shots and transitions. Also checks Gemini's answers and keeps the topic history. |
| `reel/voice.py` | Hindi narration, line timing (pauses) and word timing (Whisper) |
| `reel/sounds.py` | Sound effects and the music bed, made in code |
| `reel/build.py` | Writes each Reel's `props.json`: segments, word times, music |
| `remotion/src/StickReel.tsx` | The Reel: hook, captions, subtitles, lesson and follow cards, sound, loop |
| `remotion/src/director.ts` | Camera shots, handheld drift, punch-ins, 3D tilt, transitions |
| `remotion/src/actions.tsx` | The 26 actions, the characters and the props |
| `remotion/src/places.tsx` | The six places, drawn in layers |
| `remotion/src/engine/` | Stick-figure rig and effects (adapted from nispa/stickman-video, MIT) |

**Adding an action, place, shot or character:**
1. Add it to the list in `reel/script.py`.
2. Draw it in the matching template file.

Tests check that the two always match.

## Licence and cost

- **Remotion:** free for individuals and companies of up to 3 people ([licence](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md)).
- **Gemini:** free tier.
- **Whisper:** runs on the Actions runner.
- **Sounds and music:** made in code, so there's nothing to license.
- **GitHub Actions:** a private repository gets 2,000 free minutes a month. One Reel uses about 7.
- **Third-party code and fonts:** see [THIRD_PARTY.md](THIRD_PARTY.md).
