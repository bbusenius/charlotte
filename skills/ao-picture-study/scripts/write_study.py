#!/usr/bin/env python3
"""Persist one AO picture study and link it from its curriculum entrypoint."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml


INDEX_TEMPLATE = """---
id: ao-picture-study
subject: Art
---

# AmblesideOnline Picture Study

## Studies
"""

NON_ANCHOR_HOSTS = (
    "amblesideonline.org",
    "grokipedia.com",
    "wikimedia.org",
    "wikipedia.org",
)


def parse_source_spec(value: str) -> tuple[str, str]:
    if "|" not in value:
        raise argparse.ArgumentTypeError(
            "source must be '<descriptive label>|<https URL>'"
        )
    label, url = (part.strip() for part in value.split("|", 1))
    parsed = urlparse(url)
    if not label or parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise argparse.ArgumentTypeError(
            "source must be '<descriptive label>|<https URL>'"
        )
    return label, url


def is_discovery_host(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(
        host == blocked or host.endswith(f".{blocked}")
        for blocked in NON_ANCHOR_HOSTS
    )


def slugify(value: str, limit: int = 80) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
    return slug[:limit].rstrip("-") or "picture"


def study_path_for(entrypoint: Path, artist: str, title: str) -> Path:
    return entrypoint.parent / "artists" / slugify(artist) / f"{slugify(title)}.md"


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def read_frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise SystemExit(f"existing study has no YAML frontmatter: {path}")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise SystemExit(f"existing study has malformed YAML frontmatter: {path}")
    data = yaml.safe_load(parts[1]) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"existing study frontmatter is not a mapping: {path}")
    return data


def render_study(
    *,
    curriculum_id: str,
    artist: str,
    artist_details: str,
    title: str,
    artwork_date: str,
    ao_url: str,
    image_name: str,
    image_source: str,
    transcript: str,
    anchor_sources: list[tuple[str, str]],
    research_sources: list[tuple[str, str]],
) -> str:
    frontmatter: dict[str, Any] = {
        "curriculum": curriculum_id,
        "artist": artist,
        "title": title,
        "artwork_date": artwork_date,
        "image": image_name,
        "image_source": image_source,
        "ao_url": ao_url,
    }
    if artist_details:
        frontmatter["artist_details"] = artist_details
    yaml_text = yaml.safe_dump(
        frontmatter, sort_keys=False, allow_unicode=True
    ).strip()

    sources = [("AO-selected work", ao_url), ("Artwork reproduction", image_source)]
    sources.extend(anchor_sources)
    sources.extend(research_sources)
    seen: set[str] = set()
    source_lines: list[str] = []
    for label, url in sources:
        if not url or url in seen:
            continue
        seen.add(url)
        source_lines.append(f"- [{label}]({url})")

    return (
        f"---\n{yaml_text}\n---\n\n"
        f"# {title}\n\n"
        f"![{title}]({image_name})\n\n"
        f"## Picture study\n\n{transcript.strip()}\n\n"
        f"## Sources\n\n" + "\n".join(source_lines) + "\n"
    )


def update_index(
    entrypoint: Path,
    study_path: Path,
    artist: str,
    title: str,
    artwork_date: str,
) -> bool:
    if entrypoint.exists():
        text = entrypoint.read_text(encoding="utf-8")
    else:
        text = INDEX_TEMPLATE

    relative = study_path.relative_to(entrypoint.parent).as_posix()
    if f"]({relative})" in text:
        if not entrypoint.exists():
            atomic_write(entrypoint, text.rstrip() + "\n")
        return False

    if "## Studies" not in text:
        text = text.rstrip() + "\n\n## Studies\n"
    line = f"- [{artist} — {title}]({relative}) — {artwork_date}"
    atomic_write(entrypoint, text.rstrip() + "\n" + line + "\n")
    return True


def write_study(
    *,
    entrypoint: Path,
    curriculum_id: str,
    artist: str,
    artist_details: str,
    title: str,
    artwork_date: str,
    ao_url: str,
    image: Path,
    image_source: str,
    transcript: str,
    anchor_sources: list[tuple[str, str]],
    research_sources: list[tuple[str, str]],
) -> dict[str, Any]:
    if not image.is_file():
        raise SystemExit(f"artwork image not found: {image}")
    if not transcript.strip():
        raise SystemExit("picture-study transcript is empty")
    if not anchor_sources:
        raise SystemExit("at least one tier-1/2 anchor source is required")
    rejected = [url for _label, url in anchor_sources if is_discovery_host(url)]
    if rejected:
        raise SystemExit(
            "discovery sources cannot be anchor sources: " + ", ".join(rejected)
        )

    study_path = study_path_for(entrypoint, artist, title)
    artist_dir = study_path.parent
    image_suffix = image.suffix.lower() or ".jpg"
    image_path = artist_dir / f"{slugify(title)}{image_suffix}"
    created = not study_path.exists()

    if study_path.exists():
        existing = read_frontmatter(study_path)
        expected = {
            "curriculum": curriculum_id,
            "artist": artist,
            "title": title,
        }
        mismatches = [
            key for key, value in expected.items() if existing.get(key) != value
        ]
        if mismatches:
            raise SystemExit(
                f"existing study conflicts on {', '.join(mismatches)}: {study_path}"
            )
        existing_image = existing.get("image")
        if not existing_image:
            raise SystemExit(f"existing study has no image field: {study_path}")
        image_path = (study_path.parent / str(existing_image)).resolve()
        if image_path.parent != study_path.parent.resolve():
            raise SystemExit(f"existing study image escapes artist directory: {study_path}")

    artist_dir.mkdir(parents=True, exist_ok=True)
    image_created = not image_path.exists()
    if image_created:
        temporary_image = image_path.with_suffix(image_path.suffix + ".tmp")
        shutil.copy2(image, temporary_image)
        temporary_image.replace(image_path)

    if created:
        markdown = render_study(
            curriculum_id=curriculum_id,
            artist=artist,
            artist_details=artist_details,
            title=title,
            artwork_date=artwork_date,
            ao_url=ao_url,
            image_name=image_path.name,
            image_source=image_source,
            transcript=transcript,
            anchor_sources=anchor_sources,
            research_sources=research_sources,
        )
        atomic_write(study_path, markdown)

    index_updated = update_index(
        entrypoint, study_path, artist, title, artwork_date
    )
    return {
        "ok": True,
        "created": created,
        "image_created": image_created,
        "index_updated": index_updated,
        "curriculum_entrypoint": str(entrypoint),
        "study_path": str(study_path),
        "image_path": str(image_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--curriculum-entrypoint", required=True, type=Path)
    parser.add_argument("--curriculum-id", default="ao-picture-study")
    parser.add_argument("--artist", required=True)
    parser.add_argument("--artist-details", default="")
    parser.add_argument("--title", required=True)
    parser.add_argument("--date", required=True, dest="artwork_date")
    parser.add_argument("--ao-url", required=True)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--image-source", required=True)
    parser.add_argument("--transcript", required=True, type=Path)
    parser.add_argument(
        "--anchor-source",
        action="append",
        default=[],
        type=parse_source_spec,
        help="repeatable tier-1/2 source as '<descriptive label>|<https URL>'",
    )
    parser.add_argument(
        "--research-source",
        action="append",
        default=[],
        type=parse_source_spec,
        help="repeatable supplementary source as '<descriptive label>|<https URL>'",
    )
    args = parser.parse_args()

    if not args.transcript.is_file():
        raise SystemExit(f"transcript not found: {args.transcript}")
    result = write_study(
        entrypoint=args.curriculum_entrypoint,
        curriculum_id=args.curriculum_id,
        artist=args.artist,
        artist_details=args.artist_details,
        title=args.title,
        artwork_date=args.artwork_date,
        ao_url=args.ao_url,
        image=args.image,
        image_source=args.image_source,
        transcript=args.transcript.read_text(encoding="utf-8"),
        anchor_sources=args.anchor_source,
        research_sources=args.research_source,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
