from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    scripts_dir = str(path.parent)
    sys.path.insert(0, scripts_dir)
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(scripts_dir)
    return module


next_study = load_module("ao_next_study", REPO_ROOT / "scripts" / "ao_next_study.py")


def write_picture(state_root: Path, committed_at: str | None = None) -> Path:
    cursor = {"artist": "Artist", "title": "A Painting"}
    if committed_at:
        cursor["committed_at"] = committed_at
    path = state_root / "ao-picture-study" / "student.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump({"schema": "ao-picture-study-state/v1", "student": "student", "last_created": cursor}),
        encoding="utf-8",
    )
    return path


def write_composer(state_root: Path, committed_at: str | None = None) -> Path:
    cursor = {"composer": "Composer", "title": "A Work"}
    if committed_at:
        cursor["committed_at"] = committed_at
    path = state_root / "ao-composer-study" / "student.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump({"schema": "ao-composer-study-state/v1", "student": "student", "last_presented": cursor}),
        encoding="utf-8",
    )
    return path


def test_no_cursors_starts_with_picture(tmp_path):
    assert next_study.decide(tmp_path, "student")["next"] == "picture"


def test_only_picture_then_composer(tmp_path):
    write_picture(tmp_path, "2026-11-03T07:00:00+00:00")
    assert next_study.decide(tmp_path, "student")["next"] == "composer"


def test_only_composer_then_picture(tmp_path):
    write_composer(tmp_path, "2026-11-10T07:00:00+00:00")
    assert next_study.decide(tmp_path, "student")["next"] == "picture"


def test_alternates_from_most_recent_commit(tmp_path):
    write_picture(tmp_path, "2026-11-03T07:00:00+00:00")
    write_composer(tmp_path, "2026-11-10T07:00:00+00:00")
    result = next_study.decide(tmp_path, "student")
    assert result["next"] == "picture"
    assert result["last_created"]["kind"] == "composer"

    write_picture(tmp_path, "2026-11-24T07:00:00+00:00")
    assert next_study.decide(tmp_path, "student")["next"] == "composer"


def test_missed_weeks_do_not_skip_a_study(tmp_path):
    # Weeks of downtime between commits must not change whose turn it is.
    write_picture(tmp_path, "2026-09-01T07:00:00+00:00")
    write_composer(tmp_path, "2026-09-08T07:00:00+00:00")
    assert next_study.decide(tmp_path, "student")["next"] == "picture"


def test_legacy_cursors_fall_back_to_file_mtime(tmp_path):
    picture = write_picture(tmp_path)
    composer = write_composer(tmp_path)
    os.utime(picture, (1_000_000, 1_000_000))
    os.utime(composer, (2_000_000, 2_000_000))
    result = next_study.decide(tmp_path, "student")
    assert result["next"] == "picture"
    assert result["last_created"]["committed_at_source"] == "file_mtime"


def test_committed_at_wins_over_mtime(tmp_path):
    picture = write_picture(tmp_path, "2026-11-24T07:00:00+00:00")
    composer = write_composer(tmp_path, "2026-11-10T07:00:00+00:00")
    os.utime(picture, (1_000_000, 1_000_000))
    os.utime(composer, (2_000_000, 2_000_000))
    assert next_study.decide(tmp_path, "student")["next"] == "composer"
