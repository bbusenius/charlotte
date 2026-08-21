#!/usr/bin/env python3
"""Resolve, advance, and clean up AmblesideOnline composer-study runs."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import sys
import unicodedata
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
COMPOSER_SCRIPTS_DIR = Path(__file__).resolve().parent
for import_dir in (SCRIPTS_DIR, COMPOSER_SCRIPTS_DIR):
    if str(import_dir) not in sys.path:
        sys.path.insert(0, str(import_dir))

from curriculum_resolve import resolve_curriculum  # noqa: E402


def load_study_path_helper():
    module_path = COMPOSER_SCRIPTS_DIR / "write_study.py"
    spec = importlib.util.spec_from_file_location("ao_composer_write_study", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load AO composer study writer: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.study_path_for


study_path_for = load_study_path_helper()


DEFAULT_URL = "https://www.amblesideonline.org/composers"
DEFAULT_STATE_DIR = REPO_ROOT / ".state" / "ao-composer-study"
DEFAULT_SCRATCH_ROOT = REPO_ROOT / ".scratch" / "ao-composer-study"
STATE_SCHEMA = "ao-composer-study-state/v1"
TERM_RE = re.compile(
    r"(?P<start>\d{4})\s*[-–]\s*(?P<end>\d{4})\s+TERM\s+(?P<term>[123])",
    re.IGNORECASE,
)
NUMBERED_RE = re.compile(
    r"^\s*(?P<numbers>\d+(?:\s*,\s*\d+)*)\.\s*"
)
FOUR_WEEK_RE = re.compile(
    r"\b(?:spend\s+four\s+weeks|for\s+(?:4|four)\s+weeks)\b",
    re.IGNORECASE,
)
FOUR_WEEK_PAREN_RE = re.compile(
    r"\(\s*(?:spend\s+)?(?:for\s+)?(?:4|four)\s+weeks\s*\)",
    re.IGNORECASE,
)
OR_RE = re.compile(r"\s+OR\s+", re.IGNORECASE)
RECORDING_HOSTS = {
    "archive.org",
    "vimeo.com",
    "www.vimeo.com",
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
}


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


class AOComposerParser(HTMLParser):
    """Collect paragraph lines, anchors, and anchor offsets from AO HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[dict[str, Any]] = []
        self._block_id = ""
        self._lines: list[dict[str, Any]] | None = None
        self._link: dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "p":
            self._block_id = attributes.get("id") or ""
            self._lines = [{"parts": [], "links": []}]
        elif tag == "br" and self._lines is not None:
            self._lines.append({"parts": [], "links": []})
        elif tag == "a" and self._lines is not None:
            line = self._lines[-1]
            self._link = {
                "href": attributes.get("href") or "",
                "text": "",
                "start": sum(len(part) for part in line["parts"]),
            }
            line["links"].append(self._link)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self._link = None
        elif tag == "p" and self._lines is not None:
            lines = []
            for raw in self._lines:
                raw_text = "".join(raw["parts"])
                text = clean_text(raw_text)
                links = [
                    {
                        "href": link["href"],
                        "text": clean_text(link["text"]),
                        "start": int(link["start"]),
                    }
                    for link in raw["links"]
                    if link["href"]
                ]
                if text or links:
                    lines.append(
                        {"raw_text": raw_text, "text": text, "links": links}
                    )
            if lines:
                self.blocks.append(
                    {
                        "id": self._block_id,
                        "text": clean_text(
                            " ".join(line["text"] for line in lines)
                        ),
                        "lines": lines,
                    }
                )
            self._block_id = ""
            self._lines = None
            self._link = None

    def handle_data(self, data: str) -> None:
        if self._lines is None:
            return
        self._lines[-1]["parts"].append(data)
        if self._link is not None:
            self._link["text"] += data


def is_recording_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host in RECORDING_HOSTS:
        return True
    return host.endswith(".youtube.com") or host.endswith(".archive.org")


