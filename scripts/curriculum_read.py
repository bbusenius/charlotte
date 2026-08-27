#!/usr/bin/env python3
"""Inspect, search, and read configured curriculum source files.

Curriculum entrypoints are concrete files configured in ``students.yaml``.
Markdown entrypoints may link to Markdown, text, or PDF components. PDF text is
extracted in memory for each invocation; nothing is converted or cached.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from curriculum_common import (
    SUPPORTED_SOURCE_SUFFIXES,
    display_path,
    markdown_link_target,
    read_markdown,
    resolve_link,
    safe_resolve,
)
from curriculum_resolve import resolve_curriculum
from hsd_common import load_registry, resolve_student


MARKDOWN_LINK = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass(frozen=True)
class Component:
    path: Path
    role: str
    title: str | None = None


def normalize_search(value: str) -> str:
    """Normalize Unicode, case, and whitespace without changing source text."""
    value = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(value.split())


def spaced_query_patterns(query: str) -> list[re.Pattern[str]]:
    """Match ordinary headings plus PDF headings split across lines."""
    tokens = re.findall(r"[^\W_]+", normalize_search(query), flags=re.UNICODE)
    parts: list[str] = []
    for token in tokens:
        if token.isalpha() and len(token) >= 3:
            parts.append(r"\s{0,3}".join(re.escape(character) for character in token))
        else:
            parts.append(re.escape(token))
    patterns = [
        re.compile(r"(?<!\w)" + r"[ \t]{1,4}".join(parts) + r"(?!\w)")
    ]
    if len(parts) == 2 and tokens[-1].isdigit():
        patterns.append(
            re.compile(
                r"(?m)^[ \t]{0,50}"
                + parts[0]
                + r"[ \t]*\r?\n[ \t]{0,50}"
                + parts[1]
                + r"(?!\d)"
            )
        )
    return patterns


def query_variants(kind: str, value: str) -> list[str]:
    if kind == "lesson":
        return [f"Lesson {value}", f"Lección {value}", f"Leccion {value}"]
    if kind == "unit":
        return [f"Unit {value}"]
    if kind == "chapter":
        return [f"Chapter {value}"]
    return [value]


def text_matches(text: str, queries: Iterable[str]) -> bool:
    searchable = unicodedata.normalize("NFKC", text).casefold()
    for query in queries:
        if any(pattern.search(searchable) for pattern in spaced_query_patterns(query)):
            return True
    return False


def match_score(text: str, queries: Iterable[str]) -> int:
    """Prefer likely section pages over tables of contents and references."""
    normalized = normalize_search(text)
    score = 0
    if any(text_matches(text[:500], [query]) for query in queries):
        score += 4
    if any(text_matches(text[:1200], [query]) for query in queries):
        score += 3
    lesson_mentions = len(re.findall(r"\blesson\s*\d+", normalized))
    if lesson_mentions <= 3:
        score += 2
    else:
        score -= 2
    if "table of contents" in normalized[:1200] or normalized.startswith("contents "):
        score -= 3
    return score


def _component_from_mapping(curricula_dir: Path, index_dir: Path, raw: Any) -> Component:
    if isinstance(raw, str):
        raw = {"path": raw}
    if not isinstance(raw, dict) or not raw.get("path"):
        raise SystemExit("each curriculum component must have a path")
    path = resolve_link(
        curricula_dir, index_dir, str(raw["path"]), label="component path"
    )
    return Component(
        path=path,
        role=str(raw.get("role") or "source"),
        title=str(raw["title"]) if raw.get("title") else None,
    )


def index_components(entrypoint: Path, curricula_dir: Path) -> tuple[dict[str, Any], list[Component]]:
    """Read an entrypoint and return its metadata and local source links."""
    if entrypoint.suffix.casefold() != ".md":
        return {}, [Component(entrypoint, "primary-lessons", entrypoint.stem)]

    metadata, body = read_markdown(entrypoint)
    components: list[Component] = []
    raw_components = metadata.get("components") or []
    if not isinstance(raw_components, list):
        raise SystemExit(f"components must be a list: {entrypoint}")
    for raw in raw_components:
        component = _component_from_mapping(curricula_dir, entrypoint.parent, raw)
        components.append(component)

    known = {component.path for component in components}
    for match in MARKDOWN_LINK.finditer(body):
        target = markdown_link_target(match.group(2))
        if target is None:
            continue
        candidate = (entrypoint.parent / target).resolve()
        if not candidate.is_relative_to(curricula_dir.resolve()):
            # Generated curricula also link to pedagogy and field-trip files;
            # those are navigation, not curriculum source components.
            continue
        path = candidate
        if path in known:
            continue
        components.append(Component(path, "linked-source", match.group(1).strip()))
        known.add(path)

    if not components:
        # This keeps a direct Markdown entrypoint readable while registered
        # curricula are migrated to explicit index files.
        components.append(Component(entrypoint, "primary-lessons", entrypoint.stem))
    return metadata, components


def component_record(component: Component, registry_dir: Path) -> dict[str, Any]:
    suffix = component.path.suffix.casefold()
    return {
        "path": display_path(component.path, registry_dir),
        "role": component.role,
        "title": component.title,
        "format": suffix.removeprefix(".") or None,
        "exists": component.path.is_file(),
        "supported": suffix in SUPPORTED_SOURCE_SUFFIXES,
    }


def require_command(name: str) -> None:
    if shutil.which(name) is None:
        raise SystemExit(f"required PDF command not found: {name}")


def extract_pdf_pages(path: Path, first: int | None = None, last: int | None = None) -> list[str]:
    """Extract PDF pages in memory, preserving form-feed page boundaries."""
    require_command("pdftotext")
    command = ["pdftotext", "-layout"]
    if first is not None:
        command.extend(["-f", str(first)])
    if last is not None:
        command.extend(["-l", str(last)])
    command.extend([str(path), "-"])
    result = subprocess.run(command, check=False, capture_output=True)
    if result.returncode:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise SystemExit(f"could not extract PDF text from {path}: {error}")
    text = result.stdout.decode("utf-8", errors="replace")
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    return pages


def render_pdf_pages(path: Path, first: int, last: int, output_dir: Path) -> list[str]:
    """Render selected PDF pages to PNG files in an explicit scratch directory."""
    require_command("pdftoppm")
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = output_dir / "page"
    command = [
        "pdftoppm", "-png", "-r", "144", "-f", str(first), "-l", str(last),
        str(path), str(prefix),
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode:
        raise SystemExit(f"could not render PDF pages from {path}: {result.stderr.strip()}")
    return [str(path.resolve()) for path in sorted(output_dir.glob("page-*.png"))]


def _markdown_section(lines: list[str], match_index: int) -> tuple[int, int]:
    heading_index: int | None = None
    heading_level: int | None = None
    for index in range(match_index, -1, -1):
        match = HEADING.match(lines[index])
        if match:
            heading_index = index
            heading_level = len(match.group(1))
            break
    if heading_index is None or heading_level is None:
        return max(0, match_index - 30), min(len(lines), match_index + 31)
    end = len(lines)
    for index in range(heading_index + 1, len(lines)):
        match = HEADING.match(lines[index])
        if match and len(match.group(1)) <= heading_level:
            end = index
            break
    return heading_index, end


def search_text(component: Component, queries: list[str], registry_dir: Path) -> list[dict[str, Any]]:
    text = component.path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    matched = [index for index, line in enumerate(lines) if text_matches(line, queries)]
    results: list[dict[str, Any]] = []
    seen_ranges: set[tuple[int, int]] = set()
    for match_index in matched:
        if component.path.suffix.casefold() == ".md":
            start, end = _markdown_section(lines, match_index)
        else:
            start, end = max(0, match_index - 30), min(len(lines), match_index + 31)
        if (start, end) in seen_ranges:
            continue
        seen_ranges.add((start, end))
        results.append(
            {
                "source": display_path(component.path, registry_dir),
                "role": component.role,
                "lines": [start + 1, end],
                "matched_lines": [index + 1 for index in matched if start <= index < end],
                "text": "\n".join(lines[start:end]),
            }
        )
    return results


def search_pdf(
    component: Component,
    queries: list[str],
    registry_dir: Path,
    *,
    context_pages: int,
    max_results: int,
) -> list[dict[str, Any]]:
    pages = extract_pdf_pages(component.path)
    hits = [index for index, page in enumerate(pages) if text_matches(page, queries)]
    hits.sort(key=lambda index: (-match_score(pages[index], queries), index))
    results: list[dict[str, Any]] = []
    seen_ranges: set[tuple[int, int]] = set()
    for index in hits:
        first = max(1, index + 1 - context_pages)
        last = min(len(pages), index + 1 + context_pages)
        if (first, last) in seen_ranges:
            continue
        seen_ranges.add((first, last))
        results.append(
            {
                "source": display_path(component.path, registry_dir),
                "role": component.role,
                "pdf_pages": [first, last],
                "matched_pdf_pages": [
                    hit + 1 for hit in hits if first <= hit + 1 <= last
                ],
                "text": "\n\f\n".join(pages[first - 1 : last]),
            }
        )
        if len(results) >= max_results:
            break
    return results


def search_components(
    components: list[Component],
    queries: list[str],
    registry_dir: Path,
    *,
    role: str | None = None,
    context_pages: int = 1,
    max_results: int = 12,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for component in components:
        if role and component.role.casefold() != role.casefold():
            continue
        if not component.path.is_file() or component.path.suffix.casefold() not in SUPPORTED_SOURCE_SUFFIXES:
            continue
        if component.path.suffix.casefold() == ".pdf":
            matches = search_pdf(
                component,
                queries,
                registry_dir,
                context_pages=context_pages,
                max_results=max_results - len(results),
            )
        else:
            matches = search_text(component, queries, registry_dir)
        results.extend(matches[: max_results - len(results)])
        if len(results) >= max_results:
            break
    return results


def _student_context(registry_path: Path, student_query: str) -> tuple[Path, dict[str, Any], str, Path]:
    registry_path = registry_path.expanduser().resolve()
    registry = load_registry(registry_path)
    student_slug, student = resolve_student(registry.get("students", {}), student_query)
    configured_root = student.get("curricula_dir")
    if not configured_root:
        raise SystemExit("student has no curricula_dir")
    raw_root = Path(str(configured_root))
    curricula_dir = raw_root.expanduser()
    if not curricula_dir.is_absolute():
        curricula_dir = registry_path.parent / curricula_dir
    return registry_path.parent, student, student_slug, curricula_dir.resolve()


def _resolve_entrypoint(
    registry_path: Path,
    student_query: str,
    curriculum: str | None,
    subject: str | None,
) -> tuple[Path, Path, dict[str, Any], str, Path]:
    registry_dir, student, student_slug, curricula_dir = _student_context(registry_path, student_query)
    entry = resolve_curriculum(
        student,
        registry_dir,
        curriculum=curriculum,
        subject=subject,
        require_existing=True,
    )
    return registry_dir, Path(entry["path"]), entry, student_slug, curricula_dir


def _source_path(curricula_dir: Path, registry_dir: Path, raw_source: str) -> Path:
    raw = Path(raw_source).expanduser()
    if raw.is_absolute():
        return safe_resolve(curricula_dir, raw, label="source path")
    registry_candidate = (registry_dir / raw).resolve()
    if registry_candidate.is_relative_to(curricula_dir.resolve()):
        return registry_candidate
    return safe_resolve(curricula_dir, raw, label="source path")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", default="students.yaml", type=Path)
    parser.add_argument("--student", required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_selector(command: argparse.ArgumentParser) -> None:
        selector = command.add_mutually_exclusive_group(required=True)
        selector.add_argument("--curriculum")
        selector.add_argument("--subject")

    inspect_parser = subparsers.add_parser("inspect", help="List an index and its components")
    add_selector(inspect_parser)

    search_parser = subparsers.add_parser("search", help="Search linked curriculum sources")
    add_selector(search_parser)
    query = search_parser.add_mutually_exclusive_group(required=True)
    query.add_argument("--lesson")
    query.add_argument("--unit")
    query.add_argument("--chapter")
    query.add_argument("--query")
    search_parser.add_argument("--role")
    search_parser.add_argument("--context-pages", type=int, default=1)
    search_parser.add_argument("--max-results", type=int, default=6)

    read_parser = subparsers.add_parser("read", help="Read one exact native source")
    read_parser.add_argument("--source", required=True)
    read_parser.add_argument("--pages", help="Inclusive PDF range, such as 19-20 or 19")
    text_location = read_parser.add_mutually_exclusive_group()
    text_location.add_argument("--lines", help="Inclusive text range, such as 40-90 or 40")
    text_location.add_argument("--section", help="Markdown heading or distinctive text")
    read_parser.add_argument("--render-dir", type=Path)

    args = parser.parse_args()
    registry_path = args.registry.expanduser().resolve()

    if args.command in {"inspect", "search"}:
        registry_dir, entrypoint, entry, student_slug, curricula_dir = _resolve_entrypoint(
            registry_path, args.student, args.curriculum, args.subject
        )
        index_metadata, components = index_components(entrypoint, curricula_dir)
        base = {
            "student": student_slug,
            "curriculum": entry["id"],
            "entrypoint": display_path(entrypoint, registry_dir),
            "index": index_metadata,
            "components": [component_record(component, registry_dir) for component in components],
        }
        if args.command == "inspect":
            base["valid"] = all(
                component["exists"] and component["supported"] for component in base["components"]
            )
            print(json.dumps(base, indent=2, ensure_ascii=False))
            return 0

        kind = next(name for name in ("lesson", "unit", "chapter", "query") if getattr(args, name) is not None)
        value = str(getattr(args, kind))
        queries = query_variants(kind, value)
        result = {
            "student": student_slug,
            "curriculum": entry["id"],
            "entrypoint": display_path(entrypoint, registry_dir),
            "request": {"kind": kind, "value": value, "queries": queries},
        }
        result["matches"] = search_components(
            components,
            queries,
            registry_dir,
            role=args.role,
            context_pages=max(0, args.context_pages),
            max_results=max(1, args.max_results),
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    registry_dir, _, student_slug, curricula_dir = _student_context(registry_path, args.student)
    source = _source_path(curricula_dir, registry_dir, args.source)
    if not source.is_file():
        raise SystemExit(f"curriculum source not found: {source}")
    suffix = source.suffix.casefold()
    if suffix not in SUPPORTED_SOURCE_SUFFIXES:
        raise SystemExit(f"unsupported curriculum source: {source}")
    result: dict[str, Any] = {"student": student_slug, "source": display_path(source, registry_dir)}
    if suffix == ".pdf":
        if args.lines or args.section:
            raise SystemExit("use --pages, not --lines/--section, when reading a PDF")
        if not args.pages:
            raise SystemExit("--pages is required when reading a PDF")
        first, last = parse_range(args.pages, "pages")
        if last - first + 1 > 40:
            raise SystemExit("refusing to read more than 40 PDF pages at once")
        result["pdf_pages"] = [first, last]
        result["text"] = "\n\f\n".join(extract_pdf_pages(source, first, last))
        if args.render_dir:
            result["images"] = render_pdf_pages(source, first, last, args.render_dir)
    else:
        if args.pages:
            raise SystemExit("use --lines/--section, not --pages, when reading text")
        lines = source.read_text(encoding="utf-8", errors="replace").splitlines()
        if args.section:
            matched = [
                index for index, line in enumerate(lines)
                if text_matches(line, [args.section])
            ]
            ranges = {
                _markdown_section(lines, index)
                if suffix == ".md"
                else (max(0, index - 30), min(len(lines), index + 31))
                for index in matched
            }
            if not ranges:
                raise SystemExit(f"section not found: {args.section}")
            if len(ranges) > 1:
                raise SystemExit(f"ambiguous section: {args.section}")
            start, end = ranges.pop()
            first, last = start + 1, end
            result["section"] = args.section
        elif args.lines:
            first, last = parse_range(args.lines, "lines")
            if last > len(lines):
                raise SystemExit(f"line range exceeds source length ({len(lines)} lines)")
        else:
            first, last = 1, len(lines)
        result["lines"] = [first, last]
        result["text"] = "\n".join(lines[first - 1 : last])
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def parse_range(value: str, label: str) -> tuple[int, int]:
    match = re.fullmatch(r"\s*(\d+)(?:\s*-\s*(\d+))?\s*", value)
    if not match:
        raise SystemExit(f"invalid {label} range: {value}")
    first = int(match.group(1))
    last = int(match.group(2) or first)
    if first < 1 or last < first:
        raise SystemExit(f"invalid {label} range: {value}")
    return first, last


if __name__ == "__main__":
    raise SystemExit(main())
