#!/usr/bin/env python3
"""Create a Homeschool Screen Lock slide folder from command-line fields."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path


SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
VALID_ORIENTATIONS = {"landscape", "portrait"}
VALID_TYPES = {"question", "essay", "informational"}


def yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


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
    if args.type == "question":
        if not args.question:
            raise SystemExit("provide --question")
        if not args.answer:
            raise SystemExit("provide --answer")
        if not args.image and not args.audio:
            raise SystemExit("provide --image or --audio")
    elif args.type == "essay":
        if not args.question:
            raise SystemExit("provide --question")
        if not args.image and not args.audio:
            raise SystemExit("provide --image or --audio")
        if args.answer or args.accept or args.choice or args.hint:
            raise SystemExit("essay slides do not use --answer, --accept, --choice, or --hint")
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
    slide_md.write_text(build_markdown(args, image_name, audio_name), encoding="utf-8")
    print(slide_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
