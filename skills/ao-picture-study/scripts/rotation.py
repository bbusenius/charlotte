#!/usr/bin/env python3
"""Resolve and commit the next AmblesideOnline picture-study work."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import unicodedata
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
AO_SCRIPTS_DIR = Path(__file__).resolve().parent
for import_dir in (SCRIPTS_DIR, AO_SCRIPTS_DIR):
    if str(import_dir) not in sys.path:
        sys.path.insert(0, str(import_dir))

from curriculum_resolve import resolve_curriculum  # noqa: E402
from write_study import study_path_for  # noqa: E402


DEFAULT_URL = "https://amblesideonline.org/artists"
DEFAULT_STATE_DIR = REPO_ROOT / ".state" / "ao-picture-study"
DEFAULT_SCRATCH_ROOT = REPO_ROOT / ".scratch" / "ao-picture-study"
STATE_SCHEMA = "ao-picture-study-state/v1"
TERM_RE = re.compile(
    r"(?P<start>\d{4})\s*[-–]\s*(?P<end>\d{4})\s+TERM\s+(?P<term>[123])",
    re.IGNORECASE,
)
NUMBERED_RE = re.compile(r"^\s*(?P<number>\d+)\.\s*")
DATE_PATTERNS = (
    re.compile(r"\b(?:c\.|ca\.|circa)\s*\d{4}(?:\s*[-–]\s*\d{2,4})?\b", re.IGNORECASE),
    re.compile(r"\b(?:before|after)\s+\d{4}\b", re.IGNORECASE),
    re.compile(r"\b\d{4}(?:\s*[-–]\s*\d{2,4})?\b"),
)


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


class AOParagraphParser(HTMLParser):
    """Collect paragraph text as display lines with their links."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[dict[str, Any]] = []
        self._lines: list[dict[str, Any]] | None = None
        self._link: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "p":
            self._lines = [{"parts": [], "links": []}]
        elif tag == "br" and self._lines is not None:
            self._lines.append({"parts": [], "links": []})
        elif tag == "a" and self._lines is not None:
            href = dict(attrs).get("href") or ""
            self._link = {"href": href, "text": ""}
            self._lines[-1]["links"].append(self._link)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self._link = None
        elif tag == "p" and self._lines is not None:
            lines = []
            for raw in self._lines:
                text = clean_text("".join(raw["parts"]))
                links = [
                    {"href": link["href"], "text": clean_text(link["text"])}
                    for link in raw["links"]
                    if clean_text(link["text"])
                ]
                if text or links:
                    lines.append({"text": text, "links": links})
            if lines:
                self.blocks.append(
                    {
                        "text": clean_text(" ".join(line["text"] for line in lines)),
                        "lines": lines,
                    }
                )
            self._lines = None
            self._link = None

    def handle_data(self, data: str) -> None:
        if self._lines is None:
            return
        self._lines[-1]["parts"].append(data)
        if self._link is not None:
            self._link["text"] += data


def extract_date(line: str) -> str:
    for pattern in DATE_PATTERNS:
        match = pattern.search(line)
        if match:
            return clean_text(match.group(0)).replace("–", "-")
    return "date unknown"


def parse_rotation(html: str, source_url: str = DEFAULT_URL) -> list[dict[str, Any]]:
    parser = AOParagraphParser()
    parser.feed(html)
    headers: list[tuple[int, re.Match[str]]] = []
    for index, block in enumerate(parser.blocks):
        match = TERM_RE.search(block["text"])
        if match:
            headers.append((index, match))

    schedules: list[dict[str, Any]] = []
    for header_index, (block_index, match) in enumerate(headers):
        next_block_index = headers[header_index + 1][0] if header_index + 1 < len(headers) else len(parser.blocks)
        header = parser.blocks[block_index]["text"]
        artist_tail = header[match.end() :].strip(" :-")
        artist = clean_text(artist_tail.split("(", 1)[0])
        artist_details = ""
        if "(" in artist_tail and ")" in artist_tail:
            artist_details = artist_tail.split("(", 1)[1].rsplit(")", 1)[0].strip()

        works: list[dict[str, Any]] = []
        for block in parser.blocks[block_index + 1 : next_block_index]:
            for line in block["lines"]:
                number_match = NUMBERED_RE.match(line["text"])
                if not number_match or not line["links"]:
                    continue
                primary = line["links"][0]
                works.append(
                    {
                        "number": int(number_match.group("number")),
                        "title": primary["text"],
                        "date": extract_date(line["text"]),
                        "ao_url": urljoin(source_url, primary["href"]),
                        "ao_line": line["text"],
                    }
                )

        if artist and works:
            schedules.append(
                {
                    "school_year": f"{match.group('start')}-{match.group('end')}",
                    "start_year": int(match.group("start")),
                    "end_year": int(match.group("end")),
                    "term": int(match.group("term")),
                    "artist": artist,
                    "artist_details": artist_details,
                    "works": works,
                }
            )

    schedules.sort(key=lambda item: (item["start_year"], item["term"]))
    if not schedules:
        raise ValueError("No AO year/term picture-study schedules could be parsed")
    return schedules


