#!/usr/bin/env python3
"""Trigger a MindFeast slide using per-student students.yaml settings."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
import yaml


def load_students(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    students = data.get("students")
    if not isinstance(students, dict):
        raise SystemExit(f"No students mapping found in {path}")
    return students


def norm(value: Any) -> str:
    return str(value or "").strip().lower()


def student_matches(slug: str, student: dict[str, Any], query: str) -> bool:
    q = norm(query)
    if not q:
        return False
    candidates = {norm(slug), norm(student.get("display_name"))}
    aliases = student.get("aliases") or []
    if isinstance(aliases, list):
        candidates.update(norm(alias) for alias in aliases)
    return q in candidates


def configured_students(
    students: dict[str, Any],
    query: str | None,
    all_students: bool,
) -> list[tuple[str, dict[str, Any]]]:
    if query:
        matches = [
            (slug, student)
            for slug, student in students.items()
            if isinstance(student, dict) and student_matches(slug, student, query)
        ]
        if not matches:
            raise SystemExit(f"No student matched {query!r}")
        return matches

    configured = []
    for slug, student in students.items():
        if not isinstance(student, dict):
            continue
        mindfeast = student.get("mindfeast") or {}
        if mindfeast.get("remote_url") and mindfeast.get("remote_token"):
            configured.append((slug, student))
    if not configured:
        raise SystemExit("No students have complete MindFeast trigger config")
    return configured


def endpoint_summary(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc or parsed.path
    path = parsed.path or "/"
    return f"{host}{path}"


def response_summary(response: requests.Response) -> dict[str, Any]:
    text = response.text.strip()
    parsed: Any = None
    if text:
        try:
            parsed = response.json()
        except ValueError:
            parsed = None

    result: dict[str, Any] = {
        "status_code": response.status_code,
    }
    if isinstance(parsed, dict):
        if "message" in parsed:
            result["response"] = str(parsed["message"])
        if parsed.get("slideId"):
            result["slide_id"] = str(parsed["slideId"])
    elif text:
        result["response"] = text[:997] + "..." if len(text) > 1000 else text
    return result


def trigger_one(slug: str, student: dict[str, Any], timeout: float, dry_run: bool) -> dict[str, Any]:
    mindfeast = student.get("mindfeast") or {}
    remote_url = str(mindfeast.get("remote_url") or "").strip().rstrip("/")
    token = str(mindfeast.get("remote_token") or "").strip()
    display_name = str(student.get("display_name") or slug)

    result: dict[str, Any] = {
        "student": slug,
        "display_name": display_name,
        "ok": False,
    }

    if not remote_url:
        result.update(status="missing_config", error="mindfeast.remote_url is missing")
        return result
    if not token:
        result.update(status="missing_config", error="mindfeast.remote_token is missing")
        return result

    endpoint = f"{remote_url}/api/trigger"
    result["endpoint"] = endpoint_summary(endpoint)

    if dry_run:
        result.update(ok=True, status="dry_run")
        return result

    try:
        response = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )
    except requests.RequestException as exc:
        result.update(status="request_error", error=str(exc))
        return result

    result.update(
        ok=response.ok,
        status="completed" if response.ok else "http_error",
        **response_summary(response),
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("student_arg", nargs="?", help="Student slug, display name, or alias")
    parser.add_argument("--student", dest="student_opt", help="Student slug, display name, or alias")
    parser.add_argument("--all", action="store_true", help="Trigger all configured students")
    parser.add_argument("--dry-run", action="store_true", help="Validate config without POSTing")
    parser.add_argument("--students-file", default="students.yaml", help="Path to students.yaml")
    parser.add_argument("--timeout", type=float, default=30.0, help="Request timeout in seconds")
    args = parser.parse_args()

    student = args.student_opt or args.student_arg
    if args.student_opt and args.student_arg:
        parser.error("pass the student either positionally or with --student, not both")
    if student and args.all:
        parser.error("use either a student or --all, not both")

    students = load_students(Path(args.students_file))
    selected = configured_students(students, student, args.all)
    results = [trigger_one(slug, student, args.timeout, args.dry_run) for slug, student in selected]

    print(json.dumps({"results": results}, indent=2))
    return 0 if all(result.get("ok") for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
