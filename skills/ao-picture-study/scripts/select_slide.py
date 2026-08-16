#!/usr/bin/env python3
"""Select an exact MindFeast slide as next using per-student settings."""

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


def resolve_student(students: dict[str, Any], query: str) -> tuple[str, dict[str, Any]]:
    q = norm(query)
    matches = []
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
    result: dict[str, Any] = {"status_code": response.status_code}
    if isinstance(parsed, dict):
        if "message" in parsed:
            result["response"] = str(parsed["message"])
        if parsed.get("activeSlideId"):
            result["active_slide_id"] = str(parsed["activeSlideId"])
    elif text:
        result["response"] = text[:997] + "..." if len(text) > 1000 else text
    return result


def select_one(
    slug: str,
    student: dict[str, Any],
    slide_id: str,
    timeout: float,
    dry_run: bool,
) -> dict[str, Any]:
    mindfeast = student.get("mindfeast") or {}
    remote_url = str(mindfeast.get("remote_url") or "").strip().rstrip("/")
    token = str(mindfeast.get("remote_token") or "").strip()
    result: dict[str, Any] = {
        "student": slug,
        "display_name": student.get("display_name") or slug,
        "slide_id": slide_id,
        "ok": False,
    }
    if not remote_url:
        result.update(status="missing_config", error="mindfeast.remote_url is missing")
        return result
    if not token:
        result.update(status="missing_config", error="mindfeast.remote_token is missing")
        return result

    endpoint = f"{remote_url}/api/slides/select"
    result["endpoint"] = endpoint_summary(endpoint)
    if dry_run:
        result.update(ok=True, status="dry_run")
        return result

    try:
        response = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {token}"},
            json={"id": slide_id},
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
    parser.add_argument("--student", required=True, help="Student slug, display name, or alias")
    parser.add_argument("--slide-id", required=True)
    parser.add_argument("--students-file", default="students.yaml", type=Path)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    students = load_students(args.students_file)
    slug, student = resolve_student(students, args.student)
    result = select_one(slug, student, args.slide_id, args.timeout, args.dry_run)
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
