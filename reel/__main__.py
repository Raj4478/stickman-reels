"""Command line.

    python -m reel make [--topic "..."] [--sample examples/sample.json] [--silent]
    python -m reel send remotion/out/reel.mp4
"""
import argparse
import json
import sys
from pathlib import Path

from . import build, script, telegram

ROOT = Path(__file__).resolve().parents[1]


def caption(story, record):
    lines = [story['title'], '', story.get('instagram_caption') or story['lesson'], '', ' '.join(story.get('hashtags', []))]
    if record.get('narration') == 'failed':
        lines += ['', '(Preview without narration: ' + record.get('reason', '')[:150] + ')']
    return '\n'.join(lines).strip()


def main(argv=None):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # Hindi titles on a Windows console
    parser = argparse.ArgumentParser(prog='reel')
    commands = parser.add_subparsers(dest='command', required=True)
    make = commands.add_parser('make', help='write the script, record the narration and build props.json')
    make.add_argument('--topic', default='', help='the life lesson (default: a random line of topics.txt)')
    make.add_argument('--sample', type=Path, help='use this script JSON instead of asking Gemini')
    make.add_argument('--silent', action='store_true', help='skip the narration (timing from word counts)')
    make.add_argument('--out', type=Path, default=ROOT / 'out')
    make.add_argument('--public', type=Path, default=ROOT / 'remotion' / 'public')
    send = commands.add_parser('send', help='send a rendered video to Telegram')
    send.add_argument('video', type=Path)
    send.add_argument('--out', type=Path, default=ROOT / 'out')
    args = parser.parse_args(argv)

    if args.command == 'make':
        story = script.clean(json.loads(args.sample.read_text(encoding='utf-8'))) if args.sample else script.write(args.topic)
        props, record = build.build(story, args.out, args.public, narrate=not args.silent)
        print(f"{story['title']} ({story['topic']}): {len(props['segments'])} segments, {props['duration']:.1f}s, "
              f"narration: {record.get('voice', record.get('narration'))}")
        return 0
    story = json.loads((args.out / 'script.json').read_text(encoding='utf-8'))
    record_path = args.out / 'voice-record.json'
    record = json.loads(record_path.read_text(encoding='utf-8')) if record_path.exists() else {}
    telegram.send_video(args.video, caption(story, record))
    return 0


if __name__ == '__main__':
    sys.exit(main())
