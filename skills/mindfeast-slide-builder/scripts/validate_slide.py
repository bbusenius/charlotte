#!/usr/bin/env python3
"""Validate a MindFeast slide folder."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


VALID_ORIENTATIONS = {"landscape", "portrait"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_TYPES = {
    "question",
    "essay",
    "gratitude",
    "informational",
    "narration",
    "conversation",
}
FREE_FORM_TYPES = {"essay", "gratitude", "narration", "conversation"}
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".ogg", ".flac", ".aac"}
TEXT_EXTENSIONS = {".txt"}
# Files checked strictly for the new types only; other types keep the
# general image/audio checks below.
STRICT_FILES = {
    "narration": {
        "audio": AUDIO_EXTENSIONS,
        "script": TEXT_EXTENSIONS,
        "passage": TEXT_EXTENSIONS,
    },
    "conversation": {"context": TEXT_EXTENSIONS},
}
TEXT_FIELDS = {"script", "passage", "context"}
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def parse_frontmatter(markdown: str) -> tuple[dict, str]:
    text = markdown.lstrip()
    if not text.startswith("---"):
        raise ValueError("missing YAML frontmatter opener")
    parts = text[3:].split("---", 1)
    if len(parts) != 2:
        raise ValueError("missing YAML frontmatter closer")
    raw_yaml, body = parts[0].strip(), parts[1].strip()
    if yaml is None:
        raise ValueError("PyYAML is required for validation")
    data = yaml.safe_load(raw_yaml) or {}
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a YAML mapping")
    return data, body


def validate(slide_dir: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not slide_dir.is_dir():
        return [f"not a directory: {slide_dir}"], warnings

    slide_md = slide_dir / "slide.md"
    if not slide_md.is_file():
        return ["slide.md missing"], warnings

    try:
        data, body = parse_frontmatter(slide_md.read_text(encoding="utf-8"))
    except Exception as exc:
        return [str(exc)], warnings

    slide_id = data.get("id")
    if not slide_id:
        errors.append("id missing")
    elif slide_id != slide_dir.name:
        errors.append(f"id '{slide_id}' does not match folder '{slide_dir.name}'")
    elif not SLUG_RE.match(str(slide_id)):
        errors.append("id must use lowercase ASCII letters, digits, and hyphens")

    if slide_dir.name.startswith(".") or "/" in slide_dir.name or "\\" in slide_dir.name:
        errors.append("invalid slide folder name")

    raw_type = str(data.get("type", "question")).strip().lower()
    if not data.get("type"):
        errors.append("type missing")
        slide_type = "question"
    elif raw_type in VALID_TYPES:
        slide_type = raw_type
    else:
        slide_type = "question"
        warnings.append("legacy type value is treated as question; move category metadata to subject")

    if slide_type == "question" and not data.get("answer"):
        errors.append("answer missing")

    image = data.get("image")
    audio = data.get("audio")
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", body) if part.strip()]

    if slide_type in {"question", "essay", "gratitude"} and not image and not audio:
        errors.append("slide must declare image or audio")
    if slide_type == "informational" and not paragraphs and not image and not audio:
        errors.append("informational slide must include text, image, or audio")

    if slide_type == "narration":
        if sum(key in data for key in ("audio", "script", "passage")) != 1:
            errors.append(
                "narration must declare exactly one of audio, script, or passage"
            )
    if slide_type == "conversation":
        intent = data.get("intent")
        if not isinstance(intent, str) or not intent.strip():
            errors.append("intent must be a non-blank string")
        turns = data.get("turns")
        if type(turns) is not int or turns < 1:
            errors.append("turns must be an integer >= 1")
        if "context" not in data:
            errors.append("context missing")

    strict_files = STRICT_FILES.get(slide_type, {})
    for key, filename in (("image", image), ("audio", audio)):
        if key in strict_files:
            continue
        if filename:
            if Path(str(filename)).name != str(filename):
                errors.append(f"{key} must be a filename, not a path")
            elif not (slide_dir / str(filename)).is_file():
                errors.append(f"{key} file missing: {filename}")

    for key, extensions in strict_files.items():
        if key not in data:
            continue
        filename = data[key]
        if not isinstance(filename, str) or not filename.strip():
            errors.append(f"{key} must be a non-blank filename")
            continue
        if Path(filename).name != filename or "/" in filename or "\\" in filename:
            errors.append(f"{key} must be a filename, not a path")
            continue
        file_path = slide_dir / filename
        if not file_path.is_file():
            errors.append(f"{key} file missing: {filename}")
            continue
        if file_path.suffix.lower() not in extensions:
            warnings.append(f"{key} file has an unknown extension: {filename}")
        if key in TEXT_FIELDS:
            try:
                text = file_path.read_text(encoding="utf-8")
            except (UnicodeError, OSError):
                errors.append(f"{key} file must be readable UTF-8 text: {filename}")
            else:
                if not text.strip():
                    errors.append(f"{key} file is blank: {filename}")

    orientation = str(data.get("orientation", "landscape")).strip().lower()
    if orientation not in VALID_ORIENTATIONS:
        errors.append("orientation must be landscape or portrait")

    difficulty = str(data.get("difficulty", "easy")).strip().lower()
    if difficulty not in VALID_DIFFICULTIES:
        warnings.append("difficulty is usually easy, medium, or hard")

    accept = data.get("accept", [])
    if accept is None:
        accept = []
    if not isinstance(accept, list):
        errors.append("accept must be a list")
    elif slide_type in FREE_FORM_TYPES | {"informational"} and accept:
        warnings.append(f"{slide_type} slides ignore accept")

    choices = data.get("choices")
    if choices is not None:
        if slide_type in FREE_FORM_TYPES | {"informational"}:
            warnings.append(f"{slide_type} slides ignore choices")
        elif not isinstance(choices, list):
            errors.append("choices must be a list")
        else:
            normalized = [str(choice).strip().casefold() for choice in choices]
            if len(normalized) != len(set(normalized)):
                warnings.append("choices contains duplicates")
            answer = str(data.get("answer", "")).strip().casefold()
            accept_norm = {str(item).strip().casefold() for item in accept}
            if answer and answer not in normalized and not accept_norm.intersection(normalized):
                warnings.append("choices does not include the answer or an accepted variant")
            if orientation == "landscape" and len(choices) >= 4:
                warnings.append("four or more choices may fit better in portrait")

    if slide_type in FREE_FORM_TYPES | {"informational"} and data.get("answer"):
        warnings.append(f"{slide_type} slides ignore answer")

    if slide_type in FREE_FORM_TYPES | {"question"} and not paragraphs:
        label = "question" if slide_type in {"question", "conversation"} else "prompt"
        errors.append(f"{label} body missing")
    elif paragraphs and len(paragraphs[0]) > 140:
        label = "text" if slide_type == "informational" else "question"
        warnings.append(f"{label} is long for the lock-screen panel")
    if slide_type == "informational" and orientation == "landscape" and paragraphs:
        if len(paragraphs[0]) > 90:
            warnings.append("dense informational text may fit better in portrait")
    if slide_type in FREE_FORM_TYPES and orientation == "landscape" and paragraphs:
        if len(paragraphs[0]) > 110:
            warnings.append(f"long {slide_type} prompts may fit better in portrait")
    if slide_type == "question" and len(paragraphs) > 1 and len(paragraphs[1]) > 180:
        warnings.append("hint is long for the lock-screen panel")
    if slide_type in FREE_FORM_TYPES and len(paragraphs) > 1:
        warnings.append(f"{slide_type} slides use only the first body paragraph as the prompt")
    if slide_type == "informational" and len(paragraphs) > 1:
        warnings.append("informational slides display only the first body paragraph")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("slide_dirs", nargs="+", type=Path)
    args = parser.parse_args()

    failed = False
    for slide_dir in args.slide_dirs:
        errors, warnings = validate(slide_dir)
        label = str(slide_dir)
        if errors:
            failed = True
            print(f"{label}: FAIL")
            for error in errors:
                print(f"  error: {error}")
        else:
            print(f"{label}: OK")
        for warning in warnings:
            print(f"  warning: {warning}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
