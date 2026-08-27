#!/usr/bin/env python3
"""Resolve one configured curriculum entrypoint for a student.

Curriculum paths in ``students.yaml`` point to files. This helper owns identity
selection and safe entrypoint resolution. ``curriculum_read.py`` owns native
component inspection, search, and bounded reads.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from curriculum_common import read_markdown
from hsd_common import load_registry, resolve_student


def normalize(value: Any) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _derived_id(configured_path: str) -> str:
    path = Path(configured_path)
    if path.stem.casefold() in {"curriculum", "index"} and path.parent.name:
        return path.parent.name
    return path.stem


def _entrypoint_path(
    registry_dir: Path,
    curricula_dir: Any,
    configured_path: str,
) -> tuple[Path, Path]:
    if not curricula_dir:
        raise SystemExit("student has curricula but no curricula_dir")

    base = Path(str(curricula_dir)).expanduser()
    if not base.is_absolute():
        base = registry_dir / base
    base = base.resolve()

    relative = Path(configured_path)
    if relative.is_absolute():
        resolved = relative.expanduser().resolve()
    else:
        resolved = (base / relative).resolve()
    if not resolved.is_relative_to(base):
        raise SystemExit(
            f"curriculum path escapes curricula_dir: {configured_path}"
        )
    return base, resolved


def curriculum_entries(
    student: dict[str, Any], registry_dir: Path
) -> list[dict[str, Any]]:
    configured = student.get("curricula") or {}
    if not isinstance(configured, dict):
        raise SystemExit("student curricula must be a mapping")

    entries: list[dict[str, Any]] = []
    for raw_path, raw_metadata in configured.items():
        configured_path = str(raw_path)
        configured_metadata = raw_metadata or {}
        if not isinstance(configured_metadata, dict):
            raise SystemExit(
                f"curriculum metadata must be a mapping: {configured_path}"
            )
        base, path = _entrypoint_path(
            registry_dir, student.get("curricula_dir"), configured_path
        )
        index_metadata: dict[str, Any] = {}
        if path.is_file() and path.suffix.casefold() == ".md":
            index_metadata, _ = read_markdown(path)
        metadata = {**index_metadata, **configured_metadata}
        index_aliases = index_metadata.get("aliases") or []
        configured_aliases = configured_metadata.get("aliases") or []
        if not isinstance(index_aliases, list) or not isinstance(configured_aliases, list):
            raise SystemExit(
                f"curriculum aliases must be a list: {configured_path}"
            )
        aliases = [
            *index_aliases,
            *configured_aliases,
        ]
        if aliases:
            metadata["aliases"] = list(dict.fromkeys(str(alias) for alias in aliases))
        curriculum_id = str(
            metadata.get("id")
            or metadata.get("curriculum_slug")
            or _derived_id(configured_path)
        )
        raw_aliases = metadata.get("aliases") or []
        aliases = [str(alias) for alias in raw_aliases]
        entries.append(
            {
                "id": curriculum_id,
                "aliases": aliases,
                "subject": metadata.get("subject"),
                "configured_path": configured_path,
                "curricula_dir": str(base),
                "path": str(path),
                "exists": path.is_file(),
                "metadata": metadata,
                "index_metadata": index_metadata,
                "configured_metadata": configured_metadata,
            }
        )
    return entries


def _identity_tokens(entry: dict[str, Any]) -> set[str]:
    configured = Path(entry["configured_path"])
    return {
        normalize(entry["id"]),
        *(normalize(alias) for alias in entry["aliases"]),
        normalize(entry["configured_path"]),
        normalize(configured.name),
        normalize(configured.stem),
        normalize(configured.parent.name),
    }


def resolve_curriculum(
    student: dict[str, Any],
    registry_dir: Path,
    *,
    curriculum: str | None = None,
    subject: str | None = None,
    require_existing: bool = False,
) -> dict[str, Any]:
    if (curriculum is None) == (subject is None):
        raise ValueError("provide exactly one of curriculum or subject")

    entries = curriculum_entries(student, registry_dir)
    if curriculum is not None:
        needle = normalize(curriculum)
        matches = [entry for entry in entries if needle in _identity_tokens(entry)]
        description = f"curriculum {curriculum!r}"
    else:
        needle = normalize(subject)
        matches = [
            entry for entry in entries if normalize(entry.get("subject")) == needle
        ]
        description = f"subject {subject!r}"

    if not matches:
        raise SystemExit(f"no configured curriculum matched {description}")
    if len(matches) > 1:
        choices = ", ".join(
            f"{entry['id']} ({entry['configured_path']})" for entry in matches
        )
        raise SystemExit(f"ambiguous {description}; matches: {choices}")

    selected = matches[0]
    if require_existing and not selected["exists"]:
        raise SystemExit(f"curriculum entrypoint not found: {selected['path']}")
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--student", required=True)
    parser.add_argument("--registry", default="students.yaml", type=Path)
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--curriculum", help="Curriculum id, alias, or configured path")
    selector.add_argument("--subject", help="Resolve only when the subject match is unique")
    parser.add_argument("--require-existing", action="store_true")
    args = parser.parse_args()

    registry = load_registry(args.registry)
    slug, student = resolve_student(registry.get("students", {}), args.student)
    selected = resolve_curriculum(
        student,
        args.registry.resolve().parent,
        curriculum=args.curriculum,
        subject=args.subject,
        require_existing=args.require_existing,
    )
    print(
        json.dumps(
            {"student": slug, "curriculum": selected},
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
