# Stickman Reels

Hindi life-lesson Reels for Instagram, acted out by a stick figure and filmed like a short film. Each Reel is written, directed, narrated and rendered on GitHub Actions for free, then sent to Telegram for review.

**How a Reel is made:**
1. **Writer:** Gemini (free tier) drafts a tiny Hindi story about one life lesson. It includes three hook options, 5–8 short beats (at most 12 words each), the lesson and a question for the comments. Each beat names an action, the place, who else is in frame and a prop.
   - **First person:** the hero tells their own story ("उस दिन मैंने पहली बार उसे देखा..."), never "he did". A draft told in the third person is sent back, and the director keeps it in first person.
   - **Lively:** every story has at least two comic moments (an over-the-top reaction, a cheeky comeback, a silly misunderstanding) on the way to its lesson.
   - **Love first:** love stories (a crush, waiting for a reply, a breakup, a proposal) are the channel's favourite. About 40% of Reels without a chosen topic are love stories; change the share with the `LOVE_SHARE` variable.
2. **Director:** a second Gemini pass acts as a Reels motion director.
   - It picks and sharpens the strongest hook, using proven patterns: a surprising number, a mistake you make, a contrast, a mystery.
   - It checks that every action shows its line.
   - It plans the camera: a different shot for each beat (wide, close, extreme close, low or high angle, tilted, push-in, pull-out, pan, two-shot) and the transition into it (cut, whip pan, zoom, flash).
