from __future__ import annotations

import importlib.util
import json
import re
import sys
from datetime import date
from pathlib import Path

import yaml


def load_rotation_module():
    module_path = (
        Path(__file__).resolve().parents[1]
        / "skills"
        / "ao-picture-study"
        / "scripts"
        / "rotation.py"
    )
    spec = importlib.util.spec_from_file_location("ao_picture_rotation", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SAMPLE_HTML = """
<html><body>
<p id="artist-a"><strong>2026-2027 TERM 1</strong> Artist A (1900-1980; Painter)</p>
<p>
1. <a href="https://commons.wikimedia.org/wiki/File:First.jpg">First Work</a>, 1943, Museum<br>
2. <a href="/relative-second">Second Work</a>, c. 1950, Museum or
   <a href="https://example.test/alternate">Alternate Work</a><br>
</p>
<p id="artist-b"><strong>2026-2027 TERM 2</strong> Artist B (1870-1930)</p>
<p>
1. <a href="https://example.test/third">Third Work</a>, before 1910, Museum<br>
2. <a href="https://example.test/fourth">Fourth Work</a>, 1912-1914, Museum<br>
</p>
</body></html>
"""


def test_skill_requires_harness_agnostic_pixel_inspection():
    skill_path = (
        Path(__file__).resolve().parents[1]
        / "skills"
        / "ao-picture-study"
        / "SKILL.md"
    )
    skill = skill_path.read_text(encoding="utf-8")

    assert "default image-understanding capability" in skill
    assert "genuine pixel-level inspection" in skill
    assert "not to direct the child's gaze" in skill
    assert "guided visual inventory" in skill
    assert "subject, iconography, artistic aims, and well-grounded interpretations" in skill
    assert "the child's required conclusion" in skill
    assert "vision_analyze" not in skill
    for harness_detail in ("Gemini", "Grok", "Hermes", "Codex"):
        assert re.search(rf"\b{harness_detail}\b", skill) is None


def test_parser_extracts_primary_numbered_works_and_dates():
    rotation = load_rotation_module()
    schedules = rotation.parse_rotation(SAMPLE_HTML, "https://amblesideonline.org/artists")

    assert len(schedules) == 2
    first = schedules[0]
    assert first["school_year"] == "2026-2027"
    assert first["term"] == 1
    assert first["artist"] == "Artist A"
    assert first["artist_details"] == "1900-1980; Painter"
    assert [work["title"] for work in first["works"]] == ["First Work", "Second Work"]
    assert first["works"][0]["date"] == "1943"
    assert first["works"][1]["date"] == "c. 1950"
    assert first["works"][1]["ao_url"] == "https://amblesideonline.org/relative-second"


def test_next_uses_upcoming_term_then_advances_by_last_created(tmp_path):
    rotation = load_rotation_module()
    schedules = rotation.parse_rotation(SAMPLE_HTML)

    first = rotation.resolve_next(schedules, None, date(2026, 8, 15))
    assert first["title"] == "First Work"
    assert first["introduce_artist"] is True

    cursor_path = tmp_path / "student.yaml"
    rotation.commit_cursor(cursor_path, "student", first, first["suggested_slide_id"])
    cursor = rotation.load_cursor(cursor_path)
    second = rotation.resolve_next(schedules, cursor, date(2026, 8, 15))
    assert second["title"] == "Second Work"
    assert second["introduce_artist"] is False

    rotation.commit_cursor(cursor_path, "student", second, second["suggested_slide_id"])
    cursor = rotation.load_cursor(cursor_path)
    third = rotation.resolve_next(schedules, cursor, date(2026, 8, 15))
    assert third["title"] == "Third Work"
    assert third["term"] == 2
    assert third["introduce_artist"] is True


def test_explicit_start_can_begin_midterm_and_still_introduce_artist():
    rotation = load_rotation_module()
    schedules = rotation.parse_rotation(SAMPLE_HTML)
    target = rotation.resolve_next(
        schedules,
        None,
        date(2026, 10, 1),
        ("2026-2027", 1, 2),
    )
    assert target["title"] == "Second Work"
    assert target["introduce_artist"] is True


def test_new_term_reintroduces_even_if_artist_name_repeats():
    rotation = load_rotation_module()
    schedules = rotation.parse_rotation(SAMPLE_HTML)
    schedules[1]["artist"] = schedules[0]["artist"]
    cursor = {
        "school_year": "2026-2027",
        "term": 1,
        "picture_number": 2,
        "artist": "Artist A",
    }

    target = rotation.resolve_next(schedules, cursor, date(2026, 12, 1))

    assert target["term"] == 2
    assert target["introduce_artist"] is True


def test_next_cli_resolves_curriculum_and_exact_study_path(
    tmp_path, monkeypatch, capsys
):
    rotation = load_rotation_module()
    registry = tmp_path / "students.yaml"
    registry.write_text(
        yaml.safe_dump(
            {
                "students": {
                    "student": {
                        "display_name": "Student",
                        "grade": 3,
                        "aliases": ["student"],
                        "curricula_dir": "curricula",
                        "curricula": {
                            "art/ao-picture-study/curriculum.md": {
                                "id": "ao-picture-study",
                                "aliases": ["AO"],
                                "subject": "Art",
                            }
                        },
                        "tablet_slides_dir": "tablet-slides/student/active",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    html = tmp_path / "artists.html"
    html.write_text(SAMPLE_HTML, encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "rotation.py",
            "next",
            "--student",
            "student",
            "--students-file",
            str(registry),
            "--state-dir",
            str(tmp_path / "state"),
            "--html-file",
            str(html),
            "--today",
            "2026-08-15",
        ],
    )

    assert rotation.main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result["curriculum"]["id"] == "ao-picture-study"
    assert result["target"]["suggested_study_path"].endswith(
        "curricula/art/ao-picture-study/artists/artist-a/first-work.md"
    )
    assert result["state_path"] == str(tmp_path / "state" / "student.yaml")
    assert result["scratch_dir"].endswith(
        ".scratch/ao-picture-study/student/ao-2026-2027-t1-01-artist-a-first-work"
    )


def test_cleanup_cli_removes_only_the_committed_run(tmp_path, monkeypatch, capsys):
    rotation = load_rotation_module()
    registry = tmp_path / "students.yaml"
    registry.write_text(
        yaml.safe_dump(
            {
                "students": {
                    "student": {
                        "display_name": "Student",
                        "aliases": ["student"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    state_dir = tmp_path / "state"
    scratch_root = tmp_path / "scratch"
    slide_id = "ao-2026-2027-t1-01-artist-a-first-work"
    sibling_id = "ao-2026-2027-t1-02-artist-a-second-work"
    target = scratch_root / "student" / slide_id
    sibling = scratch_root / "student" / sibling_id
    target.mkdir(parents=True)
    sibling.mkdir()
    (target / "working.txt").write_text("remove me", encoding="utf-8")
    (sibling / "working.txt").write_text("keep me", encoding="utf-8")
    rotation.commit_cursor(
        state_dir / "student.yaml",
        "student",
        {
            "school_year": "2026-2027",
            "term": 1,
            "picture_number": 1,
            "artist": "Artist A",
            "title": "First Work",
            "date": "1943",
            "ao_url": "https://example.test/first",
        },
        slide_id,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "rotation.py",
            "cleanup",
            "--student",
            "student",
            "--students-file",
            str(registry),
            "--state-dir",
            str(state_dir),
            "--scratch-root",
            str(scratch_root),
            "--slide-id",
            slide_id,
        ],
    )

    assert rotation.main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result["removed"] is True
    assert not target.exists()
    assert sibling.is_dir()
    assert scratch_root.is_dir()


def test_cleanup_cli_refuses_an_uncommitted_run(tmp_path, monkeypatch):
    rotation = load_rotation_module()
    registry = tmp_path / "students.yaml"
    registry.write_text(
        yaml.safe_dump(
            {"students": {"student": {"display_name": "Student"}}}
        ),
        encoding="utf-8",
    )
    state_dir = tmp_path / "state"
    committed_id = "ao-2026-2027-t1-01-artist-a-first-work"
    requested_id = "ao-2026-2027-t1-02-artist-a-second-work"
    requested = tmp_path / "scratch" / "student" / requested_id
    requested.mkdir(parents=True)
    rotation.commit_cursor(
        state_dir / "student.yaml",
        "student",
        {
            "school_year": "2026-2027",
            "term": 1,
            "picture_number": 1,
            "artist": "Artist A",
            "title": "First Work",
            "date": "1943",
            "ao_url": "https://example.test/first",
        },
        committed_id,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "rotation.py",
            "cleanup",
            "--student",
            "student",
            "--students-file",
            str(registry),
            "--state-dir",
            str(state_dir),
            "--scratch-root",
            str(tmp_path / "scratch"),
            "--slide-id",
            requested_id,
        ],
    )

    try:
        rotation.main()
    except SystemExit as exc:
        assert "not the committed cursor" in str(exc)
    else:
        raise AssertionError("cleanup accepted an uncommitted AO run")
    assert requested.is_dir()
