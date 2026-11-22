#!/usr/bin/env python3
"""Decide whether a student's next AO study is a picture study or a composer study.

Picture study and composer study alternate by what was last created, not by
the calendar. A missed or late run therefore never skips a study: the next run
creates whichever kind did not come last.

The decision reads the two committed cursors under ``.state/``:

    .state/ao-picture-study/<student>.yaml   (last_created)
    .state/ao-composer-study/<student>.yaml  (last_presented)

Each cursor's commit time is its ``committed_at`` field. Cursors written before
that field existed fall back to the state file's modification time.

- Neither cursor exists: picture.
- Only one exists: the other kind.
- Both exist: the kind committed less recently.

Output is JSON on stdout.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hsd_common import load_registry, resolve_student  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_ROOT = REPO_ROOT / ".state"

KINDS = {
    "picture": ("ao-picture-study", "last_created"),
    "composer": ("ao-composer-study", "last_presented"),
}


def read_cursor(state_root: Path, kind: str, student_slug: str) -> dict[str, Any] | None:
    """Return the committed cursor for one kind, with its commit time, or None."""
    directory, key = KINDS[kind]
    path = state_root / directory / f"{student_slug}.yaml"
    if not path.is_file():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    cursor = data.get(key)
    if not isinstance(cursor, dict):
        raise SystemExit(f"Unrecognized AO {kind}-study state in {path}")
    committed_at = cursor.get("committed_at")
    if committed_at:
        moment = datetime.fromisoformat(str(committed_at))
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        source = "committed_at"
    else:
        moment = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        source = "file_mtime"
    return {
        "kind": kind,
        "title": cursor.get("title"),
        "creator": cursor.get("artist") or cursor.get("composer"),
        "committed_at": moment.isoformat(timespec="seconds"),
        "committed_at_source": source,
        "state_path": str(path),
        "_moment": moment,
    }


def decide(state_root: Path, student_slug: str) -> dict[str, Any]:
    cursors = {
        kind: read_cursor(state_root, kind, student_slug) for kind in KINDS
    }
    present = [cursor for cursor in cursors.values() if cursor]
    if not present:
        next_kind, last = "picture", None
    elif len(present) == 1:
        last = present[0]
        next_kind = "composer" if last["kind"] == "picture" else "picture"
    else:
        last = max(present, key=lambda cursor: cursor["_moment"])
        next_kind = "composer" if last["kind"] == "picture" else "picture"
    for cursor in present:
        cursor.pop("_moment")
    return {
        "student": student_slug,
        "next": next_kind,
        "last_created": last,
        "cursors": cursors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--student", required=True)
    parser.add_argument("--students-file", default=REPO_ROOT / "students.yaml", type=Path)
    parser.add_argument("--state-root", default=DEFAULT_STATE_ROOT, type=Path)
    args = parser.parse_args()

    registry = load_registry(args.students_file)
    student_slug, _student = resolve_student(registry.get("students") or {}, args.student)
    print(json.dumps(decide(args.state_root, student_slug), indent=2))


if __name__ == "__main__":
    main()
