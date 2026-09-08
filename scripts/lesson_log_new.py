#!/usr/bin/env python3
"""Locate, create, and populate lesson-log session directories.

A lesson log is one directory per teaching session:

    lesson-logs/<student>/<grade>/<year>/<month>/<day>/<subject>-<slug>/
        log.md          synthesis (written by the lesson-log skill)
        messages.md     what the parent said
        images.md       what Charlotte saw
        videos.md       videos watched: URL, account, transcript
        sources/        raw photos, screenshots, voice notes

This script owns the mechanical parts of that layout — finding an existing
session, creating a new one, and copying captured media in with stable
append-only names — so repeated runs stay deterministic no matter how often
capture runs or how material trickles in.

Subcommands:

    find    list sessions for a student on a date (optionally one subject)
    create  create a session directory and its stub log.md
    add     copy captured files into a session's sources/

All output is JSON on stdout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import date as date_cls
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hsd_common import load_registry, resolve_student  # noqa: E402

SCHEMA = "lesson-log/v1"
DEFAULT_ROOT = Path("lesson-logs")

# Role -> filename prefix for files in sources/. The only distinction here is
# what kind of file it is, which is never a judgement call. What an image shows
# — which workbook page, whether it is filled in, what the scene is — belongs in
# images.md, and the number is only the order it arrived in.
ROLE_PREFIXES = {
    "image": "image",
    "voice": "voice",
}


def slugify(value: str) -> str:
    """Lowercase, dash-separated slug with punctuation removed."""
    text = re.sub(r"[^a-z0-9]+", "-", str(value).strip().lower())
    return text.strip("-")


def grade_dir_name(grade: Any) -> str:
    """Directory name for a grade: grade-3, preschool, kindergarten."""
    text = str(grade).strip()
    if not text:
        raise SystemExit("student has no grade in students.yaml")
    return f"grade-{text}" if text.isdigit() else slugify(text)


def session_day_dir(grade_root: Path, on_date: date_cls) -> Path:
    """The directory containing every session from one school day."""
    return (
        grade_root
        / f"{on_date.year:04d}"
        / f"{on_date.month:02d}"
        / f"{on_date.day:02d}"
    )


def iter_session_dirs(grade_root: Path):
    """Yield session directories from one grade's YYYY/MM/DD tree."""
    if not grade_root.is_dir():
        return
    pattern = (
        "[0-9][0-9][0-9][0-9]/"
        "[0-9][0-9]/"
        "[0-9][0-9]/"
        "*"
    )
    for candidate in sorted(grade_root.glob(pattern)):
        if candidate.is_dir():
            yield candidate


def parse_iso_date(value: str) -> date_cls:
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise SystemExit(f"date must be YYYY-MM-DD: {value}") from None


def read_frontmatter(log_path: Path) -> dict[str, Any] | None:
    """Return a session's log.md frontmatter, or None if unreadable."""
    if not log_path.is_file():
        return None
    text = log_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        loaded = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    if not isinstance(loaded, dict):
        return None

    # YAML resolves an unquoted ISO date (the natural way to write the
    # frontmatter by hand) to a date object. Every command emits JSON, so keep
    # the in-memory schema JSON-native regardless of how the date was quoted.
    value = loaded.get("date")
    if isinstance(value, datetime):
        loaded["date"] = value.date().isoformat()
    elif isinstance(value, date_cls):
        loaded["date"] = value.isoformat()
    return loaded


def describe_session(path: Path) -> dict[str, Any]:
    """Summarize a session directory for JSON output."""
    frontmatter = read_frontmatter(path / "log.md")
    sources = sorted(p.name for p in (path / "sources").glob("*") if p.is_file())
    has_times = bool(
        (frontmatter or {}).get("start_time") and (frontmatter or {}).get("end_time")
    )
    return {
        "path": str(path),
        "frontmatter": frontmatter,
        "subject": (frontmatter or {}).get("subject"),
        "has_log": (path / "log.md").is_file(),
        "has_times": has_times,
        "sources": sources,
    }


def find_sessions(
    root: Path, student_slug: str, on_date: date_cls, subject: str | None
) -> list[dict[str, Any]]:
    """Find sessions for a student on a date, across every grade directory.

    Goes straight to each grade's dated day directory, then reads only that
    day's frontmatter. Searching across grades keeps this correct at the
    boundary where a student's grade changes in students.yaml.
    """
    student_root = root / student_slug
    if not student_root.is_dir():
        return []
    found = []
    for grade_root in sorted(student_root.iterdir()):
        if not grade_root.is_dir():
            continue
        day_dir = session_day_dir(grade_root, on_date)
        if not day_dir.is_dir():
            continue
        for candidate in sorted(day_dir.iterdir()):
            if not candidate.is_dir():
                continue
            session = describe_session(candidate)
            if subject is not None and session["subject"] != subject:
                continue
            found.append(session)
    return found