def _primary_line_data(
    line: dict[str, Any], source_url: str
) -> tuple[str, list[str]]:
    raw_text = line["raw_text"]
    number_match = NUMBERED_RE.match(clean_text(raw_text))
    if not number_match:
        return "", []

    or_match = OR_RE.search(raw_text)
    or_offset = or_match.start() if or_match else None
    recording_links = []
    for link in line["links"]:
        absolute = urljoin(source_url, link["href"])
        if not is_recording_url(absolute):
            continue
        recording_links.append((link["start"], absolute))

    cutoff = or_offset if or_offset is not None else len(raw_text)
    if recording_links:
        cutoff = min(cutoff, min(offset for offset, _url in recording_links))
    title_text = clean_text(raw_text[:cutoff])
    title_text = NUMBERED_RE.sub("", title_text, count=1)
    title_text = FOUR_WEEK_PAREN_RE.sub("", title_text)
    title_text = title_text.rstrip(" :-,;*")
    urls = list(dict.fromkeys(url for _offset, url in recording_links))
    return title_text, urls


def parse_rotation(
    html: str, source_url: str = DEFAULT_URL
) -> list[dict[str, Any]]:
    parser = AOComposerParser()
    parser.feed(html)
    headers: list[tuple[int, re.Match[str]]] = []
    for index, block in enumerate(parser.blocks):
        match = TERM_RE.search(block["text"])
        if match:
            headers.append((index, match))

    schedules: list[dict[str, Any]] = []
    for header_index, (block_index, match) in enumerate(headers):
        next_index = (
            headers[header_index + 1][0]
            if header_index + 1 < len(headers)
            else len(parser.blocks)
        )
        block = parser.blocks[block_index]
        header = block["text"]
        composer_tail = header[match.end() :].strip(" :-")
        composer = clean_text(composer_tail.split("(", 1)[0])
        details_match = re.search(r"\(([^()]*)\)", composer_tail)
        composer_details = details_match.group(1).strip() if details_match else ""
        anchor = block.get("id") or ""
        schedule_url = source_url.split("#", 1)[0]
        if anchor:
            schedule_url = f"{schedule_url}#{anchor}"

        works: list[dict[str, Any]] = []
        for candidate in parser.blocks[block_index + 1 : next_index]:
            for line in candidate["lines"]:
                number_match = NUMBERED_RE.match(line["text"])
                if not number_match:
                    continue
                slot_numbers = [
                    int(value.strip())
                    for value in number_match.group("numbers").split(",")
                ]
                title, recording_urls = _primary_line_data(line, source_url)
                if not title:
                    continue
                presentation_count = len(slot_numbers)
                if FOUR_WEEK_RE.search(line["text"]):
                    presentation_count = max(presentation_count, 2)
                works.append(
                    {
                        "selection_number": slot_numbers[0],
                        "slot_numbers": slot_numbers,
                        "presentation_count": presentation_count,
                        "title": title,
                        "recording_urls": recording_urls,
                        "ao_line": line["text"],
                        "ao_url": schedule_url,
                    }
                )

        if composer and works:
            schedules.append(
                {
                    "school_year": f"{match.group('start')}-{match.group('end')}",
                    "start_year": int(match.group("start")),
                    "end_year": int(match.group("end")),
                    "term": int(match.group("term")),
                    "composer": composer,
                    "composer_details": composer_details,
                    "ao_url": schedule_url,
                    "works": works,
                }
            )

    schedules.sort(key=lambda item: (item["start_year"], item["term"]))
    if not schedules:
        raise ValueError("No AO year/term composer-study schedules could be parsed")
    return schedules


