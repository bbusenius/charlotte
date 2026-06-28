#!/usr/bin/env python3
"""Transcribe an audiobook into markdown.

Requires ffmpeg/ffprobe on PATH. Chaptered files are transcribed chapter by
chapter; unchaptered files are treated as one source-length chapter.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


REQUIRED_TOOLS = ("ffmpeg", "ffprobe")


@dataclass(frozen=True)
class Chapter:
    index: int
    title: str
    start: float
    end: float
    synthetic: bool = False

    @property
    def duration(self) -> float:
        return self.end - self.start


def run_json(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def log(message: str) -> None:
    print(message, flush=True)


def require_tools() -> None:
    missing = [tool for tool in REQUIRED_TOOLS if not shutil.which(tool)]
    if missing:
        names = ", ".join(missing)
        raise SystemExit(
            f"Missing required audio tool(s): {names}. Install ffmpeg, which "
            "provides both ffmpeg and ffprobe."
        )


def probe_audiobook(path: Path) -> tuple[dict[str, str], list[Chapter]]:
    data = run_json(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_chapters",
            str(path),
        ]
    )
    tags = data.get("format", {}).get("tags", {})
    chapters = []
    for idx, item in enumerate(data.get("chapters", [])):
        title = item.get("tags", {}).get("title", f"Chapter {idx + 1}").strip()
        chapters.append(
            Chapter(
                index=idx,
                title=title,
                start=float(item["start_time"]),
                end=float(item["end_time"]),
            )
    )
    if not chapters:
        duration = float(data.get("format", {}).get("duration", "0"))
        chapters.append(
            Chapter(
                index=0,
                title=tags.get("title", path.stem),
                start=0.0,
                end=duration,
                synthetic=True,
            )
        )
    return tags, chapters


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "chapter"


def format_timestamp(seconds: float) -> str:
    total = round(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def markdown_heading(level: int, text: str) -> str:
    return f"{'#' * level} {text.strip()}"


def display_chapter_title(title: str) -> str:
    match = re.match(r"^(\d+)\.\s*(.+)$", title.strip())
    if match:
        return f"Chapter {match.group(1)}: {match.group(2)}"
    return title.strip()


def chapter_number(chapter: Chapter) -> int:
    return chapter.index + 1


def extract_chapter_audio(source: Path, chapter: Chapter, destination: Path) -> None:
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{chapter.start:.3f}",
            "-i",
            str(source),
            "-t",
            f"{chapter.duration:.3f}",
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(destination),
        ]
    )


def audio_for_transcription(source: Path, chapter: Chapter, destination: Path) -> Path:
    if chapter.synthetic:
        log("  Using source audio directly")
        return source
    log(f"  Extracting audio: {destination}")
    extract_chapter_audio(source, chapter, destination)
    return destination


def paragraphize(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    paragraphs: list[str] = []
    current: list[str] = []
    current_len = 0
    for sentence in sentences:
        current.append(sentence)
        current_len += len(sentence)
        if current_len >= 700:
            paragraphs.append(" ".join(current).strip())
            current = []
            current_len = 0
    if current:
        paragraphs.append(" ".join(current).strip())
    return "\n\n".join(paragraphs)


def title_case_heading(text: str) -> str:
    small_words = {
        "a",
        "an",
        "and",
        "as",
        "at",
        "but",
        "by",
        "for",
        "from",
        "in",
        "of",
        "on",
        "or",
        "the",
        "to",
    }
    words = text.strip().strip(".").split()
    formatted = []
    for index, word in enumerate(words):
        if index > 0 and word.lower() in small_words:
            formatted.append(word.lower())
        else:
            formatted.append(word[:1].upper() + word[1:])
    return " ".join(formatted)


def is_section_candidate(
    segments: list[dict[str, Any]],
    index: int,
    *,
    first_content_index: int,
) -> bool:
    text = segments[index]["text"].strip().strip(".")
    words = text.split()
    if not 2 <= len(words) <= 8:
        return False
    if "," in text or ";" in text or ":" in text:
        return False
    if text.lower().split()[0] in {
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "did",
        "do",
        "does",
        "what",
        "why",
        "how",
        "when",
        "where",
    }:
        return False
    if index == first_content_index:
        return True
    gap_before = (
        segments[index]["start"] - segments[index - 1]["end"]
        if index > 0
        else 0
    )
    gap_after = (
        segments[index + 1]["start"] - segments[index]["end"]
        if index + 1 < len(segments)
        else 0
    )
    if gap_before < 1.4 or gap_after < 0.7:
        return False
    return text[:1].isupper()


def transcribe_chapter(
    model: Any,
    audio_path: Path,
    *,
    language: str,
    beam_size: int,
) -> list[dict[str, Any]]:
    segments, _info = model.transcribe(
        str(audio_path),
        language=language,
        beam_size=beam_size,
        vad_filter=True,
    )
    return [
        {
            "start": segment.start,
            "end": segment.end,
            "text": segment.text.strip(),
        }
        for segment in segments
        if segment.text.strip()
    ]


def segments_to_markdown(segments: list[dict[str, Any]], chapter: Chapter) -> str:
    """Convert STT segments to readable prose without dropping transcribed words."""
    paragraph_segments: list[str] = []

    for segment in segments:
        paragraph_segments.append(segment["text"].strip())
    return paragraphize(" ".join(paragraph_segments))


def write_section_candidates(
    path: Path,
    chapters: list[Chapter],
    segments_by_chapter: dict[int, list[dict[str, Any]]],
) -> None:
    lines = ["# Section Candidates", ""]
    for chapter in chapters:
        segments = segments_by_chapter.get(chapter.index, [])
        if not segments:
            continue
        lines.append(markdown_heading(2, display_chapter_title(chapter.title)))
        seen: set[tuple[str, str]] = set()
        for index, segment in enumerate(segments):
            timestamp = format_timestamp(chapter.start + segment["start"])
            if is_section_candidate(segments, index, first_content_index=0):
                heading = title_case_heading(segment["text"])
                key = (timestamp, heading)
                if key not in seen:
                    lines.append(f"- `{timestamp}` {heading}")
                    seen.add(key)
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def load_existing_segments(
    work_dir: Path,
    chapter: Chapter,
) -> list[dict[str, Any]] | None:
    segment_path = (
        work_dir / f"{chapter.index:02d}-{slugify(chapter.title)}.segments.json"
    )
    if not segment_path.exists():
        return None
    return json.loads(segment_path.read_text(encoding="utf-8"))


def write_manifest(path: Path, tags: dict[str, str], chapters: list[Chapter]) -> None:
    data = {
        "title": tags.get("title"),
        "artist": tags.get("artist"),
        "album": tags.get("album"),
        "date": tags.get("date"),
        "chapters": [
            {
                "number": chapter_number(chapter),
                "index": chapter.index,
                "title": chapter.title,
                "synthetic": chapter.synthetic,
                "start": chapter.start,
                "end": chapter.end,
                "start_timestamp": format_timestamp(chapter.start),
                "end_timestamp": format_timestamp(chapter.end),
            }
            for chapter in chapters
        ],
    }
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def source_audio_label(path: Path, explicit_label: str | None) -> str:
    if explicit_label:
        return explicit_label
    return path.name or str(path)


def frontmatter_block(data: dict[str, str]) -> str:
    return "---\n" + yaml.safe_dump(
        data,
        allow_unicode=True,
        sort_keys=False,
    ).strip() + "\n---"


def build_markdown(
    *,
    source_audio: str,
    tags: dict[str, str],
    chapters: list[Chapter],
    chapter_markdown: dict[int, str],
) -> str:
    title = tags.get("title") or Path(source_audio).stem
    frontmatter = {
        "title": title,
        "source_audio": source_audio,
        "source_format": "audiobook transcription",
    }
    if tags.get("artist"):
        frontmatter["artist"] = tags["artist"]
    if tags.get("album"):
        frontmatter["album"] = tags["album"]
    if tags.get("date"):
        frontmatter["year"] = tags["date"]
    lines = [frontmatter_block(frontmatter), "", markdown_heading(1, title), ""]

    for chapter in chapters:
        lines.append(markdown_heading(2, display_chapter_title(chapter.title)))
        lines.append(
            f"<!-- audio: {format_timestamp(chapter.start)}-"
            f"{format_timestamp(chapter.end)} -->"
        )
        lines.append("")
        body = chapter_markdown.get(chapter.index, "").strip()
        lines.append(body if body else "_No transcript generated._")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def parse_chapter_selection(
    value: str | None,
    chapters: list[Chapter],
) -> list[Chapter]:
    if not value:
        return chapters
    selected: set[int] = set()
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            selected.update(range(int(start), int(end) + 1))
        else:
            selected.add(int(part))
    if any(number < 1 for number in selected):
        raise SystemExit("--chapters uses 1-based chapter numbers, e.g. 1 or 1-3.")
    selected_indexes = {number - 1 for number in selected}
    return [
        chapter
        for position, chapter in enumerate(chapters)
        if position in selected_indexes
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument(
        "--source-label",
        help="Portable source label to write in frontmatter. Default: audio filename.",
    )
    parser.add_argument("--model", default="small")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--compute-type", default="default")
    parser.add_argument("--language", default="en")
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument(
        "--chapters",
        help="Chapter numbers to transcribe, e.g. 1 or 1-3.",
    )
    parser.add_argument("--section-candidates", type=Path)
    parser.add_argument(
        "--reuse-segments",
        action="store_true",
        help="Reuse existing segment JSON files from --work-dir instead of retranscribing them.",
    )
    args = parser.parse_args()

    require_tools()
    source = args.audio.expanduser().resolve()
    tags, chapters = probe_audiobook(source)
    selected_chapters = parse_chapter_selection(args.chapters, chapters)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        write_manifest(args.manifest, tags, chapters)

    temp_context = tempfile.TemporaryDirectory() if args.work_dir is None else None
    work_dir = args.work_dir or Path(temp_context.name)
    work_dir.mkdir(parents=True, exist_ok=True)
    model = None
    chapter_markdown: dict[int, str] = {}
    segments_by_chapter: dict[int, list[dict[str, Any]]] = {}

    try:
        for chapter in selected_chapters:
            log(
                f"Transcribing chapter {chapter_number(chapter)}: {chapter.title} "
                f"({format_timestamp(chapter.start)}-{format_timestamp(chapter.end)})"
            )
            chapter_audio = work_dir / f"{chapter.index:02d}-{slugify(chapter.title)}.wav"
            segment_path = (
                work_dir / f"{chapter.index:02d}-{slugify(chapter.title)}.segments.json"
            )
            segments = (
                load_existing_segments(work_dir, chapter)
                if args.reuse_segments
                else None
            )
            if segments is not None:
                log(f"  Reusing segments: {segment_path}")
            else:
                if model is None:
                    try:
                        from faster_whisper import WhisperModel
                    except ImportError as exc:
                        raise SystemExit(
                            "Install project dependencies with faster-whisper before transcribing."
                        ) from exc
                    log(f"Loading model: {args.model}")
                    model = WhisperModel(
                        args.model,
                        device=args.device,
                        compute_type=args.compute_type,
                    )
                audio_path = audio_for_transcription(source, chapter, chapter_audio)
                log("  Running speech-to-text")
                segments = transcribe_chapter(
                    model,
                    audio_path,
                    language=args.language,
                    beam_size=args.beam_size,
                )
            segment_path.write_text(
                json.dumps(segments, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            log(f"  Wrote segments: {segment_path}")
            segments_by_chapter[chapter.index] = segments
            chapter_markdown[chapter.index] = segments_to_markdown(segments, chapter)
    finally:
        if temp_context is not None:
            temp_context.cleanup()

    args.out.write_text(
        build_markdown(
            source_audio=source_audio_label(args.audio, args.source_label),
            tags=tags,
            chapters=selected_chapters,
            chapter_markdown=chapter_markdown,
        ),
        encoding="utf-8",
    )
    log(f"Wrote markdown: {args.out}")
    if args.section_candidates:
        args.section_candidates.parent.mkdir(parents=True, exist_ok=True)
        write_section_candidates(
            args.section_candidates,
            selected_chapters,
            segments_by_chapter,
        )
        log(f"Wrote section candidates: {args.section_candidates}")


if __name__ == "__main__":
    main()