def load_students(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    students = data.get("students")
    if not isinstance(students, dict):
        raise SystemExit(f"No students mapping found in {path}")
    return students


def norm(value: Any) -> str:
    return str(value or "").strip().lower()


def resolve_student(students: dict[str, Any], query: str) -> tuple[str, dict[str, Any]]:
    q = norm(query)
    matches: list[tuple[str, dict[str, Any]]] = []
    for slug, student in students.items():
        if not isinstance(student, dict):
            continue
        candidates = {norm(slug), norm(student.get("display_name"))}
        aliases = student.get("aliases") or []
        if isinstance(aliases, list):
            candidates.update(norm(alias) for alias in aliases)
        if q in candidates:
            matches.append((slug, student))
    if len(matches) != 1:
        if not matches:
            raise SystemExit(f"No student matched {query!r}")
        raise SystemExit(f"Student query {query!r} is ambiguous")
    return matches[0]


def state_path(state_dir: Path, student_slug: str) -> Path:
    return state_dir / f"{student_slug}.yaml"


def load_cursor(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if data.get("schema") != STATE_SCHEMA or not isinstance(data.get("last_created"), dict):
        raise SystemExit(f"Unrecognized AO picture-study state in {path}")
    return data["last_created"]


def inferred_schedule_key(today: date) -> tuple[str, int]:
    if today.month >= 7:
        school_year = f"{today.year}-{today.year + 1}"
    else:
        school_year = f"{today.year - 1}-{today.year}"
    if 7 <= today.month <= 11:
        term = 1
    elif today.month == 12 or today.month <= 3:
        term = 2
    else:
        term = 3
    return school_year, term


def find_schedule(schedules: list[dict[str, Any]], school_year: str, term: int) -> dict[str, Any]:
    for schedule in schedules:
        if schedule["school_year"] == school_year and schedule["term"] == term:
            return schedule
    raise ValueError(f"AO schedule {school_year} Term {term} was not found")


def find_work(schedule: dict[str, Any], picture_number: int) -> dict[str, Any]:
    for work in schedule["works"]:
        if work["number"] == picture_number:
            return work
    raise ValueError(
        f"AO schedule {schedule['school_year']} Term {schedule['term']} has no picture {picture_number}"
    )


def slugify(value: str, limit: int = 64) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
    return slug[:limit].rstrip("-") or "picture"


def make_target(
    schedule: dict[str, Any],
    work: dict[str, Any],
    cursor: dict[str, Any] | None,
) -> dict[str, Any]:
    artist_slug = slugify(schedule["artist"], 28)
    title_slug = slugify(work["title"], 48)
    slide_id = (
        f"ao-{schedule['school_year']}-t{schedule['term']}-"
        f"{work['number']:02d}-{artist_slug}-{title_slug}"
    )
    introduce_artist = (
        cursor is None
        or str(cursor.get("school_year")) != schedule["school_year"]
        or int(cursor.get("term", 0)) != schedule["term"]
        or norm(cursor.get("artist")) != norm(schedule["artist"])
    )
    return {
        "school_year": schedule["school_year"],
        "term": schedule["term"],
        "artist": schedule["artist"],
        "artist_details": schedule["artist_details"],
        "picture_number": work["number"],
        "title": work["title"],
        "date": work["date"],
        "ao_url": work["ao_url"],
        "ao_line": work["ao_line"],
        "suggested_slide_id": slide_id,
        "introduce_artist": introduce_artist,
    }


def resolve_next(
    schedules: list[dict[str, Any]],
    cursor: dict[str, Any] | None,
    today: date,
    override: tuple[str, int, int] | None = None,
) -> dict[str, Any]:
    if override is not None:
        school_year, term, picture_number = override
        schedule = find_schedule(schedules, school_year, term)
        return make_target(schedule, find_work(schedule, picture_number), cursor)

    if cursor is None:
        school_year, term = inferred_schedule_key(today)
        try:
            schedule = find_schedule(schedules, school_year, term)
        except ValueError:
            desired_start = int(school_year[:4])
            candidates = [
                schedule
                for schedule in schedules
                if (schedule["start_year"], schedule["term"]) >= (desired_start, term)
            ]
            schedule = candidates[0] if candidates else schedules[-1]
        first_work = min(schedule["works"], key=lambda work: work["number"])
        return make_target(schedule, first_work, cursor)

    current = find_schedule(schedules, str(cursor["school_year"]), int(cursor["term"]))
    current_number = int(cursor["picture_number"])
    later = sorted(
        (work for work in current["works"] if work["number"] > current_number),
        key=lambda work: work["number"],
    )
    if later:
        return make_target(current, later[0], cursor)

    current_key = (current["start_year"], current["term"])
    following = [
        schedule
        for schedule in schedules
        if (schedule["start_year"], schedule["term"]) > current_key
    ]
    if not following:
        raise ValueError("AO has not published a schedule after the last-created picture")
    schedule = following[0]
    first_work = min(schedule["works"], key=lambda work: work["number"])
    return make_target(schedule, first_work, cursor)


def fetch_html(url: str, html_file: Path | None) -> str:
    if html_file is not None:
        return html_file.read_text(encoding="utf-8")
    response = requests.get(
        url,
        headers={"User-Agent": "CharlotteHomeschoolAgent/0.1 (AO picture study)"},
        timeout=30,
    )
    response.raise_for_status()
    return response.text


def commit_cursor(
    path: Path,
    student_slug: str,
    target: dict[str, Any],
    slide_id: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "schema": STATE_SCHEMA,
        "student": student_slug,
        "last_created": {
            "school_year": target["school_year"],
            "term": int(target["term"]),
            "picture_number": int(target["picture_number"]),
            "artist": target["artist"],
            "title": target["title"],
            "date": target["date"],
            "ao_url": target["ao_url"],
            "slide_id": slide_id,
        },
    }
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    temporary.replace(path)


def cleanup_scratch(
    scratch_root: Path,
    student_slug: str,
    slide_id: str,
) -> tuple[Path, bool]:
    """Remove one validated, already-committed AO run directory."""
    if not re.fullmatch(r"ao-[a-z0-9][a-z0-9-]*", slide_id):
        raise ValueError(f"Invalid AO slide id for scratch cleanup: {slide_id!r}")
    if Path(student_slug).name != student_slug or student_slug in {"", ".", ".."}:
        raise ValueError(f"Invalid student slug for scratch cleanup: {student_slug!r}")

    student_root = scratch_root / student_slug
    target = student_root / slide_id
    if target.is_symlink():
        raise ValueError(f"Refusing to remove symlinked AO scratch directory: {target}")
    if not target.exists():
        return target, False
    if not target.is_dir():
        raise ValueError(f"AO scratch target is not a directory: {target}")
    if target.parent.resolve() != student_root.resolve():
        raise ValueError(f"AO scratch target escaped its student directory: {target}")

    shutil.rmtree(target)
    return target, True


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--student", required=True, help="Student slug, display name, or alias")
    parser.add_argument("--students-file", default="students.yaml", type=Path)
    parser.add_argument("--state-dir", default=DEFAULT_STATE_DIR, type=Path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    next_parser = subparsers.add_parser("next", help="Resolve the next AO picture")
    add_common(next_parser)
    next_parser.add_argument("--url", default=DEFAULT_URL)
    next_parser.add_argument("--html-file", type=Path, help="Read saved AO HTML instead of fetching")
    next_parser.add_argument("--today", type=date.fromisoformat, default=date.today())
    next_parser.add_argument("--school-year")
    next_parser.add_argument("--term", type=int, choices=(1, 2, 3))
    next_parser.add_argument("--picture-number", type=int)

    commit_parser = subparsers.add_parser("commit", help="Commit a successfully selected slide")
    add_common(commit_parser)
    commit_parser.add_argument("--school-year", required=True)
    commit_parser.add_argument("--term", type=int, choices=(1, 2, 3), required=True)
    commit_parser.add_argument("--picture-number", type=int, required=True)
    commit_parser.add_argument("--artist", required=True)
    commit_parser.add_argument("--title", required=True)
    commit_parser.add_argument("--date", required=True)
    commit_parser.add_argument("--ao-url", required=True)
    commit_parser.add_argument("--slide-id", required=True)

    cleanup_parser = subparsers.add_parser(
        "cleanup", help="Remove the exact scratch directory for a committed AO slide"
    )
    add_common(cleanup_parser)
    cleanup_parser.add_argument("--slide-id", required=True)
    cleanup_parser.add_argument("--scratch-root", default=DEFAULT_SCRATCH_ROOT, type=Path)

    args = parser.parse_args()
    students = load_students(args.students_file)
    student_slug, student = resolve_student(students, args.student)
    cursor_path = state_path(args.state_dir, student_slug)

    if args.command == "next":
        curriculum = resolve_curriculum(
            student,
            args.students_file.resolve().parent,
            curriculum="ao-picture-study",
        )
        override_values = (args.school_year, args.term, args.picture_number)
        supplied = sum(value is not None for value in override_values)
        if supplied not in (0, 3):
            parser.error("pass --school-year, --term, and --picture-number together")
        override = override_values if supplied == 3 else None
        html = fetch_html(args.url, args.html_file)
        schedules = parse_rotation(html, args.url)
        cursor = load_cursor(cursor_path)
        target = resolve_next(schedules, cursor, args.today, override)  # type: ignore[arg-type]
        target["suggested_study_path"] = str(
            study_path_for(
                Path(curriculum["path"]), target["artist"], target["title"]
            )
        )
        result = {
            "student": student_slug,
            "display_name": student.get("display_name") or student_slug,
            "grade": student.get("grade"),
            "tablet_slides_dir": student.get("tablet_slides_dir"),
            "curriculum": curriculum,
            "state_path": str(cursor_path),
            "scratch_dir": str(DEFAULT_SCRATCH_ROOT / student_slug / target["suggested_slide_id"]),
            "cursor": cursor,
            "target": target,
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    if args.command == "cleanup":
        cursor = load_cursor(cursor_path)
        if cursor is None:
            raise SystemExit(f"No committed AO picture-study cursor found in {cursor_path}")
        committed_slide_id = str(cursor.get("slide_id") or "")
        if committed_slide_id != args.slide_id:
            raise SystemExit(
                "Refusing scratch cleanup because the requested slide is not the "
                f"committed cursor: requested {args.slide_id!r}, committed "
                f"{committed_slide_id!r}"
            )
        scratch_path, removed = cleanup_scratch(
            args.scratch_root, student_slug, args.slide_id
        )
        print(
            json.dumps(
                {
                    "ok": True,
                    "student": student_slug,
                    "slide_id": args.slide_id,
                    "scratch_path": str(scratch_path),
                    "removed": removed,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    target = {
        "school_year": args.school_year,
        "term": args.term,
        "picture_number": args.picture_number,
        "artist": args.artist,
        "title": args.title,
        "date": args.date,
        "ao_url": args.ao_url,
    }
    commit_cursor(cursor_path, student_slug, target, args.slide_id)
    print(
        json.dumps(
            {
                "ok": True,
                "student": student_slug,
                "state_path": str(cursor_path),
                "last_created": {**target, "slide_id": args.slide_id},
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, requests.RequestException) as exc:
        raise SystemExit(str(exc)) from exc
