"""Command line.

    python -m reel make [--topic "..."] [--count 3 | --series] [--sample examples/sample.json] [--silent]
    python -m reel send out/1 remotion/out/reel-1.mp4 [--cover out/1/cover.jpg]
    python -m reel publish out/1 remotion/out/reel-1.mp4 [--platforms instagram,youtube]
    python -m reel publish-queued out/1   (posts Instagram uploads waiting for the best time)
    python -m reel report        (weekly numbers to Telegram)
    python -m reel ideas         (next lessons from comments and trends, with Make buttons)
    python -m reel slides out/1 remotion/out/reel-1.mp4   (carousel slides)
    python -m reel compile reels.json out/week.mp4        (the weekly compilation)
    python -m reel refresh-token (renews the Instagram token; prints it for the workflow to save)
    python -m reel topic out/1   (prints the lesson of a Reel, for "Make again"; --style prints story or comic)
    python -m reel sounds        (rewrites remotion/public/sfx/*.wav)

`make` writes each Reel to out/<n>/ and its media to remotion/public/reels/<n>/, and lists the numbers in
out/reels.txt for the render step.
"""
import argparse
import json
import os
import sys
from pathlib import Path

# build and sounds need numpy (installed only where Reels are made); they load in the commands that use them,
# so posting, the report, the queue and the sign-in checks run on a plain Python.
from . import carousel, growth, publish, quality, report, script, telegram

ROOT = Path(__file__).resolve().parents[1]


def caption(story, record, folder=None):
    part = f" (भाग {story['part']})" if story.get('part') else ''
    special = [f"🎉 {story['occasion_name']} special"] if story.get('occasion_name') else []
    lines = special + [story['title'] + part, '', story.get('instagram_caption') or story['lesson'], '', ' '.join(story.get('hashtags', []))]
    check = quality.note(folder) if folder else ''
    if check:
        lines += ['', check]
    if record.get('backups'):
        lines += ['', 'Backup used: ' + ', '.join(b['service'] for b in record['backups'])]
    if record.get('narration') == 'failed':
        lines += ['', '(Preview without narration: ' + record.get('reason', '')[:150] + ')']
    return '\n'.join(lines).strip()


def stories(args):
    from . import comic
    if args.sample:
        raw = json.loads(args.sample.read_text(encoding='utf-8'))
        yield (comic.clean if raw.get('style') == 'comic' else script.clean)(raw)
        return
    if args.style == 'comic' and not args.series:
        for _ in range(args.count):
            yield comic.write(args.topic, theme=args.theme, source=args.source, audience=getattr(args, 'audience', 'adult'))
        return
    if args.series:
        first = script.write(args.topic, part='1/2', theme=args.theme, source=args.source)
        yield first
        summary = {k: first[k] for k in ('topic', 'name', 'title', 'hook', 'lesson')}
        summary['beats'] = [s['line'] for s in first['scenes']]
        yield script.write(first['topic'], part='2/2', previous=summary)
        return
    for _ in range(args.count):
        yield script.write(args.topic, theme=args.theme, source=args.source)


AUDIENCES = ('kids', 'family', 'adult')
OPTIONS = {'theme': tuple(script.THEMES), 'source': script.SOURCES, 'voice': ('male', 'female'), 'music': ('auto', 'warm', 'tense', 'off'),
           'style': script.STYLES, 'audience': AUDIENCES}


def audience_of(chosen):
    """Who comic jokes are for: the bot's choice, else REEL_AUDIENCE (the bot's 👨‍👩‍👧 switch), else adult."""
    usual = os.getenv('REEL_AUDIENCE', '').strip().lower()
    return chosen.get('audience') or (usual if usual in AUDIENCES else 'adult')


def style_of(chosen):
    """The bot's choice, else the REEL_STYLE variable (the usual style, set in the bot's Settings), else story."""
    usual = os.getenv('REEL_STYLE', '').strip().lower()
    return chosen.get('style') or (usual if usual in script.STYLES else 'story')


def parse_options(text):
    """The bot's choices, "theme=money voice=female music=off source=ideas", checked against OPTIONS."""
    chosen = {}
    for part in (text or '').replace(',', ' ').split():
        key, _, value = part.partition('=')
        if value in OPTIONS.get(key, ()):
            chosen[key] = value
    return chosen


