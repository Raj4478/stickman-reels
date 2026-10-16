"""Command line.

    python -m reel make [--topic "..."] [--count 3 | --series] [--sample examples/sample.json] [--silent]
    python -m reel send out/1 remotion/out/reel-1.mp4 [--cover out/1/cover.jpg]
    python -m reel publish out/1 remotion/out/reel-1.mp4 [--platforms instagram,youtube]
    python -m reel report        (weekly numbers to Telegram)
    python -m reel topic out/1   (prints the lesson of a Reel, for "Make again")
    python -m reel sounds        (rewrites remotion/public/sfx/*.wav)

`make` writes each Reel to out/<n>/ and its media to remotion/public/reels/<n>/, and lists the numbers in
out/reels.txt for the render step.
"""
import argparse
import json
import os
import sys
from pathlib import Path

from . import build, publish, report, script, sounds, telegram

ROOT = Path(__file__).resolve().parents[1]


def caption(story, record):
    part = f" (भाग {story['part']})" if story.get('part') else ''
    lines = [story['title'] + part, '', story.get('instagram_caption') or story['lesson'], '', ' '.join(story.get('hashtags', []))]
    if record.get('narration') == 'failed':
        lines += ['', '(Preview without narration: ' + record.get('reason', '')[:150] + ')']
    return '\n'.join(lines).strip()


def stories(args):
    if args.sample:
        yield script.clean(json.loads(args.sample.read_text(encoding='utf-8')))
        return
    if args.series:
        first = script.write(args.topic, part='1/2')
        yield first
        summary = {k: first[k] for k in ('topic', 'name', 'title', 'hook', 'lesson')}
        summary['beats'] = [s['line'] for s in first['scenes']]
        yield script.write(first['topic'], part='2/2', previous=summary)
        return
    for _ in range(args.count):
        yield script.write(args.topic)


def make(args):
    made = []
    for n, story in enumerate(stories(args), 1):
        out = args.out / str(n)
        props, record = build.build(story, out, args.public, narrate=not args.silent, music=not args.no_music,
                                    prefix=f'reels/{n}/')
        if not args.sample:
            script.remember(story)
        made.append(str(n))
        print(f"Reel {n}: {story['title']} ({story['topic']}): {len(props['segments'])} segments, "
              f"{props['duration']:.1f}s, narration: {record.get('voice', record.get('narration'))}, "
              f"words: {record.get('word_timing', '-')}, directed: {story.get('directed', '-')}")
    (args.out / 'reels.txt').write_text('\n'.join(made) + '\n', encoding='utf-8')


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
    make_cmd.add_argument('--out', type=Path, default=ROOT / 'out')
    make_cmd.add_argument('--public', type=Path, default=ROOT / 'remotion' / 'public')
    send = commands.add_parser('send', help='send a rendered Reel (and its cover) to Telegram')
    send.add_argument('folder', type=Path, help='the Reel folder, e.g. out/1')
    send.add_argument('video', type=Path)
    send.add_argument('--cover', type=Path)
    post = commands.add_parser('publish', help='post a rendered Reel to Instagram and YouTube (whichever is set up)')
    post.add_argument('folder', type=Path)
    post.add_argument('video', type=Path)
    post.add_argument('--platforms', default='', help='comma-separated: instagram,youtube (default: all set up)')
    commands.add_parser('report', help='send the weekly numbers to Telegram')
    topic = commands.add_parser('topic', help="print a Reel's lesson")
    topic.add_argument('folder', type=Path)
    commands.add_parser('sounds', help='regenerate the sound effects in remotion/public/sfx')
    args = parser.parse_args(argv)

    if args.command == 'make':
        args.count = max(1, min(args.count, 5))
        make(args)
    elif args.command == 'sounds':
        print(sounds.write_effects(ROOT / 'remotion' / 'public' / 'sfx'))
    elif args.command == 'publish':
        receipt = publish.publish(args.folder, args.video, [p for p in args.platforms.split(',') if p] or None)
        story = json.loads((args.folder / 'script.json').read_text(encoding='utf-8'))
        telegram.send_message(publish.summary(story, receipt))
        return 1 if any(r.get('status') == 'failed' for r in receipt['platforms'].values()) else 0
    elif args.command == 'report':
        telegram.send_message(report.weekly())
    elif args.command == 'topic':
        print(json.loads((args.folder / 'script.json').read_text(encoding='utf-8'))['topic'])
    else:
        story = json.loads((args.folder / 'script.json').read_text(encoding='utf-8'))
        record_path = args.folder / 'voice-record.json'
        record = json.loads(record_path.read_text(encoding='utf-8')) if record_path.exists() else {}
        if args.cover and args.cover.exists():
            telegram.send_file('sendPhoto', 'photo', args.cover, 'image/jpeg', f"Cover: {story['title']}")
        keys = telegram.review_buttons(os.getenv('GITHUB_RUN_ID', ''), args.folder.name)
        telegram.send_file('sendVideo', 'video', args.video, 'video/mp4', caption(story, record),
                           {'reply_markup': keys} if keys and os.getenv('AUTO_POST', '').strip() != 'true' else None)
    return 0


if __name__ == '__main__':
    sys.exit(main())
