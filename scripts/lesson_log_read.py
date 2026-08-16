#!/usr/bin/env python3
"""Query lesson logs without pulling whole sessions into context.

A session's log, its page transcriptions, and the parent's original messages
add up to a lot of text. A week of five subjects would swamp a conversation, so
every subcommand here returns frontmatter plus bounded excerpts, and the caller
asks for more only when it needs more.

Searches span every grade directory: what a child covered two grades ago is a
legitimate answer to "has she done this before?"

Subcommands:

    list    session summaries, newest first
    search  sessions whose text matches, with the matching snippets
    show    named sections of one session

All output is JSON on stdout.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date as date_cls
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hsd_common import load_registry, parse_date, resolve_student  # noqa: E402
from lesson_log_new import iter_session_dirs, read_frontmatter  # noqa: E402

DEFAULT_ROOT = Path("lesson-logs")
SEARCHABLE = ("log.md", "images.md", "messages.md")
SUMMARY_SECTION = "what we did"
SUMMARY_CHARS = 240
SNIPPET_CHARS = 200


def strip_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    parts = text.split("---", 2)
    return parts[2] if len(parts) >= 3 else text


def split_sections(text: str) -> dict[str, str]:
    """Map `## Heading` -> body text, for one markdown file."""
    sections: dict[str, str] = {}
    heading = None
    buffer: list[str] = []
    for line in strip_frontmatter(text).splitlines():
        match = re.match(r"^##\s+(.*\S)\s*$", line)
        if match:
            if heading is not None:
                sections[heading] = "\n".join(buffer).strip()
            heading = match.group(1)
            buffer = []
        elif heading is not None:
            buffer.append(line)
    if heading is not None:
        sections[heading] = "\n".join(buffer).strip()
    return sections


def condense(text: str, limit: int) -> str:
    collapsed = re.sub(r"\s+", " ", text).strip()
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[:limit].rsplit(" ", 1)[0] + "…"


def summarize(
    session: Path, frontmatter: dict[str, Any], include: list[str] | None = None
) -> dict[str, Any]:
    """Frontmatter plus a short excerpt — enough to answer most questions.

    `include` names extra sections to fold in, each condensed to the same
    bound. A caller that needs the observations for a whole week can ask for
    them here instead of running `show` once per session.
    """
    log_path = session / "log.md"
    summary = ""
    extra: dict[str, str] = {}
    if log_path.is_file():
        sections = split_sections(log_path.read_text(encoding="utf-8"))
        for heading, body in sections.items():
            if heading.strip().lower() == SUMMARY_SECTION:
                summary = condense(body, SUMMARY_CHARS)
            for request in include or []:
                if request.strip().lower() in heading.strip().lower():
                    extra[heading] = condense(body, SUMMARY_CHARS)
    lesson = frontmatter.get("lesson") or {}
    return {
        "path": str(session),
        "date": frontmatter.get("date"),
        "subject": frontmatter.get("subject"),
        "curriculum": lesson.get("curriculum"),
        "lesson_number": lesson.get("number"),
        "lesson_title": lesson.get("title"),
        "source": lesson.get("source"),
        # The real pages in the real book — what "what page are we on?" means.
        "pages": lesson.get("pages"),
        "teacher": frontmatter.get("teacher"),
        "start_time": frontmatter.get("start_time"),
        "end_time": frontmatter.get("end_time"),
        "concepts": frontmatter.get("concepts") or [],
        "summary": summary,
        **({"sections": extra} if extra else {}),
    }


def iter_sessions(root: Path, student_slug: str):
    """Every session for a student, across every grade directory."""
    student_root = root / student_slug
    if not student_root.is_dir():
        return
    for grade_dir in sorted(student_root.iterdir()):
        if not grade_dir.is_dir():
            continue
        for session in iter_session_dirs(grade_dir):
            frontmatter = read_frontmatter(session / "log.md")
            if frontmatter:
                yield session, frontmatter


def collect(
    root: Path,
    student_slug: str,
    subject: str | None,
    date_from: date_cls | None,
    date_to: date_cls | None,
) -> list[tuple[Path, dict[str, Any], date_cls | None]]:
    found = []
    for session, frontmatter in iter_sessions(root, student_slug):
        on_date = parse_date(frontmatter.get("date"))
        if date_from and (on_date is None or on_date < date_from):
            continue
        if date_to and (on_date is None or on_date > date_to):
            continue
        if subject and str(frontmatter.get("subject", "")).lower() != subject.lower():
            continue
        found.append((session, frontmatter, on_date))
    found.sort(key=lambda item: (item[2] or date_cls.min, item[0].name), reverse=True)
    return found


def resolve(args: argparse.Namespace) -> str:
    registry = load_registry(Path(args.registry))
    slug, _ = resolve_student(registry.get("students", {}), args.student)
    return slug


def cmd_list(args: argparse.Namespace) -> dict[str, Any]:
    slug = resolve(args)
    matches = collect(
        Path(args.root),
        slug,
        args.subject,
        parse_date(args.date_from) if args.date_from else None,
        parse_date(args.date_to) if args.date_to else None,
    )
    limit = args.latest or args.limit
    return {
        "student": slug,
        "subject": args.subject,
        "count": len(matches),
        "returned": min(len(matches), limit),
        "sessions": [
            summarize(s, f, args.include_section) for s, f, _ in matches[:limit]
        ],
    }


def snippets_for(path: Path, pattern: re.Pattern[str], cap: int) -> list[str]:
    if not path.is_file():
        return []
    text = strip_frontmatter(path.read_text(encoding="utf-8"))
    found = []
    for match in pattern.finditer(text):
        start = max(0, match.start() - SNIPPET_CHARS // 2)
        found.append(condense(text[start : match.end() + SNIPPET_CHARS // 2], SNIPPET_CHARS))
        if len(found) >= cap:
            break
    return found


def cmd_search(args: argparse.Namespace) -> dict[str, Any]:
    slug = resolve(args)
    pattern = re.compile(re.escape(args.query), re.IGNORECASE)
    matches = collect(
        Path(args.root),
        slug,
        args.subject,
        parse_date(args.date_from) if args.date_from else None,
        parse_date(args.date_to) if args.date_to else None,
    )

    hits = []
    for session, frontmatter, _ in matches:
        per_file = {}
        for name in SEARCHABLE:
            found = snippets_for(session / name, pattern, args.snippets)
            if found:
                per_file[name] = found
        if per_file:
            hits.append({**summarize(session, frontmatter), "matches": per_file})
        if len(hits) >= args.limit:
            break

    return {"student": slug, "query": args.query, "count": len(hits), "sessions": hits}


def cmd_show(args: argparse.Namespace) -> dict[str, Any]:
    session = Path(args.session)
    target = session / args.file
    if not target.is_file():
        raise SystemExit(f"no {args.file} in {session}")

    text = target.read_text(encoding="utf-8")
    sections = split_sections(text)
    result: dict[str, Any] = {
        "session": str(session),
        "file": args.file,
        "frontmatter": read_frontmatter(session / "log.md"),
        "available_sections": list(sections),
    }

    if args.full:
        result["content"] = strip_frontmatter(text).strip()
        return result

    if args.section:
        wanted = {}
        for request in args.section:
            needle = request.strip().lower()
            for heading, body in sections.items():
                if needle in heading.strip().lower():
                    wanted[heading] = body
        result["sections"] = wanted
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--registry", default="students.yaml")
    sub = parser.add_subparsers(dest="command", required=True)

    lister = sub.add_parser("list", help="session summaries, newest first")
    lister.add_argument("--student", required=True)
    lister.add_argument("--subject")
    lister.add_argument("--from", dest="date_from", help="YYYY-MM-DD")
    lister.add_argument("--to", dest="date_to", help="YYYY-MM-DD")
    lister.add_argument("--latest", type=int, help="only the N most recent")
    lister.add_argument("--limit", type=int, default=20)
    lister.add_argument(
        "--include-section",
        action="append",
        help="also return this section, condensed; repeatable, partial match",
    )
    lister.set_defaults(func=cmd_list)

    searcher = sub.add_parser("search", help="sessions whose text matches")
    searcher.add_argument("--student", required=True)
    searcher.add_argument("--query", required=True)
    searcher.add_argument("--subject")
    searcher.add_argument("--from", dest="date_from", help="YYYY-MM-DD")
    searcher.add_argument("--to", dest="date_to", help="YYYY-MM-DD")
    searcher.add_argument("--limit", type=int, default=10, help="max sessions")
    searcher.add_argument("--snippets", type=int, default=3, help="max snippets per file")
    searcher.set_defaults(func=cmd_search)

    shower = sub.add_parser("show", help="named sections of one session")
    shower.add_argument("--session", required=True)
    shower.add_argument("--file", default="log.md", choices=list(SEARCHABLE))
    shower.add_argument("--section", action="append", help="repeatable; partial match")
    shower.add_argument("--full", action="store_true", help="whole file; prefer --section")
    shower.set_defaults(func=cmd_show)

    args = parser.parse_args()
    print(json.dumps(args.func(args), indent=2))


if __name__ == "__main__":
    main()
