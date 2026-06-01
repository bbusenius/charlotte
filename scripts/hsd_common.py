#!/usr/bin/env python3
"""Shared helpers for Homeschool-Dashboard-compatible Charlotte scripts."""

from __future__ import annotations

import re
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

import yaml


def normalize_header(value: Any) -> str:
    """Return a lowercase, whitespace-normalized column header."""
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def cell_text(value: Any) -> str:
    """Convert a spreadsheet cell value into stable display text."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%-m/%-d/%Y")
    if isinstance(value, date):
        return value.strftime("%-m/%-d/%Y")
    if isinstance(value, time):
        return value.strftime("%-I:%M %p").lstrip("0")
    return str(value).strip()


def parse_date(value: Any) -> date | None:
    """Parse common spreadsheet date values."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%m/%d/%Y", "%-m/%-d/%Y", "%Y-%m-%d", "%m/%d/%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_time(value: Any) -> time | None:
    """Parse common spreadsheet time values."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.time().replace(second=0, microsecond=0)
    if isinstance(value, time):
        return value.replace(second=0, microsecond=0)
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%I:%M %p", "%I %p", "%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    return None


def time_sort_key(value: Any) -> tuple[int, int, str]:
    """Return a sortable key for common spreadsheet time formats."""
    parsed = parse_time(value)
    text = cell_text(value)
    if parsed:
        return parsed.hour, parsed.minute, text
    return 99, 99, text


def duration_minutes(start_value: Any, end_value: Any) -> int | None:
    """Return same-day duration in minutes when both times parse."""
    start = parse_time(start_value)
    end = parse_time(end_value)
    if not start or not end:
        return None
    start_minutes = start.hour * 60 + start.minute
    end_minutes = end.hour * 60 + end.minute
    if end_minutes < start_minutes:
        return None
    return end_minutes - start_minutes


def find_column(headers: list[str], accepted: set[str]) -> int | None:
    """Find the first header whose normalized name is accepted."""
    for index, header in enumerate(headers):
        if header in accepted:
            return index
    return None


def load_registry(path: Path = Path("students.yaml")) -> dict[str, Any]:
    """Load the student registry."""
    if not path.is_file():
        raise SystemExit(f"students registry not found: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def resolve_student(students: dict[str, Any], query: str) -> tuple[str, dict[str, Any]]:
    """Resolve a student by slug, display name, or alias."""
    needle = query.strip().lower()
    for slug, data in students.items():
        candidates = {slug.lower(), str(data.get("display_name", "")).lower()}
        candidates.update(str(alias).lower() for alias in data.get("aliases", []) or [])
        if needle in candidates:
            return slug, data
    raise SystemExit(f"student not found: {query}")


def expand_existing_file(value: Any, label: str) -> Path:
    """Expand a configured path and require it to exist."""
    if not value:
        raise SystemExit(f"{label} missing")
    path = Path(str(value)).expanduser()
    if not path.is_file():
        raise SystemExit(f"{label} not found: {path}")
    return path
