#!/usr/bin/env python3
"""Create a MindFeast slide folder from command-line fields."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path


SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
VALID_ORIENTATIONS = {"landscape", "portrait"}
VALID_TYPES = {"question", "essay", "gratitude", "informational", "narration", "conversation"}


def yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def quote_intent(value: str) -> str:
    # Match the app writer, including escaping the frontmatter separator.
    escapes = {"\\": "\\\\", '"': '\\"', "\n": "\\n", "\r": "\\r", "\t": "\\t", "-": "\\u002d"}
    escaped = []
    for char in value:
        if char in escapes:
            escaped.append(escapes[char])
        elif ord(char) < 0x20 or ord(char) in {0x7F, 0x85, 0x2028, 0x2029}:
            escaped.append(f"\\u{ord(char):04x}")
        else:
            escaped.append(char)
    return '"' + "".join(escaped) + '"'


def read_markdown(args: argparse.Namespace, field: str) -> str | None:
    text = getattr(args, f"{field}_text")
    source = getattr(args, f"{field}_file")
    if source is not None:
        try:
            text = source.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise SystemExit(f"cannot read --{field}-file as UTF-8: {exc}") from exc
    if text is not None and not text.strip():
        raise SystemExit(f"--{field}-text/--{field}-file must contain non-blank Markdown")
    return text


def add_list(lines: list[str], key: str, values: list[str]) -> None:
    if not values:
        return
    lines.append(f"{key}:")
    for value in values:
        lines.append(f"  - {yaml_quote(value)}")


def copy_media(source: str | None, slide_dir: Path) -> str | None:
    if not source:
        return None
    src = Path(source)
    if not src.is_file():
        raise ValueError(f"media file not found: {source}")
    dest_name = src.name
    if Path(dest_name).name != dest_name:
        raise ValueError(f"invalid media filename: {dest_name}")
    dest = slide_dir / dest_name
    if src.resolve() != dest.resolve():
        shutil.copy2(src, dest)
    return dest_name


def build_markdown(args: argparse.Namespace, image_name: str | None, audio_name: str | None) -> str:
    body_text = (args.text if args.text is not None else args.question or "").strip()
    lines = [
        "---",
        f"id: {args.id}",
        f"type: {args.type}",
    ]
    if args.subject:
        lines.append(f"subject: {args.subject}")
    if image_name:
        lines.append(f"image: {image_name}")
    if audio_name:
        lines.append(f"audio: {audio_name}")
    if args.type == "narration":
        for field in ("script", "passage"):
            if getattr(args, field) is not None:
                lines.append(f"{field}: {field}.md")
    if args.type == "conversation":
        lines.append(f"intent: {quote_intent(args.intent)}")
        lines.append(f"turns: {args.turns}")
        lines.append("context: context.md")
    if args.type == "question":
        lines.append(f"answer: {yaml_quote(args.answer)}")
        add_list(lines, "accept", args.accept)
        add_list(lines, "choices", args.choice)
    lines.append(f"difficulty: {args.difficulty}")
    lines.append(f"orientation: {args.orientation}")
    lines.extend(["---"])
    if body_text:
        lines.extend(["", body_text])
    if args.type == "question" and args.hint:
        lines.extend(["", args.hint.strip()])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="tablet-slides", type=Path)
    parser.add_argument("--id", required=True)
    parser.add_argument("--type", default="question", choices=sorted(VALID_TYPES))
    parser.add_argument("--subject")
    parser.add_argument("--image")
    parser.add_argument("--audio")
    for field in ("script", "passage", "context"):
        source = parser.add_mutually_exclusive_group()
        source.add_argument(f"--{field}-text", help=f"Literal Markdown to write to {field}.md")
        source.add_argument(f"--{field}-file", type=Path, help=f"UTF-8 file to write as {field}.md")
    parser.add_argument("--intent", help="Hidden instructions for the conversation AI")
    parser.add_argument("--turns", type=int, help="Learner/AI reply pairs, at least 1")
    parser.add_argument("--answer")
    parser.add_argument("--accept", action="append", default=[])
    parser.add_argument("--choice", action="append", default=[])
    parser.add_argument("--difficulty", default="easy")
    parser.add_argument("--orientation", required=True)
    parser.add_argument("--question")
    parser.add_argument("--text", help="Display text for informational slides; aliases --question")
    parser.add_argument("--hint")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if not SLUG_RE.match(args.id):
        raise SystemExit("--id must use lowercase ASCII letters, digits, and hyphens")
    if args.orientation not in VALID_ORIENTATIONS:
        raise SystemExit("--orientation must be landscape or portrait")
    body_text = (args.text if args.text is not None else args.question or "").strip()
    for field in ("script", "passage", "context"):
        supplied = getattr(args, f"{field}_text") is not None or getattr(args, f"{field}_file") is not None
        expected_type = "conversation" if field == "context" else "narration"
        if supplied and args.type != expected_type:
            raise SystemExit(f"--{field}-text/--{field}-file require --type {expected_type}")
        setattr(args, field, read_markdown(args, field))
    if args.type != "conversation" and (args.intent is not None or args.turns is not None):
        raise SystemExit("--intent and --turns require --type conversation")
    if args.type == "question":
        if not args.question:
            raise SystemExit("provide --question")
        if not args.answer:
            raise SystemExit("provide --answer")
        if not args.image and not args.audio:
            raise SystemExit("provide --image or --audio")
    elif args.type in {"essay", "gratitude"}:
        if not args.question:
            raise SystemExit("provide --question")
        if not args.image and not args.audio:
            raise SystemExit("provide --image or --audio")
        if args.answer or args.accept or args.choice or args.hint:
            raise SystemExit(
                f"{args.type} slides do not use --answer, --accept, --choice, or --hint"
            )
    elif args.type in {"narration", "conversation"}:
        if not body_text:
            raise SystemExit("provide non-blank --question/--text")
        if args.answer is not None or args.accept or args.choice or args.hint is not None:
            raise SystemExit(
                f"{args.type} slides do not use --answer, --accept, --choice, or --hint"
            )
        if args.type == "narration":
            if sum(value is not None for value in (args.audio, args.script, args.passage)) != 1:
                raise SystemExit("narration requires exactly one of --audio, --script-text/--script-file, or --passage-text/--passage-file")
        else:
            if args.intent is None or not args.intent.strip():
                raise SystemExit("provide non-blank --intent")
            if args.turns is None or args.turns < 1:
                raise SystemExit("--turns must be an integer >= 1")
            if args.context is None:
                raise SystemExit("provide --context-text or --context-file")
        for field in ("image", "audio"):
            source = getattr(args, field)
            if source is not None:
                path = Path(source)
                if not path.is_file():
                    raise SystemExit(f"media file not found: {source}")
                if "\\" in path.name or path.name in {"slide.md", "script.md", "passage.md", "context.md"}:
                    raise SystemExit(f"invalid media filename: {path.name}")
    else:
        if args.answer or args.accept or args.choice or args.hint:
            raise SystemExit("informational slides do not use --answer, --accept, --choice, or --hint")
        if not body_text and not args.image and not args.audio:
            raise SystemExit("informational slides require --text/--question, --image, or --audio")

    slide_dir = args.out / args.id
    slide_md = slide_dir / "slide.md"
    if slide_md.exists() and not args.force:
        raise SystemExit(f"{slide_md} already exists; pass --force to overwrite")

    slide_dir.mkdir(parents=True, exist_ok=True)
    image_name = copy_media(args.image, slide_dir)
    audio_name = copy_media(args.audio, slide_dir)
    for field in ("script", "passage", "context"):
        content = getattr(args, field)
        if content is not None:
            (slide_dir / f"{field}.md").write_text(content, encoding="utf-8")
    slide_md.write_text(build_markdown(args, image_name, audio_name), encoding="utf-8")
    print(slide_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
