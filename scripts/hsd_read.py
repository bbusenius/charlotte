#!/usr/bin/env python3
"""Read Homeschool-Dashboard-compatible records as compact JSON."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import openpyxl

from hsd_common import (
    cell_text,
    duration_minutes,
    expand_existing_file,
    find_column,
    load_registry,
    normalize_header,
    parse_date,
    resolve_student,
    time_sort_key,
)

DATE_HEADERS = {"date"}
START_HEADERS = {"start time", "start"}
END_HEADERS = {"end time", "end"}
DESCRIPTION_HEADERS = {"description", "lesson", "task"}
TEACHER_HEADERS = {"teacher"}
NOTES_HEADERS = {"notes", "note"}

BOOK_HEADERS = {
    "title": {"title"},
    "author": {"author"},
    "language": {"language"},
    "isbn": {"isbn"},
    "sku": {"sku"},
    "level": {"level", "lexile", "reading level"},
    "audiobook": {"audiobook", "audio book"},
    "coursework": {"part of coursework?", "coursework", "part of coursework"},
}


def row_value(row: tuple[Any, ...], index: int | None) -> Any:
    """Return a cell value when the index exists."""
    if index is None or index >= len(row):
        return None
    return row[index]


def parse_cli_date(value: str | None) -> Any:
    """Parse YYYY-MM-DD command-line dates."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise SystemExit(f"invalid date {value!r}; use YYYY-MM-DD") from exc


