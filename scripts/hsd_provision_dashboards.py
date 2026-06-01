#!/usr/bin/env python3
"""Generate configured Homeschool Dashboard HTML files opportunistically."""

from __future__ import annotations

import argparse
import traceback
from pathlib import Path
from typing import Any

from hsd_common import expand_existing_file, load_registry
from hsd_dashboard import default_output_path, save_dashboard_html


def write_log(log_dir: Path, slug: str, message: str) -> None:
    """Write a provisioning log for a student."""
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / f"{slug}.log").write_text(message.rstrip() + "\n", encoding="utf-8")


def provision_student(
    slug: str,
    student: dict[str, Any],
    log_dir: Path,
) -> tuple[bool, str]:
    """Generate one student's dashboard when its workbook is available."""
    try:
        workbook = expand_existing_file(
            student.get("time_tracking_spreadsheet"),
            f"{slug}.time_tracking_spreadsheet",
        )

        from homeschool_dashboard import save_html

        output = default_output_path(slug)
        save_dashboard_html(save_html, workbook, output)
        write_log(log_dir, slug, f"Generated {output.resolve()}")
        return True, slug
    except SystemExit:
        write_log(log_dir, slug, traceback.format_exc())
        return False, slug
    except Exception:
        write_log(log_dir, slug, traceback.format_exc())
        return False, slug


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description="Generate all configured student dashboard HTML files."
    )
    parser.add_argument("--students-yaml", default="students.yaml", type=Path)
    parser.add_argument("--log-dir", default=Path(".logs/hsd-dashboard"), type=Path)
    return parser


def main() -> int:
    """Run dashboard provisioning without failing the caller."""
    args = build_parser().parse_args()
    registry = load_registry(args.students_yaml)
    students = registry.get("students", {}) or {}

    generated: list[str] = []
    skipped: list[str] = []
    for slug, student in students.items():
        ok, name = provision_student(slug, student, args.log_dir)
        if ok:
            generated.append(name)
        else:
            skipped.append(name)

    if generated:
        print("Generated dashboards: " + ", ".join(generated))
    if skipped:
        print("Skipped dashboards: " + ", ".join(skipped))
        print(f"See logs in {args.log_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
