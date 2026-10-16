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
   - **Dialogue:** 1–2 beats are spoken by the characters themselves. The narrator voices the hero's own words, and the other person (माँ, पापा, बॉस…) gets a fitting second voice. Their mouths move with the sound, and the subtitle shows who is speaking.
   - FFmpeg finds the pauses between lines.
   - Whisper (`small` model, given the script as a hint) times every word, so the subtitle highlight lands on the word being spoken.
4. **Animation:** [Remotion](https://www.remotion.dev) renders a 1080×1920 Reel with:
   - **The hook:** on screen from the very first frame, over the story's most dramatic action and a push-in.
   - **The hero:** the same capped figure every time, named in the hook.
   - **26 actions:** for example walk in, think, idea, sad, cry, cheer, angry, run, scroll the phone, sleep and alarm, workout, work late, count money, fall and get up, carry a burden, climb, read, walk away, handshake, argue, hug, help up.
   - **Characters:** माँ, पापा, दोस्त, बॉस, पार्टनर, बच्चा and अजनबी, each with its own colour and accessory. They join two-person beats or watch and react.
   - **Places:** home, office, street, night, park, classroom, kitchen, bus, hospital, sunset, rain, and day turning into night. They're drawn in layers that move at different speeds, so camera moves have depth.
   - **Expressions:** surprised, heart eyes, crying, a big smile, sleepy, blushing, and talking mouths.
   - **Captions:** each beat's keyword pops out on a marker swipe, with an optional sticker (🔥 ⭐ ✅ ❌ ⚡ ₹ ❤️ ⚠️ 💯 ❓, drawn as shapes).
   - **Camera:** handheld drift, a punch-in and shake on impacts, and a 3D tilt for low and high angles.
   - **Sound:** effects made in code (whoosh, pop, thud, ding, ta-da, alarm, heartbeat…) and a lo-fi music bed made for each Reel. The music sits under the voice and rises at the end.
   - **The ending:**
     - the lesson card, then the question;
     - **Like · Subscribe · Follow · Share** buttons, tapped one by one by a cursor;
     - a small "+ फ़ॉलो करें" nudge slides in halfway through;
     - the last frames dissolve into the opening, so the Reel loops.
   - **Quality check:** before sending, FFmpeg checks the length, the size and the sound. Gemini then looks at 4 frames for cut-off or overlapping text and badly framed figures. Any problem is listed in the Telegram caption.
5. **Review:** each video and its cover image arrive in your Telegram chat with three buttons:
   - **✅ Post** sends it to Instagram and YouTube Shorts, and the links come back to the chat.
   - **🔁 Make again** writes a new story on the same lesson.
   - **🗑 Skip** discards it.

   With the `AUTO_POST` variable set to `true`, Reels are posted without waiting for a tap.
6. **Weekly report:** every Monday at 09:00 IST (or on `/report`) you get:
   - the last 7 days of views, likes, comments, saves and shares on both platforms;
   - the three best Reels;
   - a tip on what to make more of.

## When Gemini fails (free backups)

| Step | Backups, in order |
| --- | --- |
| Story (text) | 3 Gemini keys × 2 models → **Groq** (`GROQ_API_KEY`, free) → **OpenRouter** free models (`OPENROUTER_API_KEY`, free) |
| Voice | 3 Gemini keys × 2 speech models → free **Microsoft Edge** Hindi neural voices (Madhur and Swara, pitch-shifted per character; no key needed) |
| Quality check | Gemini; when it fails the visual check is skipped, but the length and sound checks still run |

Every backup used is named in the Telegram caption. Both backup keys are free: [console.groq.com](https://console.groq.com/keys) and [openrouter.ai/keys](https://openrouter.ai/keys).

## Make Reels

- **From Telegram:**
  - Send any life lesson (e.g. "गुस्से में फैसले मत लो") and the bot makes a Reel about it.
  - `/reel` picks a fresh lesson.
  - `/batch 3` makes three Reels at once.
  - `/series दोस्ती` makes a two-part story.
  - `/status` shows what's running, and `/report` sends this week's numbers.
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
| `GROQ_API_KEY`, `OPENROUTER_API_KEY` | Optional free text backups for when Gemini fails |
| `TELEGRAM_BOT_TOKEN` | Bot token |
| `TELEGRAM_CHAT_ID` | Your chat with the bot |

**Telegram bot** (the stickman bot, separate from the infographic one): add these secrets, then run Actions → **Deploy bot** once. After that it redeploys by itself whenever `bot/` changes.

| Secret | What |
| --- | --- |
| `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN` | The same values as in the infographic repository. The token needs *Workers Scripts: Edit*. |
| `GH_DISPATCH_TOKEN` | A fine-grained GitHub token. Set *Repository access* to stickman-reels and *Actions* to Read and write. The bot uses it to start the workflows. |

**Posting** (each platform switches on when its secrets are added):

| Secret | What |
| --- | --- |
| `INSTAGRAM_ACCESS_TOKEN` | A long-lived token for the new Instagram Professional account (it lasts 60 days). Optionally also add `INSTAGRAM_USER_ID`. |
| `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN` | Run `python tools/youtube_auth.py --save-to-github` on your PC and sign in with the **stickman channel's** Google account. Using the same Google Cloud OAuth client as the infographic page is fine. |

**Variables** (all optional):

| Variable | What |
| --- | --- |
| `REEL_HANDLE` | The channel handle shown on the Reel, e.g. `@stick.seekh` |
| `DAILY_REEL` | `true` makes a Reel every day at 09:00 IST |
| `AUTO_POST` | `true` posts every Reel without waiting for ✅ Post |
| `YOUTUBE_PRIVACY` | `public` (default), `unlisted` or `private` |
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
| `reel/publish.py` | Instagram (resumable upload) and YouTube Shorts posting, with a receipt so nothing is posted twice |
| `reel/report.py` | The weekly numbers |
| `bot/` | The Telegram bot (Cloudflare Worker): turns messages and button taps into workflow runs |
| `tools/youtube_auth.py` | One-time YouTube sign-in that saves the secrets |
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