def stub_log(student_slug: str, student: dict[str, Any], on_date: date_cls, subject: str) -> str:
    """Frontmatter-only log.md, written at create time.

    Writing this immediately — rather than waiting for synthesis — is what
    makes `find` reliable. A run that copies photos and then dies still leaves
    a session that the next run will locate and complete, instead of a second
    directory for the same lesson.
    """
    frontmatter = {
        "schema": SCHEMA,
        "student": student_slug,
        "grade": student.get("grade"),
        "date": on_date.isoformat(),
        "subject": subject,
        "class": None,
        "lesson": {
            "curriculum": None,
            "number": None,
            "title": None,
            "source": None,
            "pages": None,
        },
        "teacher": "",
        "concepts": [],
    }
    body = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).strip()
    return f"---\n{body}\n---\n\nNot yet written up.\n"


def cmd_find(args: argparse.Namespace) -> dict[str, Any]:
    registry = load_registry(Path(args.registry))
    slug, _ = resolve_student(registry.get("students", {}), args.student)
    on_date = parse_iso_date(args.date)
    sessions = find_sessions(Path(args.root), slug, on_date, args.subject)
    return {
        "student": slug,
        "date": on_date.isoformat(),
        "subject": args.subject,
        "count": len(sessions),
        "sessions": sessions,
    }


def cmd_create(args: argparse.Namespace) -> dict[str, Any]:
    registry = load_registry(Path(args.registry))
    slug, student = resolve_student(registry.get("students", {}), args.student)

    subjects = [str(s) for s in student.get("subjects", []) or []]
    if subjects and args.subject not in subjects:
        raise SystemExit(
            f"subject {args.subject!r} is not one of {slug}'s configured subjects: "
            f"{', '.join(subjects)}"
        )

    on_date = parse_iso_date(args.date)
    root = Path(args.root)
    slug_part = slugify(args.slug)
    if not slug_part:
        raise SystemExit("--slug must contain at least one alphanumeric character")

    subject_part = slugify(args.subject)
    if not subject_part:
        raise SystemExit("--subject must contain at least one alphanumeric character")

    grade_root = root / slug / grade_dir_name(student.get("grade"))
    name = f"{subject_part}-{slug_part}"
    session_dir = session_day_dir(grade_root, on_date) / name

    # Same date, same subject, same content slug means this is the session that
    # already exists — late-arriving material for a lesson already logged.
    if session_dir.is_dir():
        return {"created": False, "reason": "already exists", **describe_session(session_dir)}

    (session_dir / "sources").mkdir(parents=True)
    (session_dir / "log.md").write_text(
        stub_log(slug, student, on_date, args.subject), encoding="utf-8"
    )
    return {"created": True, **describe_session(session_dir)}


def next_index(sources: Path, prefix: str) -> int:
    """Next free number for a role prefix. Never reuses or renumbers."""
    highest = 0
    for existing in sources.glob(f"{prefix}-*"):
        match = re.match(rf"{re.escape(prefix)}-(\d+)", existing.name)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cmd_add(args: argparse.Namespace) -> dict[str, Any]:
    session_dir = Path(args.session)
    sources = session_dir / "sources"
    if not sources.is_dir():
        raise SystemExit(f"not a session directory (no sources/): {session_dir}")

    prefix = ROLE_PREFIXES[args.role]
    existing = {digest(p): p.name for p in sources.iterdir() if p.is_file()}

    added = []
    for raw in args.file:
        source = Path(raw).expanduser()
        if not source.is_file():
            raise SystemExit(f"file not found: {source}")

        # Copying the same photo twice is a real risk in conversational mode,
        # where nothing marks material consumed. Identical bytes reuse the
        # name they already have.
        source_digest = digest(source)
        if source_digest in existing:
            added.append(
                {"source": str(source), "name": existing[source_digest], "deduped": True}
            )
            continue

        name = f"{prefix}-{next_index(sources, prefix):02d}{source.suffix.lower()}"
        shutil.copy2(source, sources / name)
        existing[source_digest] = name
        added.append({"source": str(source), "name": name, "deduped": False})

    return {"session": str(session_dir), "role": args.role, "added": added}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="lesson-logs root")
    parser.add_argument("--registry", default="students.yaml", help="student registry path")
    sub = parser.add_subparsers(dest="command", required=True)

    finder = sub.add_parser("find", help="list sessions for a student on a date")
    finder.add_argument("--student", required=True)
    finder.add_argument("--date", required=True, help="YYYY-MM-DD")
    finder.add_argument("--subject", help="exact configured subject name")
    finder.set_defaults(func=cmd_find)

    creator = sub.add_parser("create", help="create a session directory")
    creator.add_argument("--student", required=True)
    creator.add_argument("--date", required=True, help="YYYY-MM-DD")
    creator.add_argument("--subject", required=True, help="exact configured subject name")
    creator.add_argument("--slug", required=True, help="short content slug, e.g. lesson-112-guide-words")
    creator.set_defaults(func=cmd_create)

    adder = sub.add_parser("add", help="copy captured files into a session")
    adder.add_argument("--session", required=True, help="session directory path")
    adder.add_argument("--role", required=True, choices=sorted(ROLE_PREFIXES))
    adder.add_argument("--file", required=True, action="append", help="repeatable")
    adder.set_defaults(func=cmd_add)

    args = parser.parse_args()
    print(json.dumps(args.func(args), indent=2))


if __name__ == "__main__":
    main()
