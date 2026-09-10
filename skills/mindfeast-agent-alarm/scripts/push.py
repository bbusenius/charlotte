#!/usr/bin/env python3
"""Push atmosphere / alarm settings to MindFeast Agent Alarm over LAN."""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
import yaml

TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")


def load_students(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"No students mapping found in {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    students = data.get("students") if isinstance(data, dict) else None
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


def alarm_config(student: dict[str, Any]) -> tuple[str, str]:
    block = student.get("agent_alarm") or {}
    if not isinstance(block, dict):
        block = {}
    url = str(block.get("remote_url") or "").strip().rstrip("/")
    token = str(block.get("remote_token") or "").strip()
    return url, token


def configured_students(
    students: dict[str, Any],
    query: str | None,
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
        url, token = alarm_config(student)
        if url and token:
            configured.append((slug, student))
    if not configured:
        raise SystemExit("No students have complete Agent Alarm config")
    return configured


def endpoint_summary(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc or parsed.path
    path = parsed.path or ""
    if path in {"", "/"}:
        return host
    return f"{host}{path}"


def headers(token: str, content_type: str | None = None, filename: str | None = None) -> dict[str, str]:
    out = {"Authorization": f"Bearer {token}"}
    if content_type:
        out["Content-Type"] = content_type
    if filename:
        out["X-Filename"] = Path(filename).name
    return out


def request(
    method: str,
    base: str,
    path: str,
    token: str,
    *,
    timeout: float,
    dry_run: bool,
    json_body: Any | None = None,
    data: bytes | None = None,
    content_type: str | None = None,
    filename: str | None = None,
) -> dict[str, Any]:
    url = f"{base}{path}"
    summary = {"method": method, "endpoint": endpoint_summary(url)}
    if dry_run:
        summary["dry_run"] = True
        summary["ok"] = True
        return summary
    try:
        resp = requests.request(
            method,
            url,
            headers=headers(token, content_type=content_type, filename=filename),
            json=json_body,
            data=data,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        summary["ok"] = False
        summary["error"] = str(exc)
        return summary
    summary["status_code"] = resp.status_code
    try:
        body = resp.json()
    except ValueError:
        body = {"raw": resp.text[:500]}
    summary["ok"] = resp.ok
    summary["body"] = body
    return summary


def guess_audio_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(str(path))
    if guessed and guessed.startswith("audio/"):
        return guessed
    return "application/octet-stream"


def guess_image_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(str(path))
    if guessed in {"image/jpeg", "image/png", "image/webp"}:
        return guessed
    suffix = path.suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(suffix, "application/octet-stream")


def parse_time(value: str) -> str:
    match = TIME_RE.fullmatch(value.strip())
    if not match:
        raise SystemExit("--time must be HH:MM (24-hour)")
    hour = int(match.group(1))
    minute = int(match.group(2))
    if hour > 23 or minute > 59:
        raise SystemExit("--time must be HH:MM (24-hour)")
    return f"{hour:02d}:{minute:02d}"


def mutation_requested(args: argparse.Namespace) -> bool:
    return any(
        [
            args.audio,
            args.picture,
            args.artist is not None,
            args.title is not None,
            args.composer is not None,
            args.audio_title is not None,
            args.notes is not None,
            args.notes_heading is not None,
            args.theme,
            args.theme_restore_default,
            args.time,
            args.enable,
            args.disable,
            args.use_24_hour,
            args.use_12_hour,
        ]
    )


def parse_theme(args: argparse.Namespace) -> dict[str, Any] | None:
    if not args.theme:
        return None
    try:
        theme_obj = json.loads(args.theme)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid --theme JSON: {exc}") from exc
    if not isinstance(theme_obj, dict):
        raise SystemExit("--theme must be a JSON object")
    return theme_obj


def resolve_media(path_arg: Path | None, *, kind: str) -> Path | None:
    if path_arg is None:
        return None
    path = path_arg.expanduser().resolve()
    if not path.is_file():
        raise SystemExit(f"{kind} file not found: {path}")
    return path


def push_one(
    slug: str,
    student: dict[str, Any],
    args: argparse.Namespace,
    *,
    alarm_time: str | None,
    theme_obj: dict[str, Any] | None,
    audio_path: Path | None,
    picture_path: Path | None,
) -> dict[str, Any]:
    display_name = str(student.get("display_name") or slug)
    result: dict[str, Any] = {
        "student": slug,
        "display_name": display_name,
        "ok": False,
    }
    base, token = alarm_config(student)
    if not base:
        result.update(status="missing_config", error="agent_alarm.remote_url is missing")
        return result
    if not token:
        result.update(status="missing_config", error="agent_alarm.remote_token is missing")
        return result

    result["base"] = endpoint_summary(base)
    operations: list[dict[str, Any]] = []

    def run(**kwargs: Any) -> None:
        operations.append(
            request(timeout=args.timeout, dry_run=args.dry_run, token=token, base=base, **kwargs)
        )

    if args.status:
        run(method="GET", path="/api/status")

    if audio_path is not None:
        run(
            method="POST",
            path="/api/audio",
            data=audio_path.read_bytes() if not args.dry_run else None,
            content_type=guess_audio_type(audio_path),
            filename=audio_path.name,
        )

    if picture_path is not None:
        run(
            method="POST",
            path="/api/picture",
            data=picture_path.read_bytes() if not args.dry_run else None,
            content_type=guess_image_type(picture_path),
            filename=picture_path.name,
        )

    if args.artist is not None or args.title is not None:
        run(
            method="POST",
            path="/api/picture/meta",
            json_body={
                "artist": args.artist if args.artist is not None else "",
                "title": args.title if args.title is not None else "",
            },
            content_type="application/json",
        )

    if args.composer is not None or args.audio_title is not None:
        run(
            method="POST",
            path="/api/audio/meta",
            json_body={
                "composer": args.composer if args.composer is not None else "",
                "title": args.audio_title if args.audio_title is not None else "",
            },
            content_type="application/json",
        )

    if args.notes is not None or args.notes_heading is not None:
        body: dict[str, str] = {}
        if args.notes is not None:
            body["notes"] = args.notes
        if args.notes_heading is not None:
            body["notesHeading"] = args.notes_heading
        run(method="POST", path="/api/notes", json_body=body, content_type="application/json")

    if args.theme_restore_default:
        run(method="POST", path="/api/theme/restore-default", json_body={}, content_type="application/json")
    elif theme_obj is not None:
        run(method="POST", path="/api/theme", json_body=theme_obj, content_type="application/json")

    if args.use_24_hour or args.use_12_hour:
        run(
            method="POST",
            path="/api/alarm/clock",
            json_body={"use24Hour": bool(args.use_24_hour)},
            content_type="application/json",
        )

    if alarm_time:
        run(
            method="POST",
            path="/api/alarm/time",
            json_body={"time": alarm_time},
            content_type="application/json",
        )

    if args.enable or args.disable:
        run(
            method="POST",
            path="/api/alarm/enable",
            json_body={"enabled": bool(args.enable)},
            content_type="application/json",
        )

    mutated = any(item.get("method") == "POST" for item in operations)
    if mutated and not args.dry_run:
        run(method="GET", path="/api/status")

    result["operations"] = operations
    result["ok"] = bool(operations) and all(item.get("ok") for item in operations)
    if args.dry_run:
        result["status"] = "dry_run"
    elif result["ok"]:
        result["status"] = "completed"
    else:
        result["status"] = "http_error"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("student_arg", nargs="?", help="Student slug, display name, or alias")
    parser.add_argument("--student", dest="student_opt", help="Student slug, display name, or alias")
    parser.add_argument("--all", action="store_true", help="Push to all students with Agent Alarm config")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--students-file", default="students.yaml", help="Path to students.yaml")
    parser.add_argument("--audio", type=Path)
    parser.add_argument("--picture", type=Path)
    parser.add_argument("--artist")
    parser.add_argument("--title")
    parser.add_argument("--composer", help="Wake-sound composer (POST /api/audio/meta)")
    parser.add_argument("--audio-title", help="Wake-sound song title (POST /api/audio/meta)")
    parser.add_argument("--notes")
    parser.add_argument("--notes-heading")
    parser.add_argument("--theme", help="JSON object of theme tokens")
    parser.add_argument("--theme-restore-default", action="store_true")
    parser.add_argument("--time", help="HH:MM local wake time")
    parser.add_argument("--enable", action="store_true")
    parser.add_argument("--disable", action="store_true")
    parser.add_argument("--use-24-hour", action="store_true")
    parser.add_argument("--use-12-hour", action="store_true")
    args = parser.parse_args(argv)

    student = args.student_opt or args.student_arg
    if args.student_opt and args.student_arg:
        parser.error("pass the student either positionally or with --student, not both")
    if student and args.all:
        parser.error("use either a student or --all, not both")

    if args.enable and args.disable:
        raise SystemExit("Pass only one of --enable / --disable")
    if args.use_24_hour and args.use_12_hour:
        raise SystemExit("Pass only one of --use-24-hour / --use-12-hour")
    if args.theme and args.theme_restore_default:
        raise SystemExit("Pass only one of --theme / --theme-restore-default")
    if args.picture and args.theme_restore_default:
        raise SystemExit("--picture requires --theme derived from the image")
    if args.picture and not args.theme:
        raise SystemExit("--picture requires --theme derived from the image")

    if not args.status and not mutation_requested(args):
        raise SystemExit("Nothing to do; pass --status and/or push flags (see --help)")

    alarm_time = parse_time(args.time) if args.time else None
    theme_obj = parse_theme(args)
    audio_path = resolve_media(args.audio, kind="Audio")
    picture_path = resolve_media(args.picture, kind="Picture")

    students = load_students(Path(args.students_file))
    selected = configured_students(students, student)
    results = [
        push_one(
            slug,
            record,
            args,
            alarm_time=alarm_time,
            theme_obj=theme_obj,
            audio_path=audio_path,
            picture_path=picture_path,
        )
        for slug, record in selected
    ]

    print(json.dumps({"results": results}, indent=2))
    return 0 if all(result.get("ok") for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
