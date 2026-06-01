#!/usr/bin/env python3
"""Generate Homeschool-Dashboard HTML for configured Charlotte students."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import webbrowser
from pathlib import Path
from typing import Callable

from hsd_common import expand_existing_file, load_registry, resolve_student


def default_output_path(slug: str) -> Path:
    """Return the default generated dashboard path."""
    return Path("dashboards") / f"{slug}.html"


def save_dashboard_html(
    save_html: Callable[[list[str], str], None],
    workbook: Path,
    output: Path,
) -> None:
    """Write dashboard HTML, replacing an existing output file."""
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            suffix=".tmp",
            prefix=f".{output.name}.",
            dir=output.parent,
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)

        save_html([str(workbook)], str(temp_path))
        os.replace(temp_path, output)
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description="Generate Homeschool-Dashboard HTML from Charlotte student config."
    )
    parser.add_argument("--students-yaml", default="students.yaml", type=Path)
    parser.add_argument("--student", required=True)
    parser.add_argument("--output", type=Path, help="Output HTML path")
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the generated dashboard in the default browser",
    )
    return parser


def main() -> int:
    """Run the CLI."""
    parser = build_parser()
    args = parser.parse_args()
    registry = load_registry(args.students_yaml)
    slug, student = resolve_student(registry.get("students", {}), args.student)
    workbook = expand_existing_file(student.get("time_tracking_spreadsheet"), "time_tracking_spreadsheet")
    output = args.output or default_output_path(slug)

    try:
        from homeschool_dashboard import save_html
    except ImportError as exc:
        raise SystemExit(
            "homeschool_dashboard is not installed. Run `.venv/bin/python -m pip install -e .` "
            "after installing Charlotte dependencies."
        ) from exc

    save_dashboard_html(save_html, workbook, output)
    resolved = output.resolve()
    if args.open:
        webbrowser.open(resolved.as_uri())

    print(
        json.dumps(
            {
                "student_slug": slug,
                "display_name": student.get("display_name", slug),
                "spreadsheet": str(workbook),
                "dashboard": str(resolved),
                "opened": bool(args.open),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
