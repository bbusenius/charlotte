#!/usr/bin/env python3
"""Project lesson logs into Homeschool-Dashboard time-tracking workbooks.

The lesson log is the system of record; a spreadsheet row is a thin receipt of
it. This script fills gaps: it finds logged sessions that have no row yet and
appends them.

It never updates or rewrites an existing row. Hand edits in the workbook are
safe, and running this twice writes nothing the second time. It only ever looks
at (date, subject) pairs that have a lesson log behind them, so rows from before
lesson logging existed are never touched and never counted as missing.

Subcommands:

    gaps    list logged sessions that have no spreadsheet row yet
    append  write the row for one session

All output is JSON on stdout.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date as date_cls
from datetime import datetime
from pathlib import Path
from typing import Any

import openpyxl
import yaml
from openpyxl.utils import get_column_letter

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hsd_common import (  # noqa: E402
    expand_existing_file,
    load_registry,
    normalize_header,
    parse_date,
    parse_time,
    resolve_student,
)
from lesson_log_new import grade_dir_name, iter_session_dirs, read_frontmatter  # noqa: E402

DEFAULT_ROOT = Path("lesson-logs")
DESCRIPTION_HEADER = "description"
NOTES_HEADERS = {"notes", "note"}
SESSION_ID_HEADER = "lesson log id"
REQUIRED_HEADERS = {"date", "start time", "end time", "description", "teacher"}


def load_logging_config(path: Path) -> dict[str, Any]:
    """Read the global logging switches, applying documented defaults."""
    data: dict[str, Any] = {}
    if path.is_file():
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        data = loaded.get("logging") or {}
    config = {
        "lesson_log": data.get("lesson_log", True),
        "time": data.get("time", True),
        "hsd": data.get("hsd", False),
    }
    if config["hsd"] and not config["lesson_log"]:
        raise SystemExit(
            "configuration error: logging.hsd requires logging.lesson_log, because "
            "Homeschool-Dashboard rows are projected from lesson logs"
        )
    if config["hsd"] and not config["time"]:
        raise SystemExit(
            "configuration error: logging.hsd requires logging.time, because "
            "Homeschool-Dashboard needs start and end times"
        )
    return config


def format_date(value: date_cls) -> str:
    """M/D/YYYY with no leading zeros, matching the existing workbooks."""
    return f"{value.month}/{value.day}/{value.year}"


def session_logs(
    root: Path,
    student_slug: str,
    grade: Any,
    date_from: date_cls | None,
    date_to: date_cls | None,
) -> list[dict[str, Any]]:
    """Load logs for the student's current grade, oldest first.

    Scoped to the current grade directory on purpose: a previous grade's logs
    belong to a previous grade's workbook, which this student's configured
    spreadsheet is not.
    """
    grade_root = root / student_slug / grade_dir_name(grade)
    if not grade_root.is_dir():
        return []

    logs = []
    for session in iter_session_dirs(grade_root):
        frontmatter = read_frontmatter(session / "log.md")
        if not frontmatter:
            continue
        on_date = parse_date(frontmatter.get("date"))
        if on_date is None:
            continue
        if date_from and on_date < date_from:
            continue
        if date_to and on_date > date_to:
            continue
        logs.append(
            {
                "path": str(session),
                "session_id": session_id(root, session),
                "date": on_date,
                "frontmatter": frontmatter,
            }
        )
    return logs


def sheet_headers(worksheet) -> list[str]:
    first = next(worksheet.iter_rows(min_row=1, max_row=1), ())
    return [normalize_header(cell.value) for cell in first]


def validate_headers(worksheet) -> list[str]:
    """Require the columns Charlotte writes before touching a sheet."""
    headers = sheet_headers(worksheet)
    missing = sorted(REQUIRED_HEADERS - set(headers))
    if missing:
        raise SystemExit(
            f"sheet {worksheet.title!r} is missing required columns: "
            f"{', '.join(missing)}"
        )
    return headers


def projection_state(
    worksheet,
) -> tuple[set[str], set[tuple[date_cls, Any]]]:
    """Return stable session IDs and legacy (date, start) keys.

    Rows written by this projector carry a hidden stable ID. Rows that predate
    the ID column retain the date/start fallback so existing workbooks migrate
    without duplicate rows.
    """
    headers = validate_headers(worksheet)
    date_col = headers.index("date")
    start_col = headers.index("start time")
    id_col = headers.index(SESSION_ID_HEADER) if SESSION_ID_HEADER in headers else None

    session_ids: set[str] = set()
    legacy_keys: set[tuple[date_cls, Any]] = set()
    for row in worksheet.iter_rows(min_row=2, values_only=True):
        if date_col >= len(row) or start_col >= len(row):
            continue
        on_date = parse_date(row[date_col])
        start = parse_time(row[start_col])
        if on_date is None:
            continue

        raw_id = row[id_col] if id_col is not None and id_col < len(row) else None
        stable_id = str(raw_id).strip() if raw_id is not None else ""
        if stable_id:
            session_ids.add(stable_id)
        else:
            legacy_keys.add((on_date, start))
    return session_ids, legacy_keys


def session_id(root: Path, session: Path) -> str:
    """Stable workbook identity derived from the canonical session path."""
    root = root.expanduser().resolve()
    session = session.expanduser().resolve()
    try:
        relative = session.relative_to(root)
    except ValueError:
        raise SystemExit(f"log is outside the lesson-logs root: {session}") from None
    if len(relative.parts) != 6:
        raise SystemExit(f"log path is not a complete lesson session: {session}")
    return relative.as_posix()


def ensure_session_id_header(worksheet) -> list[str]:
    """Add and hide the stable projection-ID column when first needed."""
    headers = validate_headers(worksheet)
    if SESSION_ID_HEADER in headers:
        return headers

    column = worksheet.max_column + 1
    worksheet.cell(row=1, column=column, value="Lesson Log ID")
    worksheet.column_dimensions[get_column_letter(column)].hidden = True
    return sheet_headers(worksheet)


def cmd_gaps(args: argparse.Namespace) -> dict[str, Any]:
    config = load_logging_config(Path(args.runtime))
    registry = load_registry(Path(args.registry))
    slug, student = resolve_student(registry.get("students", {}), args.student)

    if not config["hsd"]:
        return {
            "student": slug,
            "workbook": None,
            "hsd_enabled": False,
            "logs_examined": 0,
            "already_logged": 0,
            "pending": [],
            "waiting_on_times": [],
            "unknown_subject": [],
        }

    workbook_path = expand_existing_file(
        student.get("time_tracking_spreadsheet"), f"{slug} time_tracking_spreadsheet"
    )
    workbook = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)

    date_from = parse_date(args.date_from) if args.date_from else None
    date_to = parse_date(args.date_to) if args.date_to else None
    logs = session_logs(Path(args.root), slug, student.get("grade"), date_from, date_to)

    stable_ids: dict[str, set[str]] = {}
    legacy_keys: dict[str, set[tuple[date_cls, Any]]] = {}
    columns: dict[str, list[str]] = {}
    for name in workbook.sheetnames:
        stable_ids[name], legacy_keys[name] = projection_state(workbook[name])
        columns[name] = validate_headers(workbook[name])

    pending, waiting_on_times, already_logged, unknown_subject = [], [], 0, []
    for log in logs:
        frontmatter = log["frontmatter"]
        subject = frontmatter.get("subject")
        start = parse_time(frontmatter.get("start_time"))
        end = parse_time(frontmatter.get("end_time"))
        entry = {
            "path": log["path"],
            "session_id": log["session_id"],
            "date": log["date"].isoformat(),
            "subject": subject,
            "start_time": frontmatter.get("start_time"),
            "end_time": frontmatter.get("end_time"),
            "teacher": frontmatter.get("teacher", ""),
            "lesson": frontmatter.get("lesson"),
        }

        if subject not in stable_ids:
            unknown_subject.append(entry)
            continue
        if start is None or end is None:
            waiting_on_times.append(entry)
            continue
        if (
            log["session_id"] in stable_ids[subject]
            or (log["date"], start) in legacy_keys[subject]
        ):
            already_logged += 1
            continue

        entry["has_notes_column"] = any(h in NOTES_HEADERS for h in columns[subject])
        pending.append(entry)

    workbook.close()
    return {
        "student": slug,
        "workbook": str(workbook_path),
        "hsd_enabled": config["hsd"],
        "logs_examined": len(logs),
        "already_logged": already_logged,
        "pending": pending,
        "waiting_on_times": waiting_on_times,
        "unknown_subject": unknown_subject,
    }


def build_row(headers: list[str], values: dict[str, str]) -> list[str]:
    """Lay values out by header name, padding everything else blank.

    xlsx-append writes positionally, and Notes sits at a different index on
    every sheet, so the position has to come from the header row.
    """
    row = []
    for header in headers:
        if header in NOTES_HEADERS:
            row.append(values.get("notes", ""))
        else:
            row.append(values.get(header, ""))
    while row and row[-1] == "":
        row.pop()
    return row


def cmd_append(args: argparse.Namespace) -> dict[str, Any]:
    from xlsx_append.cli import append_row

    config = load_logging_config(Path(args.runtime))
    if not config["hsd"]:
        raise SystemExit("logging.hsd is disabled in runtime.yaml")

    registry = load_registry(Path(args.registry))
    slug, student = resolve_student(registry.get("students", {}), args.student)

    log_path = Path(args.log)
    stable_id = session_id(Path(args.root), log_path)
    expected_prefix = [slug, grade_dir_name(student.get("grade"))]
    if stable_id.split("/")[:2] != expected_prefix:
        raise SystemExit(
            f"log {stable_id!r} does not belong to {slug}'s current grade"
        )

    frontmatter = read_frontmatter(log_path / "log.md")
    if not frontmatter:
        raise SystemExit(f"no readable log.md in {args.log}")
    if frontmatter.get("student") != slug:
        raise SystemExit(
            f"log belongs to {frontmatter.get('student')!r}, "
            f"not requested student {slug!r}"
        )

    subject = frontmatter.get("subject")
    on_date = parse_date(frontmatter.get("date"))
    start = parse_time(frontmatter.get("start_time"))
    end = parse_time(frontmatter.get("end_time"))
    if on_date is None:
        raise SystemExit(f"log has no usable date: {args.log}")
    if start is None or end is None:
        raise SystemExit(
            f"log has no start/end time yet, so it cannot be projected: {args.log}"
        )

    workbook_path = expand_existing_file(
        student.get("time_tracking_spreadsheet"), f"{slug} time_tracking_spreadsheet"
    )
    workbook = openpyxl.load_workbook(workbook_path)
    if subject not in workbook.sheetnames:
        raise SystemExit(
            f"sheet {subject!r} not found in {workbook_path.name}. "
            f"Available: {', '.join(workbook.sheetnames)}"
        )

    worksheet = workbook[subject]
    headers = validate_headers(worksheet)
    session_ids, legacy_keys = projection_state(worksheet)
    # Re-check at write time; the gap listing may be minutes old.
    if stable_id in session_ids or (on_date, start) in legacy_keys:
        workbook.close()
        return {
            "written": False,
            "reason": (
                "this lesson-log session already has a row"
                if stable_id in session_ids
                else "a legacy row already exists for this date and start time"
            ),
            "log": args.log,
            "session_id": stable_id,
            "sheet": subject,
        }

    headers = ensure_session_id_header(worksheet)
    workbook.save(workbook_path)
    workbook.close()

    values = {
        "date": format_date(on_date),
        "start time": start.strftime("%-I:%M %p"),
        "end time": end.strftime("%-I:%M %p"),
        DESCRIPTION_HEADER: args.description,
        "teacher": frontmatter.get("teacher", "") or "",
        SESSION_ID_HEADER: stable_id,
    }
    has_notes = any(h in NOTES_HEADERS for h in headers)
    if args.notes and has_notes:
        values["notes"] = args.notes

    row = build_row(headers, values)
    row_number = append_row(workbook_path, subject, row)
    return {
        "written": True,
        "log": args.log,
        "session_id": stable_id,
        "sheet": subject,
        "row": row_number,
        "notes_written": bool(args.notes and has_notes),
        "notes_skipped_no_column": bool(args.notes and not has_notes),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="lesson-logs root")
    parser.add_argument("--registry", default="students.yaml")
    parser.add_argument("--runtime", default="runtime.yaml")
    sub = parser.add_subparsers(dest="command", required=True)

    gaps = sub.add_parser("gaps", help="logged sessions with no spreadsheet row")
    gaps.add_argument("--student", required=True)
    gaps.add_argument("--from", dest="date_from", help="YYYY-MM-DD")
    gaps.add_argument("--to", dest="date_to", help="YYYY-MM-DD")
    gaps.set_defaults(func=cmd_gaps)

    append = sub.add_parser("append", help="write the row for one session")
    append.add_argument("--student", required=True)
    append.add_argument("--log", required=True, help="session directory path")
    append.add_argument("--description", required=True, help="one-sentence summary")
    append.add_argument("--notes", help="observations; written only if the sheet has Notes")
    append.set_defaults(func=cmd_append)

    args = parser.parse_args()
    print(json.dumps(args.func(args), indent=2))


if __name__ == "__main__":
    main()
