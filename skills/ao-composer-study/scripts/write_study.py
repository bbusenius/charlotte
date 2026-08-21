#!/usr/bin/env python3
"""Persist one AO composer study and link it from its curriculum entrypoint."""

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
id: ao-composer-study
subject: Music
---

# AmblesideOnline Composer Study

## Studies
"""

NON_ANCHOR_HOSTS = (
    "amblesideonline.org",
    "grokipedia.com",
    "youtube.com",
    "youtu.be",
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
    return slug[:limit].rstrip("-") or "music"


def study_path_for(entrypoint: Path, composer: str, title: str) -> Path:
    return entrypoint.parent / "composers" / slugify(composer) / f"{slugify(title)}.md"


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


def safe_media_path(study_path: Path, value: Any, field: str) -> Path:
    if not value:
        raise SystemExit(f"existing study has no {field} field: {study_path}")
    result = (study_path.parent / str(value)).resolve()
    if result.parent != study_path.parent.resolve():
        raise SystemExit(f"existing study {field} escapes composer directory: {study_path}")
    return result


def render_study(
    *,
    curriculum_id: str,
    composer: str,
    composer_details: str,
    title: str,
    ao_url: str,
    presentation_count: int,
    work_audio_name: str,
    work_image_name: str,
    podcast_audio_name: str,
    podcast_image_name: str,
    transcript: str,
    recording_source: str,
    recording_title: str,
    recording_performer: str,
    recording_duration: float | None,
    anchor_sources: list[tuple[str, str]],
    research_sources: list[tuple[str, str]],
) -> str:
    frontmatter: dict[str, Any] = {
        "curriculum": curriculum_id,
        "composer": composer,
        "title": title,
        "presentation_count": presentation_count,
        "work_audio": work_audio_name,
        "work_image": work_image_name,
        "podcast_audio": podcast_audio_name,
        "podcast_image": podcast_image_name,
        "recording_source": recording_source,
        "ao_url": ao_url,
    }
    if composer_details:
        frontmatter["composer_details"] = composer_details
    if recording_title:
        frontmatter["recording_title"] = recording_title
    if recording_performer:
        frontmatter["recording_performer"] = recording_performer
    if recording_duration is not None:
        frontmatter["recording_duration_seconds"] = recording_duration
    yaml_text = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).strip()

    sources = [("AO-selected work", ao_url), ("Recording", recording_source)]
    sources.extend(anchor_sources)
    sources.extend(research_sources)
    seen: set[str] = set()
    source_lines = []
    for label, url in sources:
        if not url or url in seen:
            continue
        seen.add(url)
        source_lines.append(f"- [{label}]({url})")

    performer = f" — {recording_performer}" if recording_performer else ""
    return (
        f"---\n{yaml_text}\n---\n\n"
        f"# {title}\n\n"
        f"![Generated study image]({podcast_image_name})\n\n"
        f"## Composer study\n\n{transcript.strip()}\n\n"
        f"## Listening\n\n"
        f"[{recording_title or title}{performer}]({work_audio_name})\n\n"
        f"## Sources\n\n" + "\n".join(source_lines) + "\n"
    )


def update_index(entrypoint: Path, study_path: Path, composer: str, title: str) -> bool:
    text = entrypoint.read_text(encoding="utf-8") if entrypoint.exists() else INDEX_TEMPLATE
    relative = study_path.relative_to(entrypoint.parent).as_posix()
    if f"]({relative})" in text:
        if not entrypoint.exists():
            atomic_write(entrypoint, text.rstrip() + "\n")
        return False
    if "## Studies" not in text:
        text = text.rstrip() + "\n\n## Studies\n"
    atomic_write(entrypoint, text.rstrip() + f"\n- [{composer} — {title}]({relative})\n")
    return True


def write_study(
    *,
    entrypoint: Path,
    curriculum_id: str,
    composer: str,
    composer_details: str,
    title: str,
    ao_url: str,
    presentation_count: int,
    work_audio: Path,
    work_image: Path,
    podcast_audio: Path,
    podcast_image: Path,
    transcript: str,
    recording_source: str,
    recording_title: str,
    recording_performer: str,
    recording_duration: float | None,
    anchor_sources: list[tuple[str, str]],
    research_sources: list[tuple[str, str]],
) -> dict[str, Any]:
    incoming = {
        "work_audio": work_audio,
        "work_image": work_image,
        "podcast_audio": podcast_audio,
        "podcast_image": podcast_image,
    }
    missing = [f"{field}: {path}" for field, path in incoming.items() if not path.is_file()]
    if missing:
        raise SystemExit("study media not found: " + ", ".join(missing))
    if not transcript.strip():
        raise SystemExit("composer-study transcript is empty")
    if presentation_count < 1:
        raise SystemExit("presentation_count must be at least 1")
    if not anchor_sources:
        raise SystemExit("at least one tier-1/2 anchor source is required")
    rejected = [url for _label, url in anchor_sources if is_discovery_host(url)]
    if rejected:
        raise SystemExit("discovery sources cannot be anchor sources: " + ", ".join(rejected))

    study_path = study_path_for(entrypoint, composer, title)
    stem = slugify(title)
    planned = {
        "work_audio": study_path.parent / f"{stem}-recording{work_audio.suffix.lower()}",
        "work_image": study_path.parent / f"{stem}-work-image{work_image.suffix.lower()}",
        "podcast_audio": study_path.parent / f"{stem}-podcast{podcast_audio.suffix.lower()}",
        "podcast_image": study_path.parent / f"{stem}-podcast-image{podcast_image.suffix.lower()}",
    }
    created = not study_path.exists()
    if study_path.exists():
        existing = read_frontmatter(study_path)
        expected = {"curriculum": curriculum_id, "composer": composer, "title": title}
        mismatches = [key for key, value in expected.items() if existing.get(key) != value]
        if mismatches:
            raise SystemExit(f"existing study conflicts on {', '.join(mismatches)}: {study_path}")
        planned = {
            field: safe_media_path(study_path, existing.get(field), field)
            for field in incoming
        }

    study_path.parent.mkdir(parents=True, exist_ok=True)
    media_created: dict[str, bool] = {}
    for field, source in incoming.items():
        destination = planned[field]
        media_created[field] = not destination.exists()
        if media_created[field]:
            temporary = destination.with_suffix(destination.suffix + ".tmp")
            shutil.copy2(source, temporary)
            temporary.replace(destination)

    if created:
        atomic_write(
            study_path,
            render_study(
                curriculum_id=curriculum_id,
                composer=composer,
                composer_details=composer_details,
                title=title,
                ao_url=ao_url,
                presentation_count=presentation_count,
                work_audio_name=planned["work_audio"].name,
                work_image_name=planned["work_image"].name,
                podcast_audio_name=planned["podcast_audio"].name,
                podcast_image_name=planned["podcast_image"].name,
                transcript=transcript,
                recording_source=recording_source,
                recording_title=recording_title,
                recording_performer=recording_performer,
                recording_duration=recording_duration,
                anchor_sources=anchor_sources,
                research_sources=research_sources,
            ),
        )

    result: dict[str, Any] = {
        "ok": True,
        "created": created,
        "media_created": media_created,
        "index_updated": update_index(entrypoint, study_path, composer, title),
        "curriculum_entrypoint": str(entrypoint),
        "study_path": str(study_path),
    }
    result.update({f"{field}_path": str(path) for field, path in planned.items()})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--curriculum-entrypoint", required=True, type=Path)
    parser.add_argument("--curriculum-id", default="ao-composer-study")
    parser.add_argument("--composer", required=True)
    parser.add_argument("--composer-details", default="")
    parser.add_argument("--title", required=True)
    parser.add_argument("--ao-url", required=True)
    parser.add_argument("--presentation-count", type=int, default=1)
    parser.add_argument("--work-audio", required=True, type=Path)
    parser.add_argument("--work-image", required=True, type=Path)
    parser.add_argument("--podcast-audio", required=True, type=Path)
    parser.add_argument("--podcast-image", required=True, type=Path)
    parser.add_argument("--transcript", required=True, type=Path)
    parser.add_argument("--recording-source", required=True)
    parser.add_argument("--recording-title", default="")
    parser.add_argument("--recording-performer", default="")
    parser.add_argument("--recording-duration", type=float)
    parser.add_argument("--anchor-source", action="append", default=[], type=parse_source_spec)
    parser.add_argument("--research-source", action="append", default=[], type=parse_source_spec)
    args = parser.parse_args()
    result = write_study(
        entrypoint=args.curriculum_entrypoint,
        curriculum_id=args.curriculum_id,
        composer=args.composer,
        composer_details=args.composer_details,
        title=args.title,
        ao_url=args.ao_url,
        presentation_count=args.presentation_count,
        work_audio=args.work_audio,
        work_image=args.work_image,
        podcast_audio=args.podcast_audio,
        podcast_image=args.podcast_image,
        transcript=args.transcript.read_text(encoding="utf-8"),
        recording_source=args.recording_source,
        recording_title=args.recording_title,
        recording_performer=args.recording_performer,
        recording_duration=args.recording_duration,
        anchor_sources=args.anchor_source,
        research_sources=args.research_source,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
