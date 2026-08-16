from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def load_module():
    repo = Path(__file__).resolve().parents[1]
    scripts = repo / "scripts"
    sys.path.insert(0, str(scripts))
    try:
        spec = importlib.util.spec_from_file_location(
            "curriculum_resolve", scripts / "curriculum_resolve.py"
        )
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(scripts))


def student() -> dict:
    return {
        "curricula_dir": "curricula",
        "curricula": {
            "third-party/math-3/Math-3.md": {
                "subject": "Math",
            },
            "art/ao-picture-study/curriculum.md": {
                "id": "ao-picture-study",
                "aliases": ["AO", "picture study"],
                "subject": "Art",
            },
            "art/oil-painting/curriculum.md": {
                "id": "oil-painting",
                "aliases": ["oils"],
                "subject": "Art",
            },
        },
    }


def test_resolves_by_id_alias_and_configured_path(tmp_path):
    mod = load_module()
    by_id = mod.resolve_curriculum(
        student(), tmp_path, curriculum="ao-picture-study"
    )
    by_alias = mod.resolve_curriculum(student(), tmp_path, curriculum="AO")
    by_path = mod.resolve_curriculum(
        student(),
        tmp_path,
        curriculum="art/ao-picture-study/curriculum.md",
    )

    assert by_id["path"] == by_alias["path"] == by_path["path"]
    assert by_id["id"] == "ao-picture-study"


def test_subject_resolves_only_when_unique(tmp_path):
    mod = load_module()
    selected = mod.resolve_curriculum(student(), tmp_path, subject="math")
    assert selected["id"] == "Math-3"

    with pytest.raises(SystemExit, match="ambiguous subject"):
        mod.resolve_curriculum(student(), tmp_path, subject="Art")


def test_legacy_entry_derives_an_identity(tmp_path):
    mod = load_module()
    selected = mod.resolve_curriculum(student(), tmp_path, curriculum="Math-3.md")
    assert selected["id"] == "Math-3"


def test_require_existing_and_safe_paths(tmp_path):
    mod = load_module()
    with pytest.raises(SystemExit, match="entrypoint not found"):
        mod.resolve_curriculum(
            student(), tmp_path, curriculum="AO", require_existing=True
        )

    unsafe = {
        "curricula_dir": "curricula",
        "curricula": {"../outside.md": {"subject": "Art"}},
    }
    with pytest.raises(SystemExit, match="escapes curricula_dir"):
        mod.curriculum_entries(unsafe, tmp_path)