def collect_time_rows(
    workbook_path: Path,
    subjects: list[str],
    subject_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Collect lesson rows from a time-tracking workbook."""
    wb = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)
    rows: list[dict[str, Any]] = []
    subject_names = subjects or wb.sheetnames
    if subject_filter:
        subject_names = [subject_filter]

    for subject in subject_names:
        if subject not in wb.sheetnames:
            continue
        ws = wb[subject]
        iterator = ws.iter_rows(values_only=True)
        try:
            header_row = next(iterator)
        except StopIteration:
            continue

        headers = [normalize_header(value) for value in header_row]
        date_col = find_column(headers, DATE_HEADERS)
        start_col = find_column(headers, START_HEADERS)
        end_col = find_column(headers, END_HEADERS)
        desc_col = find_column(headers, DESCRIPTION_HEADERS)
        teacher_col = find_column(headers, TEACHER_HEADERS)
        notes_col = find_column(headers, NOTES_HEADERS)
        if date_col is None or desc_col is None:
            continue

        for index, row in enumerate(iterator, start=2):
            row_date = parse_date(row_value(row, date_col))
            description = cell_text(row_value(row, desc_col))
            notes = cell_text(row_value(row, notes_col))
            if row_date is None or (not description and not notes):
                continue
            start_value = row_value(row, start_col)
            end_value = row_value(row, end_col)
            rows.append(
                {
                    "subject": subject,
                    "date": row_date.isoformat(),
                    "date_display": cell_text(row_value(row, date_col)),
                    "start_time": cell_text(start_value),
                    "end_time": cell_text(end_value),
                    "duration_minutes": duration_minutes(start_value, end_value),
                    "description": description,
                    "teacher": cell_text(row_value(row, teacher_col)),
                    "notes": notes,
                    "sheet": subject,
                    "workbook_row": index,
                }
            )

    wb.close()
    rows.sort(
        key=lambda item: (
            item["date"],
            time_sort_key(item["start_time"]),
            item["subject"],
            item["workbook_row"],
        )
    )
    return rows


def filter_time_rows(args: argparse.Namespace, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply CLI filters to time rows."""
    start = parse_cli_date(args.from_date)
    end = parse_cli_date(args.to_date)
    query = args.query.lower() if args.query else None

    filtered: list[dict[str, Any]] = []
    for row in rows:
        row_date = parse_cli_date(row["date"])
        if start and row_date < start:
            continue
        if end and row_date > end:
            continue
        if query:
            haystack = " ".join(
                [
                    row.get("subject", ""),
                    row.get("description", ""),
                    row.get("teacher", ""),
                    row.get("notes", ""),
                ]
            ).lower()
            if query not in haystack:
                continue
        filtered.append(row)

    if args.latest:
        filtered = list(reversed(filtered))[: args.latest]
    elif args.limit:
        filtered = filtered[: args.limit]
    return filtered


def sheet_role(reading: dict[str, Any], index: int) -> str:
    """Return the configured role for a reading-list sheet index."""
    try:
        read_by_self_index = int(reading.get("read_by_self_sheet_index", -1))
    except (TypeError, ValueError):
        read_by_self_index = -1
    try:
        read_to_index = int(reading.get("read_to_sheet_index", -1))
    except (TypeError, ValueError):
        read_to_index = -1

    if index == read_by_self_index:
        return "read_by_self"
    if index == read_to_index:
        return "read_to"
    return "unknown"


def collect_book_rows(workbook_path: Path, reading: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect rows from a reading-list workbook."""
    wb = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)
    rows: list[dict[str, Any]] = []
    for sheet_index, sheet_name in enumerate(wb.sheetnames):
        ws = wb[sheet_name]
        iterator = ws.iter_rows(values_only=True)
        try:
            header_row = next(iterator)
        except StopIteration:
            continue

        headers = [normalize_header(value) for value in header_row]
        columns = {
            field: find_column(headers, accepted)
            for field, accepted in BOOK_HEADERS.items()
        }
        if columns["title"] is None:
            continue

        for index, row in enumerate(iterator, start=2):
            title = cell_text(row_value(row, columns["title"]))
            if not title:
                continue
            item = {
                field: cell_text(row_value(row, column_index))
                for field, column_index in columns.items()
            }
            item.update(
                {
                    "sheet": sheet_name,
                    "sheet_index": sheet_index,
                    "list_type": sheet_role(reading, sheet_index),
                    "workbook_row": index,
                }
            )
            rows.append(item)
    wb.close()
    return rows


def filter_book_rows(args: argparse.Namespace, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply CLI filters to reading-list rows."""
    query = args.query.lower() if args.query else None
    filtered: list[dict[str, Any]] = []
    for row in rows:
        if args.list_type != "all" and row.get("list_type") != args.list_type:
            continue
        if query:
            haystack = " ".join(
                [
                    row.get("title", ""),
                    row.get("author", ""),
                    row.get("language", ""),
                    row.get("isbn", ""),
                    row.get("level", ""),
                    row.get("sheet", ""),
                ]
            ).lower()
            if query not in haystack:
                continue
        filtered.append(row)

    if args.latest:
        filtered = sorted(
            filtered,
            key=lambda item: (item["workbook_row"], item["sheet_index"]),
            reverse=True,
        )[: args.latest]
    elif args.limit:
        filtered = filtered[: args.limit]
    return filtered


def emit(result: dict[str, Any]) -> int:
    """Print JSON result."""
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def run_time(args: argparse.Namespace, slug: str, student: dict[str, Any]) -> int:
    """Run the time-log reader."""
    workbook = expand_existing_file(student.get("time_tracking_spreadsheet"), "time_tracking_spreadsheet")
    subjects = student.get("subjects", []) or []
    rows = collect_time_rows(workbook, subjects, args.subject)
    rows = filter_time_rows(args, rows)
    return emit(
        {
            "student_slug": slug,
            "display_name": student.get("display_name", slug),
            "kind": "time",
            "spreadsheet": str(workbook),
            "row_count": len(rows),
            "rows": rows,
        }
    )


def run_books(args: argparse.Namespace, slug: str, student: dict[str, Any]) -> int:
    """Run the reading-list reader."""
    reading = student.get("reading", {}) or {}
    workbook = expand_existing_file(reading.get("spreadsheet"), "reading.spreadsheet")
    rows = collect_book_rows(workbook, reading)
    rows = filter_book_rows(args, rows)
    return emit(
        {
            "student_slug": slug,
            "display_name": student.get("display_name", slug),
            "kind": "books",
            "spreadsheet": str(workbook),
            "row_count": len(rows),
            "rows": rows,
        }
    )


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description="Read Charlotte Homeschool-Dashboard-compatible records as JSON."
    )
    parser.add_argument("--students-yaml", default="students.yaml", type=Path)
    parser.add_argument("--student", required=True)
    subparsers = parser.add_subparsers(dest="kind", required=True)

    time_parser = subparsers.add_parser("time", help="Read lesson time records")
    time_parser.add_argument("--subject", help="Exact subject/sheet name, e.g. Math")
    time_parser.add_argument("--from", dest="from_date", help="Start date YYYY-MM-DD")
    time_parser.add_argument("--to", dest="to_date", help="End date YYYY-MM-DD")
    time_parser.add_argument("--query", help="Case-insensitive text search")
    time_parser.add_argument("--latest", type=int, help="Return the N latest matching rows")
    time_parser.add_argument("--limit", type=int, help="Return at most N rows in chronological order")

    books_parser = subparsers.add_parser("books", help="Read reading-list records")
    books_parser.add_argument("--query", help="Case-insensitive title/author/etc. search")
    books_parser.add_argument(
        "--list-type",
        choices=("all", "read_by_self", "read_to"),
        default="all",
        help="Filter by configured reading-list role",
    )
    books_parser.add_argument("--latest", type=int, help="Return the N latest appended matching rows")
    books_parser.add_argument("--limit", type=int, help="Return at most N rows in workbook order")
    return parser


def main() -> int:
    """Run the CLI."""
    parser = build_parser()
    args = parser.parse_args()
    registry = load_registry(args.students_yaml)
    slug, student = resolve_student(registry.get("students", {}), args.student)
    if args.kind == "time":
        return run_time(args, slug, student)
    if args.kind == "books":
        return run_books(args, slug, student)
    parser.error(f"unsupported kind: {args.kind}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