def make(args):
    made = []
    for n, story in enumerate(stories(args), 1):
        if args.music in script.MUSIC:
            story['music'] = args.music
        out = args.out / str(n)
        from . import build
        props, record = build.build(story, out, args.public, narrate=not args.silent, music=not args.no_music,
                                    prefix=f'reels/{n}/')
        if not args.sample:
            script.remember(story)
        made.append(str(n))
        print(f"Reel {n}: {story['title']} ({story['topic']}): {len(props['segments'])} segments, "
              f"{props['duration']:.1f}s, narration: {record.get('voice', record.get('narration'))}, "
              f"words: {record.get('word_timing', '-')}, directed: {story.get('directed', '-')}")
    (args.out / 'reels.txt').write_text('\n'.join(made) + '\n', encoding='utf-8')


YOUTUBE_FIX = ('Fix it once:\n1. console.cloud.google.com/auth/audience → Publish app (status "In production"); '
               'in "Testing" Google ends the sign-in every 7 days.\n2. On your PC, in the stickman-reels folder: '
               'python tools/youtube_auth.py --save-to-github (sign in with the stickman channel\'s Google account).')


def youtube_check():
    """Daily: make sure YouTube posting still works. Exit 2 when a renewed token was written for the workflow to save."""
    if 'youtube' not in publish.configured():
        print('YouTube is not connected yet.')
        return 0
    result = publish.youtube_check()
    print({k: v for k, v in result.items() if k != 'new_refresh_token'})
    if not result['ok']:
        telegram.send_message(f"⚠️ YouTube posting is not working: {result['problem']}\n\n{YOUTUBE_FIX}")
        return 1
    days = result.get('expires_days')
    if days is not None and days <= 3:
        telegram.send_message(f'⏳ The YouTube sign-in ends in {days} day(s) because the Google app is still in "Testing".\n\n{YOUTUBE_FIX}')
    if result.get('new_refresh_token'):
        token = result['new_refresh_token']
        print(f'::add-mask::{token}')
        Path(os.getenv('TOKEN_FILE', 'yt-token.txt')).write_text(token, encoding='utf-8')
        return 2
    return 0


def compile_week(args):
    """Join the week's Reels between the intro and outro cards; upload to YouTube with --post."""
    if args.reuse:
        title, _, text = args.out.with_suffix('.txt').read_text(encoding='utf-8').partition('\n\n')
        result = publish.youtube_upload(args.out, {'title': title, 'lesson': '', 'hashtags': ['#hindi', '#lifelessons', '#stickman']},
                                        {}, title=title, description=text, shorts=False)
        telegram.send_message(f"📺 Weekly compilation on YouTube: {result['url']}" + (f"\n{result['note']}" if result.get('note') else ''))
        return 0
    plan = json.loads(args.list.read_text(encoding='utf-8'))
    stories = [json.loads((Path(r['folder']) / 'script.json').read_text(encoding='utf-8')) for r in plan['reels']]
    clips = [plan['intro'], *(r['video'] for r in plan['reels']), plan['outro']]
    carousel.join(clips, args.out)
    marks = carousel.chapters(carousel.duration(plan['intro']), [(s['title'], carousel.duration(r['video']))
                                                                  for s, r in zip(stories, plan['reels'])])
    text = carousel.description(marks, [s['lesson'] for s in stories])
    title = f'इस हफ्ते की {len(stories)} सीख | Hindi Life Lessons | Stickman Stories'
    args.out.with_suffix('.txt').write_text(title + '\n\n' + text, encoding='utf-8')
    print(title, f'{carousel.duration(args.out):.0f}s')
    if args.post:
        story = {'title': title, 'lesson': '', 'hashtags': ['#hindi', '#lifelessons', '#stickman', '#motivation']}
        result = publish.youtube_upload(args.out, story, {}, title=title, description=text, shorts=False)
        telegram.send_message(f"📺 Weekly compilation on YouTube: {result['url']}" + (f"\n{result['note']}" if result.get('note') else ''))
    return 0