3. **Voice:**
   - Gemini's speech model reads the story as the hero, personal and sincere. The bot's voice choice also picks the hero: a male voice tells a boy's story, a female voice a girl's (with feminine verb forms, and a young man's voice for her partner).
   - **Dialogue:** 1–2 beats are spoken by the characters themselves. The narrator voices the hero's own words, and the other person (माँ, पापा, बॉस…) gets a fitting second voice. Their mouths move with the sound, and the subtitle shows who is speaking.
   - FFmpeg finds the pauses between lines.
   - Whisper (`small` model, given the script as a hint) times every word, so the subtitle highlight lands on the word being spoken.
4. **Animation:** [Remotion](https://www.remotion.dev) renders a 1080×1920 Reel with:
   - **More shots:** a scene longer than 3 seconds cuts to a second camera angle halfway, on a word (wide to medium, medium to close, a push-in to an extreme close-up…).
   - **The hook:** on screen from the very first frame, over the story's most dramatic action and a push-in.
   - **The hero:** the same figure every time, named in the hook: a boy in a cap, or a girl with a ponytail and a bow.
   - **Cartoon faces:** big white heads with an outline, eyes with pupils and a shine that blink every few seconds, eyebrows that carry the emotion, and a black open mouth (with a tongue) that moves with the voice.
   - **28 actions:** for example walk in, think, idea, sad, cry, cheer, angry, run, scroll the phone, sleep and alarm, workout, work late, count money, fall and get up, carry a burden, climb, read, walk away, handshake, argue, hug, help up, and for love stories **shy** (a blushing crush, hearts rising) and **propose** (kneels with a rose; the other person gasps, then says yes).
   - **Characters:** माँ, पापा, टीचर, दोस्त, बॉस, पार्टनर, बच्चा and अजनबी, each with its own colour and accessory (पापा and टीचर wear glasses and a moustache). They join two-person beats or watch and react.
   - **Places:** home, office, street, night, park, classroom, kitchen, bus, hospital, sunset, rain, and day turning into night. They're drawn in layers that move at different speeds, so camera moves have depth.
   - **Expressions:** happy, a big smile, surprised, angry, sad, crying, heart eyes, blushing, shy, smug, nervous (with a sweat drop), sleepy, and talking mouths.
   - **Captions:** each beat's keyword pops out on a marker swipe, with an optional sticker (🔥 ⭐ ✅ ❌ ⚡ ₹ ❤️ ⚠️ 💯 ❓, drawn as shapes).
   - **Camera:** handheld drift, a punch-in and shake on impacts, and a 3D tilt for low and high angles.
   - **Sound:** effects made in code (whoosh, pop, thud, ding, ta-da, alarm, heartbeat…) and a lo-fi music bed made for each Reel. The music sits under the voice and rises at the end.
   - **The ending:**
     - the lesson card, then the question;
     - **Like · Subscribe · Follow · Share** buttons, tapped one by one by a cursor;
     - a small "+ फ़ॉलो करें" nudge slides in halfway through;
     - the last frames dissolve into the opening, so the Reel loops.
   - **Safe zones:** subtitles, the corner bubble, the handle and the end card stay out of Instagram's top bar, bottom caption row and right-hand button column (`remotion/src/SafeZones.tsx`; set `guides: true` in the Studio to see them).
   - **Camera and acting (rules from Mr Omi's [claude-animated-shorts](https://github.com/mromidev/claude-animated-shorts)):**
     - a cut inside a line always changes the shot size by 40% or moves the kid a quarter of the frame;
     - the punchline snaps in on its twist word, with a spotlight and an impact kick;
     - story Reels glide with no handheld drift;
     - faces change 2 frames before the word, with natural random blinks and a blink over every face change;
     - gestures wind up before they move, hair trails the head, and a shock stretches the head;
     - mouth shapes follow the words (closed for म/ब/प, round, wide or open).
   - **Sound and master:** the music ducks under every spoken word, stops dead for the comic twist, and every Reel is colour-graded and loudness-normalised to -14 LUFS in one final encode (rendered at CRF 14, mastered at CRF 18).
   - **Cover:** comic Reels get their own cover image (`ComicCover`): the punchline's face, big, with 1–3 teaser words that survive the grid's 4:5 and 3:4 crops.
   - **Quality check:** before sending, FFmpeg checks the length, the size and the sound, and scans every frame for black or white flashes, frozen pictures and sudden pops (`reel/scan.py`). Gemini then looks at the cover, up to six lines and the end card for cut-off or overlapping text, badly framed figures and anything inside the phone's UI areas. Any problem is listed in the Telegram caption, and a contact sheet (one frame a second) follows the video.
5. **Review:** each video and its cover image arrive in your Telegram chat with three buttons:
   - **✅ Post** sends it to Instagram and YouTube Shorts, and the links come back to the chat.
   - **🔁 Make again** writes a new story on the same lesson.
   - **🗑 Skip** discards it.

   With the `AUTO_POST` variable set to `true`, Reels are posted without waiting for a tap.
6. **Weekly report:** every Monday at 09:00 IST (or on `/report`) you get:
   - the last 7 days of views, likes, comments, saves and shares on both platforms;
   - the three best Reels;
   - a tip on what to make more of.

## 😂 Comic Reels

A second style, made for the cartoon-meme Reels that go viral in India: one room, one cheeky cartoon kid behind a
table, talking straight to the viewer about a painfully relatable situation, ending on a punchline. The kid is
the channel's own character, not any TV cartoon, so nothing is copied.

- **The script** ([`reel/comic.py`](reel/comic.py)): Gemini writes a 30–40 second scene in everyday Hindi (a light
  UP/Bihar flavour is welcome), with naughty-kid cartoon energy: cheeky, mischievous, big reactions that switch
  fast, a silly dance, and dry deadpan lines in between. It has a setup line that hooks in two seconds, 5–7 short
  lines that escalate, and a punchline whose twist sits in its last words. A second Gemini pass, the comedy editor, sharpens the setup,
  makes the punchline land and cuts every extra word.
  - Each line says how the kid acts it: a **face** (deadpan, side eye, smug, cheeky, shock, eye roll, angry, cry, happy, nervous, sad), a **gesture** (typing, talking, shrug, facepalm, pointing, arms crossed, slamming the table, phone, chai, thinking, scratching the head, a victory dance, panicking) and where the kid **looks**.
  - **Banter:** up to three lines may come from someone else (मम्मी calling from the kitchen, पापा, the teacher, the boss), never two in a row, so the kid answers each with a cheeky comeback. They get their own voice.
  - Situations come from [`comic_topics.txt`](comic_topics.txt), a chosen theme, viewer ideas or the next festival, told the funny way.
- **The look** ([`remotion/src/comic/`](remotion/src/comic)):
  - **The kid:** a big round head, huge eyes and thick eyebrows that do the acting, a saffron T-shirt. A boy has a spiky tuft; a girl (female voice) has a ponytail and a bow.
  - **The room:** bedroom, classroom, kitchen, office, living room, gym or a street chai stall, chosen per line, so the kid can move. The bedroom desk only shows the computer when the line is about it.
  - **The picture follows the words:** each line has its own visual, chosen by the writer:
    - **the kid** talking;
    - **a person** saying the line in their own room (मम्मी in the kitchen, पापा, सर in the classroom, the boss, a friend), or a sepia **फ्लैशबैक** when the kid quotes them ("सर बोले थे...");
    - **a daydream** in a thought bubble;
    - **a cutaway:** the computer screen (song, video, job site, search, error), calendar pages flying, a salary slip, a certificate gathering cobwebs, a spinning clock, a phone chat or an exam result. The kid keeps talking in a corner bubble during a cutaway.

    The first shot follows its words too (no default computer), and at least half the lines show a character.
  - **On screen:** a white title strip with two emoji at the top ("Computer Course 😭😭"), subtitles at the bottom, and a new camera angle about every 2 seconds, cut on a word like a sitcom editor would (medium, close, left, tight, right). A cutaway or another person's line cuts back to the kid reacting on every other shot. There's and a snap zoom on the punchline followed by a "ba-dum-tss".
- **The voice:** Gemini reads it like a real, cheeky person talking to a friend: lively and playful, mock-dramatic where it's funny, dry on the deadpan lines, and a grin in the voice on the punchline. It uses its casual voices (`Zubenelgenubi`, or `Callirrhoe` for a girl; `REEL_VOICE` overrides). The Edge backup keeps its natural pitch, only a little faster.
- **The ending:** the question for the comments, then Like, Subscribe, Follow and Share.

### 👨‍👩‍👧 Who the jokes are for: `audience`

| Audience | What changes |
| --- | --- |
| `adult` (the default) | today's rants about adult life: salary, the boss, the gym, the WiFi |
| `family` (recommended) | a recurring kid (गोलू, or पिंकी with the female voice) with a catchphrase, kid-world situations from [`kids_topics.txt`](kids_topics.txt) that kids *and* parents enjoy, the rule of three, a callback twist, big readable faces, sound words, a brighter voice and music, and a kid-safety check |
| `kids` | the same, made **for** children: YouTube marks it "made for kids" (comments, the bell and personalised ads turn off), so the closing question becomes the catchphrase with a wink |

- Pick it per Reel with `audience=family` in the options, or switch **👨‍👩‍👧 Family comedy** on in the bot's ⚙️ Settings (the `REEL_AUDIENCE` variable). `kids` is a legal declaration, so it's only set by hand (`REEL_AUDIENCE=kids`).
- **Best of two:** every comic Reel (any audience) is now written twice; a Gemini "test audience" (an 8-year-old, a parent and a kids' comedy writer) scores both on laughs, surprise, clarity, picture and safety, the funnier one goes to the editor with the judges' one suggested fix, and for kids and family a draft that isn't safe to show a child is never picked. `COMIC_DRAFTS=1` switches it off (2 text calls a Reel instead of 4).
- **Safety nets:** a list of things a child could copy and get hurt by (matches, gas, sockets, medicines, heights, knives, roads, locking someone in), the judge's safety score, and the visual check, which also looks for anything mean or scary in family Reels.
- **New on screen:** faces *giggle*, *sneaky*, *proud* and *dizzy* (spiral eyes); gestures *hide* (peeking through the fingers), *jump*, *eat* and *sneak*; दादी and दीदी join मम्मी, पापा and सर; and the *oops* cutaway, a full-screen sound word ("धड़ाम!") on a starburst. Cartoon sounds (slide whistle, squeaky toy, tiptoes, sparkle) and a bouncier kids music bed.
- **Funnier for every audience:** the comedy rules now ask for the rule of three, a callback to the setup, one picture per joke and a hook whose first three words say the situation; story Reels get a "wait, why?" mystery beat and a lesson that calls back to the hook.

**Make one:**
- **From Telegram:** tap **😂 Comic Reel now**, use **😂 Make it comic instead** on the last step of the menu, or send `/comic` (or `/comic gym membership`).
- **Always:** switch on **😂 Comic style by default** in ⚙️ Settings, which sets `REEL_STYLE=comic`. The daily Reel and plain `/reel` are then comic too.
- **Make again** keeps the style. A two-part series is always a story.
- **From GitHub:** Make a Reel with `style=comic` in *options*. With *sample* ticked, that renders [`examples/comic.json`](examples/comic.json) without Gemini.

## Growth features

| Feature | What it does | Switch |
| --- | --- | --- |
| **Best time to post** | The weekly report learns which slot (08:00, 13:00, 19:00 or 21:00 IST) gets the most reach. ✅ Post then schedules the Reel for that slot: YouTube and Facebook schedule it themselves, and Instagram is uploaded at once and published by **Post queued Reels** at that time. | `POST_AT_PEAK=true` |
| **Learning** | Each Reel's score (shares and saves count most) is saved in the topic history. The writer is told which recent Reels did best and worst, and leans toward what worked. | always on |
| **Hook test** | The director writes a second on-screen hook (`title_b`). That version is rendered too and posted as an Instagram **trial Reel**, which is shown to non-followers first and shared with followers if it does well. | `HOOK_TEST=true` |
| **Carousel** | 5 portrait slides from every Reel (the hook, three beats and the lesson) are posted as an Instagram carousel, which earns the most saves. The images are hosted for 2 days by the bot's Worker (Workers KV, free). | `CAROUSEL=true` |
| **Weekly compilation** | Every Sunday at 19:00 IST, the week's posted Reels are joined into "इस हफ्ते की N सीख" with an intro, an outro and YouTube chapters. It arrives in Telegram with a ✅ Post to YouTube button. | needs 3+ posted Reels |
| **Facebook Reels** | Each Reel is also posted to your Facebook Page. | `FACEBOOK_PAGE_ID`, `FACEBOOK_PAGE_TOKEN` |
| **Festivals and special days** | A plain `/reel` or the daily Reel checks the calendar first. 0–3 days before Diwali, Holi, Raksha Bandhan, Dussehra, New Year, Mother's Day, Father's Day, Friendship Day, Teachers' Day, Children's Day and more, the Reel's lesson is tied to the occasion: family and values, never religious content. In board-exam and results season, one Reel a week. The caption says "🎉 दिवाली special". Moving festival dates are listed in `reel/occasions.py` for 2026–2027. | `OCCASIONS=off` turns it off |
| **Ideas from comments and trends** | Every Monday, and on `/ideas`, Gemini reads your Reels' comments plus what India searches on YouTube and Google. It suggests 5 new lessons, each with a Make button, plus reply drafts for you to copy. Plain `/reel` uses these ideas first. | always on |
| **Instagram token** | Renewed on the 1st and 15th of each month and saved back as the secret, so posting never stops. | `GH_DISPATCH_TOKEN` needs *Secrets: Read and write* |

## Gemini first, free backups only when it fails

Gemini always gets priority, for both the story and the voice. A backup is used only after Gemini has had every chance:

1. **Every Gemini key and model:** up to 3 keys (`GEMINI_API_KEY`, `_2`, `_3`) on 2 models each.
2. **Per-minute limits are waited out:** when Gemini answers "too many requests, retry in 20s", the run waits (up to 65 s, `GEMINI_MAX_WAIT`) and tries the same key again, once per key.
3. **A daily quota that's used up** moves straight to the next key. A brief outage moves to the next key or model.
4. **Dialogue:** if Gemini's two-voice dialogue fails, Gemini retries with its single storyteller voice before any backup.

| Step | When all of Gemini fails |
| --- | --- |
| Story (text) | **Groq** (`GROQ_API_KEY`, free) → **OpenRouter** free models (`OPENROUTER_API_KEY`, free) |
| Voice | Free **Microsoft Edge** Hindi neural voices (Madhur and Swara, pitch-shifted per character; no key needed) |
| Quality check | The visual check is skipped; the length and sound checks still run |

Every backup used is named in the Telegram caption, so you know when Gemini didn't make a Reel. Both text backup keys are free: [console.groq.com](https://console.groq.com/keys) and [openrouter.ai/keys](https://openrouter.ai/keys).

## Make Reels

- **From Telegram:**
  - Tap **🎬 New Reel** and choose step by step:
    - **topic:** 🎲 a fresh random lesson, 💡 viewer ideas, 🎉 the next festival, 📚 a theme (प्यार, परिवार, पैसा, सेहत, पढ़ाई, दोस्ती, काम, आत्मसम्मान, रिश्ते, आदतें, समय), or ✍️ your own lesson;
    - **voice:** 👨 male or 👩 female;
    - **music:** auto, warm, tense or none;
    - **how many:** 1, 2, 3 or 5, or a 📖 two-part story;
    - then **✅ Make it**.

    **⚡ Random Reel now** skips the questions.
  - **Send any lesson as a message**, and the menu continues with voice, music and count. `/reel <lesson>` makes it straight away with the usual settings.
  - **⚙️ Settings** shows on/off switches for auto-post, posting at the best time, carousel, hook test, the daily Reel and festival topics. Each tap saves the repository variable; `GH_DISPATCH_TOKEN` needs *Variables: Read and write*.
  - **Other commands:** `/comic [situation]`, `/batch 3`, `/series <lesson>`, `/status`, `/report`, `/ideas`.
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
| `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN` | The same values as in the infographic repository. The token needs *Workers Scripts: Edit*, plus *Workers KV Storage: Edit* for carousel images. |
| `GH_DISPATCH_TOKEN` | A fine-grained GitHub token. Set *Repository access* to stickman-reels, and *Actions*, *Secrets* and *Variables* to Read and write. The bot uses it to start the workflows, and the token renewal uses it to save the new Instagram token. |

**Posting** (each platform switches on when its secrets are added):

| Secret | What |
| --- | --- |
| `INSTAGRAM_ACCESS_TOKEN` | A long-lived token for the new Instagram Professional account. It lasts 60 days and is renewed automatically. Optionally also add `INSTAGRAM_USER_ID`. |
| `FACEBOOK_PAGE_ID`, `FACEBOOK_PAGE_TOKEN` | Optional: the Facebook Page linked to the Instagram account, and a Page access token with *pages_manage_posts* |
| `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN` | Follow [docs/youtube-setup.md](docs/youtube-setup.md): set up the Google Cloud app, then run `python tools/youtube_auth.py --save-to-github` and sign in with the **stickman channel's** account. **Check YouTube sign-in** runs every morning. It saves a renewed token back automatically, and warns you in Telegram before the sign-in ends or if it stops working. |

**Variables** (all optional):

| Variable | What |
| --- | --- |
| `REEL_HANDLE` | The channel handle shown on the Reel, e.g. `@stick.seekh` |
| `DAILY_REEL` | `true` makes a Reel every day at 09:00 IST |
| `AUTO_POST` | `true` posts every Reel without waiting for ✅ Post |
| `POST_AT_PEAK` | `true` posts at the learned best time instead of at once |
| `HOOK_TEST` | `true` also posts a second-hook version as an Instagram trial Reel |
| `CAROUSEL` | `true` also posts a 5-slide carousel of every Reel |
| `YOUTUBE_PRIVACY` | `public` (default), `unlisted` or `private` |
| `REEL_AUDIENCE` | `family` writes comic Reels for families (a recurring kid, kid-world jokes); `kids` also marks YouTube uploads "made for kids"; empty or `adult` keeps adult rants. The bot's ⚙️ Settings switch sets `family` or `adult` |
| `COMIC_DRAFTS` | How many comic drafts the test-audience judge picks from, `1`-`3` (default `2`; `1` switches the judge off) |
| `KID_NAME`, `KID_NAME_GIRL`, `KID_CATCHPHRASE` | The recurring kid of family and kids Reels (default गोलू, पिंकी and "प्लान तो मेरा फुल-प्रूफ था!") |
| `REEL_ENGINE` | `three` draws comic Reels' rooms in 3D (three.js): a toon-shaded room with real perspective, light, shadows and depth of field, real 3/4, low and high angles and a dolly zoom on a shock, with the same SVG kid placed by the same camera. Rendered on the CPU on GitHub Actions (slower: the run's notice shows the time); empty or `svg` keeps the flat rooms |
| `REEL_INK` | `plum` tries Mr Omi's softer plum ink (#241726) on comic Reels instead of near-black, as an A/B test |
| `LOVE_SHARE` | The share of Reels without a chosen topic that are love stories, from `0` to `1` (default `0.4`) |
| `REEL_STYLE` | `comic` makes comic Reels by default (the bot's 😂 switch); `story` or empty for stick-figure stories |
| `REEL_VOICE` | Gemini voice name (default `Achird`; try `Sulafat`, `Charon`, `Kore`) |
| `GEMINI_MODEL`, `GEMINI_TTS_MODEL` | Override the text or speech model |

## Work on it locally

```bash
pip install -r requirements.txt
python -m reel make --sample examples/sample.json --silent
python -m reel make --sample examples/comic.json --silent   # a comic Reel
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
| `reel/comic.py` | Comic Reels: the comedy writer and editor prompts, and the kid's faces, gestures, looks and rooms |
| `reel/voice.py` | Hindi narration, line timing (pauses) and word timing (Whisper) |
| `reel/sounds.py` | Sound effects and the music bed, made in code |
| `reel/build.py` | Writes each Reel's `props.json`: segments, word times, music |
| `reel/publish.py` | Instagram (resumable upload) and YouTube Shorts posting, with a receipt so nothing is posted twice |
| `reel/report.py` | The weekly numbers |
| `reel/growth.py` | Best posting time, learning from scores, ideas from comments and trends, Instagram token renewal |
| `reel/occasions.py` | Festivals, special days and seasons, and which one is due |
| `reel/carousel.py` | Carousel slides and the weekly compilation |
| `reel/media.py` | 2-day public links for carousel images (Workers KV, served by the bot) |
| `bot/` | The Telegram bot (Cloudflare Worker): turns messages and button taps into workflow runs |
| `tools/youtube_auth.py` | One-time YouTube sign-in that saves the secrets |
| `remotion/src/StickReel.tsx` | The Reel: hook, captions, subtitles, lesson and follow cards, sound, loop |
| `remotion/src/director.ts` | Camera shots, handheld drift, punch-ins, 3D tilt, transitions |
| `remotion/src/actions.tsx` | The 26 actions, the characters and the props |
| `remotion/src/places.tsx` | The six places, drawn in layers |
| `remotion/src/engine/` | Stick-figure rig and effects (adapted from nispa/stickman-video, MIT) |
| `remotion/src/comic/` | Comic Reels: the cartoon kid (`Kid.tsx`), the rooms, the drawn emoji and the Reel itself (`ComicReel.tsx`) |

**Adding an action, place, shot or character** (or a comic face, gesture, room or emoji):
1. Add it to the list in `reel/script.py` (or `reel/comic.py`).
2. Draw it in the matching template file.

Tests check that the two always match.

## Licence and cost

- **Remotion:** free for individuals and companies of up to 3 people ([licence](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md)).
- **Gemini:** free tier.
- **Whisper:** runs on the Actions runner.
- **Sounds and music:** made in code, so there's nothing to license.
- **GitHub Actions:** a private repository gets 2,000 free minutes a month. One Reel uses about 7.
- **Third-party code and fonts:** see [THIRD_PARTY.md](THIRD_PARTY.md).
