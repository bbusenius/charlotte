#!/usr/bin/env python3
"""Shared parsing and path-safety helpers for curriculum entrypoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import yaml


SUPPORTED_SOURCE_SUFFIXES = {".md", ".pdf", ".txt"}


def read_markdown(path: Path) -> tuple[dict[str, Any], str]:
    """Return YAML frontmatter and body from a Markdown file."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return {}, text
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            metadata = yaml.safe_load("".join(lines[1:index])) or {}
            if not isinstance(metadata, dict):
                raise SystemExit(f"frontmatter must be a mapping: {path}")
            return metadata, "".join(lines[index + 1 :])
    return {}, text


def safe_resolve(base: Path, value: str | Path, *, label: str) -> Path:
    """Resolve *value* beneath *base*, rejecting path traversal."""
    base = base.expanduser().resolve()
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = base / candidate
    candidate = candidate.resolve()
    if not candidate.is_relative_to(base):
        raise SystemExit(f"{label} escapes curricula_dir: {value}")
    return candidate


def resolve_link(root: Path, anchor: Path, value: str | Path, *, label: str) -> Path:
    """Resolve a link relative to *anchor* while confining it beneath *root*."""
    root = root.expanduser().resolve()
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = anchor / candidate
    candidate = candidate.resolve()
    if not candidate.is_relative_to(root):
        raise SystemExit(f"{label} escapes curricula_dir: {value}")
    return candidate


def markdown_link_target(raw_target: str) -> str | None:
    """Return a decoded local Markdown-link target, excluding URLs/anchors."""
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1].strip()
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    return unquote(parsed.path)


def display_path(path: Path, registry_dir: Path) -> str:
    """Prefer a stable registry-relative path for logs and JSON output."""
    resolved = path.resolve()
    registry_dir = registry_dir.resolve()
    if resolved.is_relative_to(registry_dir):
        return resolved.relative_to(registry_dir).as_posix()
    return str(resolved)