def main(argv=None):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # Hindi titles on a Windows console
    parser = argparse.ArgumentParser(prog='reel')
    commands = parser.add_subparsers(dest='command', required=True)
    make_cmd = commands.add_parser('make', help='write the scripts, record the narration and build props.json')
    make_cmd.add_argument('--topic', default='', help='the life lesson (default: a random fresh line of topics.txt)')
    make_cmd.add_argument('--count', type=int, default=1, help='how many Reels to make (different topics)')
    make_cmd.add_argument('--series', action='store_true', help='make a two-part story (part 1 ends on a cliffhanger)')
    make_cmd.add_argument('--sample', type=Path, help='use this script JSON instead of asking Gemini')
    make_cmd.add_argument('--silent', action='store_true', help='skip the narration (timing from word counts)')
    make_cmd.add_argument('--no-music', action='store_true', help='leave out the music bed')
    make_cmd.add_argument('--options', default='', help='the bot\'s choices: theme=<%s> source=<random|ideas|occasion> '
                          'voice=<male|female> music=<auto|warm|tense|off> style=<story|comic> audience=<kids|family|adult>' % '|'.join(script.THEMES))
    make_cmd.add_argument('--out', type=Path, default=ROOT / 'out')
    make_cmd.add_argument('--public', type=Path, default=ROOT / 'remotion' / 'public')
    send = commands.add_parser('send', help='send a rendered Reel (and its cover) to Telegram')
    send.add_argument('folder', type=Path, help='the Reel folder, e.g. out/1')
    send.add_argument('video', type=Path)
    send.add_argument('--cover', type=Path)
    post = commands.add_parser('publish', help='post a rendered Reel to Instagram and YouTube (whichever is set up)')
    post.add_argument('folder', type=Path)
    post.add_argument('video', type=Path)
    post.add_argument('--platforms', default='', help='comma-separated: instagram,youtube,facebook,carousel,instagram_trial')
    post.add_argument('--video-b', type=Path, help='the second-hook version, for the Instagram trial Reel')
    post.add_argument('--now', action='store_true', help='post now even when POST_AT_PEAK would wait for the best time')
    queued = commands.add_parser('publish-queued', help='publish Instagram uploads whose time has come')
    queued.add_argument('folder', type=Path)
    slides = commands.add_parser('slides', help='cut carousel slides from a rendered Reel')
    slides.add_argument('folder', type=Path)
    slides.add_argument('video', type=Path)
    comp = commands.add_parser('compile', help='join Reels into the weekly compilation')
    comp.add_argument('list', type=Path, help='JSON: {"intro": path, "outro": path, "reels": [{"video", "folder"}]}')
    comp.add_argument('out', type=Path)
    comp.add_argument('--post', action='store_true', help='upload it to YouTube')
    comp.add_argument('--reuse', action='store_true', help='upload an already joined video (its .txt has the title and chapters)')
    ideas = commands.add_parser('ideas', help='send next-lesson ideas from comments and trends to Telegram')
    ideas.add_argument('--out', type=Path, default=ROOT / 'out' / 'ideas.json')
    commands.add_parser('refresh-token', help='renew the Instagram token')
    commands.add_parser('youtube-check', help='check the YouTube sign-in; save a renewed token; warn before it ends')
    commands.add_parser('report', help='send the weekly numbers to Telegram')
    posted_cmd = commands.add_parser('posted', help='exit 0 when a receipt (publish.json) shows the Reel went out')
    posted_cmd.add_argument('receipt', type=Path)
    qc = commands.add_parser('check', help='quality-check a rendered Reel (length, sound, text and framing)')
    qc.add_argument('folder', type=Path)
    qc.add_argument('video', type=Path)
    topic = commands.add_parser('topic', help="print a Reel's lesson")
    topic.add_argument('folder', type=Path)
    topic.add_argument('--style', action='store_true', help="print the Reel's style (story or comic) instead")
    commands.add_parser('sounds', help='regenerate the sound effects in remotion/public/sfx')
    args = parser.parse_args(argv)

    if args.command == 'make':
        args.count = max(1, min(args.count, 5))
        chosen = parse_options(args.options)
        args.theme, args.source, args.music = chosen.get('theme', ''), chosen.get('source', ''), chosen.get('music', 'auto')
        args.style = style_of(chosen)
        args.audience = audience_of(chosen)
        if args.style == 'comic' and args.series:
            print('Two-part stories are story Reels; making a story series')
        if args.music == 'off':
            args.no_music = True
        if chosen.get('voice'):
            os.environ['NARRATOR'] = chosen['voice']
        if chosen:
            print('Options:', ' '.join(f'{k}={v}' for k, v in chosen.items()))
        make(args)
    elif args.command == 'sounds':
        from . import sounds
        print(sounds.write_effects(ROOT / 'remotion' / 'public' / 'sfx'))
    elif args.command == 'publish':
        at = None if args.now or growth.post_now() else growth.next_time(growth.best_slot())
        receipt = publish.publish(args.folder, args.video, [p for p in args.platforms.split(',') if p] or None,
                                  video_b=args.video_b, publish_at=at)
        story = json.loads((args.folder / 'script.json').read_text(encoding='utf-8'))
        telegram.send_message(publish.summary(story, receipt))
        return 1 if any(r.get('status') == 'failed' for r in receipt['platforms'].values()) else 0
    elif args.command == 'publish-queued':
        receipt, done, failed = publish.publish_queued(args.folder)
        if done or failed:
            story = json.loads((args.folder / 'script.json').read_text(encoding='utf-8'))
            text = publish.summary(story, receipt)
            if failed:
                # the upload cannot be retried from here (Instagram keeps it for 24 hours only): say so, loudly
                text = ('⚠️ The scheduled Instagram post did not go out.\n' + text +
                        '\n\nPost it by hand in the Instagram app: the copy button under the Reel has the caption.')
                print(f"::error::Scheduled Instagram post failed: {'; '.join(receipt['platforms'][n].get('error', '') for n in failed)}")
            telegram.send_message(text)
        print('still waiting' if publish.waiting(receipt) else 'failed' if failed else 'done')
    elif args.command == 'posted':
        receipt = json.loads(args.receipt.read_text(encoding='utf-8')) if args.receipt.exists() else {}
        sys.exit(0 if publish.posted(receipt) else 1)
    elif args.command == 'slides':
        print([str(x) for x in carousel.slides(args.folder, args.video)])
    elif args.command == 'compile':
        return compile_week(args)
    elif args.command == 'ideas':
        found = growth.ideas()
        growth.remember_ideas(found)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(found, ensure_ascii=False, indent=2), encoding='utf-8')
        run = os.getenv('GITHUB_RUN_ID', '')
        rows = [[(str(n), f'idea:{run}:{n - 1}') for n in range(1, len(found['ideas']) + 1)]] if run and found['ideas'] else None
        telegram.send_message(growth.ideas_message(found), telegram.buttons(rows) if rows else None)
    elif args.command == 'youtube-check':
        return youtube_check()
    elif args.command == 'refresh-token':
        token, days = growth.refresh_token()
        print(f'::add-mask::{token}')
        Path(os.getenv('TOKEN_FILE', 'token.txt')).write_text(token, encoding='utf-8')
        print(f'Instagram token renewed for {days} days')
    elif args.command == 'check':
        quality.check(args.folder, args.video)
    elif args.command == 'report':
        telegram.send_message(report.weekly())
    elif args.command == 'topic':
        story = json.loads((args.folder / 'script.json').read_text(encoding='utf-8'))
        if args.style:
            audience = story.get('audience')
            print(story.get('style', 'story') + (f' audience={audience}' if story.get('style') == 'comic' and audience else ''))
        else:
            print(story['topic'])
    else:
        story = json.loads((args.folder / 'script.json').read_text(encoding='utf-8'))
        record_path = args.folder / 'voice-record.json'
        record = json.loads(record_path.read_text(encoding='utf-8')) if record_path.exists() else {}
        if args.cover and args.cover.exists():
            telegram.send_file('sendPhoto', 'photo', args.cover, 'image/jpeg', f"Cover: {story['title']}")
        copy = publish.copy_texts(story)
        keys = telegram.review_buttons(os.getenv('GITHUB_RUN_ID', ''), args.folder.name, copy,
                                       actions=os.getenv('AUTO_POST', '').strip() != 'true')
        telegram.send_file('sendVideo', 'video', args.video, 'video/mp4', caption(story, record, args.folder),
                           {'reply_markup': keys} if keys else None)
        long_caption = telegram.copy_message(copy)
        if long_caption:
            telegram.send_message(long_caption, html=True)
        sheet = args.folder / 'sheet.jpg'  # the frame scan's contact sheet (reel/scan.py)
        if sheet.exists():
            telegram.send_file('sendPhoto', 'photo', sheet, 'image/jpeg', '🎞 One frame a second')
    return 0


if __name__ == '__main__':
    sys.exit(main())