def load_students(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    students = data.get("students")
    if not isinstance(students, dict):
        raise SystemExit(f"No students mapping found in {path}")
    return students


def norm(value: Any) -> str:
    return str(value or "").strip().casefold()


def resolve_student(
    students: dict[str, Any], query: str
) -> tuple[str, dict[str, Any]]:
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
    if data.get("schema") != STATE_SCHEMA or not isinstance(
        data.get("last_presented"), dict
    ):
        raise SystemExit(f"Unrecognized AO composer-study state in {path}")
    return data["last_presented"]


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


def find_schedule(
    schedules: list[dict[str, Any]], school_year: str, term: int
) -> dict[str, Any]:
    for schedule in schedules:
        if schedule["school_year"] == school_year and schedule["term"] == term:
            return schedule
    raise ValueError(f"AO schedule {school_year} Term {term} was not found")


def find_work(
    schedule: dict[str, Any], selection_number: int, title: str | None = None
) -> dict[str, Any]:
    matches = [
        work
        for work in schedule["works"]
        if selection_number == work["selection_number"]
        or selection_number in work["slot_numbers"]
    ]
    if title:
        title_matches = [work for work in matches if norm(work["title"]) == norm(title)]
        if title_matches:
            matches = title_matches
    if len(matches) != 1:
        raise ValueError(
            f"AO schedule {schedule['school_year']} Term {schedule['term']} "
            f"has no unique selection {selection_number}"
        )
    return matches[0]


def slugify(value: str, limit: int = 64) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
    return slug[:limit].rstrip("-") or "music"


def make_target(
    schedule: dict[str, Any],
    work: dict[str, Any],
    cursor: dict[str, Any] | None,
    presentation: int,
) -> dict[str, Any]:
    composer_slug = slugify(schedule["composer"], 26)
    title_slug = slugify(work["title"], 42)
    base_id = (
        f"ao-composer-{schedule['school_year']}-t{schedule['term']}-"
        f"{work['selection_number']:02d}-{composer_slug}-{title_slug}"
    )
    introduce_composer = (
        presentation == 1
        and (
            cursor is None
            or str(cursor.get("school_year")) != schedule["school_year"]
            or int(cursor.get("term", 0)) != schedule["term"]
            or norm(cursor.get("composer")) != norm(schedule["composer"])
        )
    )
    return {
        "school_year": schedule["school_year"],
        "term": schedule["term"],
        "composer": schedule["composer"],
        "composer_details": schedule["composer_details"],
        "selection_number": work["selection_number"],
        "slot_numbers": work["slot_numbers"],
        "presentation": presentation,
        "presentation_count": work["presentation_count"],
        "repeat_presentation": presentation > 1,
        "title": work["title"],
        "recording_urls": work["recording_urls"],
        "ao_line": work["ao_line"],
        "ao_url": work["ao_url"],
        "introduce_composer": introduce_composer,
        "scratch_id": base_id,
        "suggested_work_slide_id": f"{base_id}-work",
        "suggested_podcast_slide_id": f"{base_id}-podcast",
    }


def resolve_next(
    schedules: list[dict[str, Any]],
    cursor: dict[str, Any] | None,
    today: date,
    override: tuple[str, int, int, int] | None = None,
) -> dict[str, Any]:
    if override is not None:
        school_year, term, selection_number, presentation = override
        schedule = find_schedule(schedules, school_year, term)
        work = find_work(schedule, selection_number)
        if not 1 <= presentation <= int(work["presentation_count"]):
            raise ValueError(
                f"presentation must be between 1 and {work['presentation_count']}"
            )
        return make_target(schedule, work, cursor, presentation)

    if cursor is None:
        school_year, term = inferred_schedule_key(today)
        try:
            schedule = find_schedule(schedules, school_year, term)
        except ValueError:
            desired_start = int(school_year[:4])
            candidates = [
                schedule
                for schedule in schedules
                if (schedule["start_year"], schedule["term"])
                >= (desired_start, term)
            ]
            schedule = candidates[0] if candidates else schedules[-1]
        return make_target(schedule, schedule["works"][0], cursor, 1)

    current = find_schedule(
        schedules, str(cursor["school_year"]), int(cursor["term"])
    )
    work = find_work(
        current,
        int(cursor["selection_number"]),
        str(cursor.get("title") or ""),
    )
    completed = int(cursor.get("presentation", 1))
    if completed < int(work["presentation_count"]):
        return make_target(current, work, cursor, completed + 1)

    work_index = current["works"].index(work)
    if work_index + 1 < len(current["works"]):
        return make_target(current, current["works"][work_index + 1], cursor, 1)

    current_key = (current["start_year"], current["term"])
    following = [
        schedule
        for schedule in schedules
        if (schedule["start_year"], schedule["term"]) > current_key
    ]
    if not following:
        raise ValueError("AO has not published a schedule after the last presentation")
    schedule = following[0]
    return make_target(schedule, schedule["works"][0], cursor, 1)


def fetch_html(url: str, html_file: Path | None) -> str:
    if html_file is not None:
        return html_file.read_text(encoding="utf-8")
    response = requests.get(
        url,
        headers={"User-Agent": "CharlotteHomeschoolAgent/0.1 (AO composer study)"},
        timeout=30,
    )
    response.raise_for_status()
    return response.text


def commit_cursor(
    path: Path,
    student_slug: str,
    target: dict[str, Any],
    work_slide_id: str,
    podcast_slide_id: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    last_presented = {
        key: target[key]
        for key in (
            "school_year",
            "term",
            "composer",
            "selection_number",
            "slot_numbers",
            "title",
            "presentation",
            "presentation_count",
            "ao_url",
            "scratch_id",
        )
    }
    last_presented.update(
        work_slide_id=work_slide_id,
        podcast_slide_id=podcast_slide_id,
    )
    data = {
        "schema": STATE_SCHEMA,
        "student": student_slug,
        "last_presented": last_presented,
    }
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    temporary.replace(path)


def cleanup_scratch(
    scratch_root: Path, student_slug: str, scratch_id: str
) -> tuple[Path, bool]:
    if not re.fullmatch(r"ao-composer-[a-z0-9][a-z0-9-]*", scratch_id):
        raise ValueError(f"Invalid AO composer scratch id: {scratch_id!r}")
    if Path(student_slug).name != student_slug or student_slug in {"", ".", ".."}:
        raise ValueError(f"Invalid student slug for scratch cleanup: {student_slug!r}")
    student_root = scratch_root / student_slug
    target = student_root / scratch_id
    if target.is_symlink():
        raise ValueError(f"Refusing to remove symlinked scratch directory: {target}")
    if not target.exists():
        return target, False
    if not target.is_dir():
        raise ValueError(f"AO composer scratch target is not a directory: {target}")
    if target.parent.resolve() != student_root.resolve():
        raise ValueError(f"AO composer scratch target escaped its student directory: {target}")
    shutil.rmtree(target)
    return target, True


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--student", required=True)
    parser.add_argument("--students-file", default="students.yaml", type=Path)
    parser.add_argument("--state-dir", default=DEFAULT_STATE_DIR, type=Path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    next_parser = subparsers.add_parser("next", help="Resolve the next AO work")
    add_common(next_parser)
    next_parser.add_argument("--url", default=DEFAULT_URL)
    next_parser.add_argument("--html-file", type=Path)
    next_parser.add_argument("--today", type=date.fromisoformat, default=date.today())
    next_parser.add_argument("--school-year")
    next_parser.add_argument("--term", type=int, choices=(1, 2, 3))
    next_parser.add_argument("--selection-number", type=int)
    next_parser.add_argument("--presentation", type=int, default=1)

    commit_parser = subparsers.add_parser(
        "commit", help="Commit a successfully selected presentation"
    )
    add_common(commit_parser)
    commit_parser.add_argument("--school-year", required=True)
    commit_parser.add_argument("--term", type=int, choices=(1, 2, 3), required=True)
    commit_parser.add_argument("--composer", required=True)
    commit_parser.add_argument("--selection-number", type=int, required=True)
    commit_parser.add_argument("--slot-number", action="append", type=int, default=[])
    commit_parser.add_argument("--title", required=True)
    commit_parser.add_argument("--presentation", type=int, required=True)
    commit_parser.add_argument("--presentation-count", type=int, required=True)
    commit_parser.add_argument("--ao-url", required=True)
    commit_parser.add_argument("--scratch-id", required=True)
    commit_parser.add_argument("--work-slide-id", required=True)
    commit_parser.add_argument("--podcast-slide-id", required=True)

    cleanup_parser = subparsers.add_parser(
        "cleanup", help="Remove the exact scratch directory for a committed run"
    )
    add_common(cleanup_parser)
    cleanup_parser.add_argument("--scratch-id", required=True)
    cleanup_parser.add_argument(
        "--scratch-root", default=DEFAULT_SCRATCH_ROOT, type=Path
    )

    args = parser.parse_args()
    students = load_students(args.students_file)
    student_slug, student = resolve_student(students, args.student)
    cursor_path = state_path(args.state_dir, student_slug)

    if args.command == "next":
        curriculum = resolve_curriculum(
            student,
            args.students_file.resolve().parent,
            curriculum="ao-composer-study",
        )
        override_values = (args.school_year, args.term, args.selection_number)
        supplied = sum(value is not None for value in override_values)
        if supplied not in (0, 3):
            parser.error(
                "pass --school-year, --term, and --selection-number together"
            )
        if supplied == 0 and args.presentation != 1:
            parser.error("--presentation requires an explicit starting selection")
        override = (
            (*override_values, args.presentation) if supplied == 3 else None
        )
        html = fetch_html(args.url, args.html_file)
        schedules = parse_rotation(html, args.url)
        cursor = load_cursor(cursor_path)
        target = resolve_next(schedules, cursor, args.today, override)  # type: ignore[arg-type]
        target["suggested_study_path"] = str(
            study_path_for(
                Path(curriculum["path"]), target["composer"], target["title"]
            )
        )
        result = {
            "student": student_slug,
            "display_name": student.get("display_name") or student_slug,
            "grade": student.get("grade"),
            "tablet_slides_dir": student.get("tablet_slides_dir"),
            "curriculum": curriculum,
            "state_path": str(cursor_path),
            "scratch_dir": str(
                DEFAULT_SCRATCH_ROOT / student_slug / target["scratch_id"]
            ),
            "cursor": cursor,
            "target": target,
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    if args.command == "cleanup":
        cursor = load_cursor(cursor_path)
        if cursor is None:
            raise SystemExit(f"No committed AO composer cursor found in {cursor_path}")
        if str(cursor.get("scratch_id") or "") != args.scratch_id:
            raise SystemExit(
                "Refusing scratch cleanup because the requested run is not the "
                "committed cursor"
            )
        scratch_path, removed = cleanup_scratch(
            args.scratch_root, student_slug, args.scratch_id
        )
        print(
            json.dumps(
                {
                    "ok": True,
                    "student": student_slug,
                    "scratch_id": args.scratch_id,
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
        "composer": args.composer,
        "selection_number": args.selection_number,
        "slot_numbers": args.slot_number or [args.selection_number],
        "title": args.title,
        "presentation": args.presentation,
        "presentation_count": args.presentation_count,
        "ao_url": args.ao_url,
        "scratch_id": args.scratch_id,
    }
    if not 1 <= args.presentation <= args.presentation_count:
        parser.error("presentation must be between 1 and presentation-count")
    commit_cursor(
        cursor_path,
        student_slug,
        target,
        args.work_slide_id,
        args.podcast_slide_id,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "student": student_slug,
                "state_path": str(cursor_path),
                "last_presented": {
                    **target,
                    "work_slide_id": args.work_slide_id,
                    "podcast_slide_id": args.podcast_slide_id,
                },
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
