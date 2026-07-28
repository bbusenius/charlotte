from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml


def load_module():
    repo = Path(__file__).resolve().parents[1]
    scripts_dir = repo / "scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        spec = importlib.util.spec_from_file_location(
            "lesson_log_new", scripts_dir / "lesson_log_new.py"
        )
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(scripts_dir))


def write_registry(tmp_path: Path) -> Path:
    registry = {
        "students": {
            "eliana": {
                "display_name": "Eliana",
                "grade": 3,
                "aliases": ["eliana"],
                "subjects": ["Language Arts & Literature", "Science"],
            },
            "isamaya": {
                "display_name": "Isamaya",
                "grade": "preschool",
                "aliases": ["isamaya", "sisi"],
                "subjects": ["Handwriting"],
            },
        }
    }
    path = tmp_path / "students.yaml"
    path.write_text(yaml.safe_dump(registry), encoding="utf-8")
    return path


def make_args(tmp_path: Path, **kwargs) -> argparse.Namespace:
    base = {
        "root": str(tmp_path / "lesson-logs"),
        "registry": str(write_registry(tmp_path)),
    }
    base.update(kwargs)
    return argparse.Namespace(**base)


def create_session(mod, tmp_path: Path, **kwargs) -> dict:
    args = make_args(
        tmp_path,
        student=kwargs.pop("student", "eliana"),
        date=kwargs.pop("date", "2026-07-24"),
        subject=kwargs.pop("subject", "Science"),
        slug=kwargs.pop("slug", "lesson-12-levers"),
        **kwargs,
    )
    return mod.cmd_create(args)


def test_slugify_and_grade_dir_names():
    mod = load_module()
    assert mod.slugify("Language Arts & Literature") == "language-arts-literature"
    assert mod.slugify("  Lesson 112: Guide Words  ") == "lesson-112-guide-words"
    assert mod.grade_dir_name(3) == "grade-3"
    assert mod.grade_dir_name("preschool") == "preschool"


def test_create_places_session_in_the_student_grade_and_day(tmp_path):
    mod = load_module()
    result = create_session(mod, tmp_path)

    assert result["created"] is True
    session = Path(result["path"])
    assert session.relative_to(tmp_path / "lesson-logs").parts == (
        "eliana",
        "grade-3",
        "2026",
        "07",
        "24",
        "science-lesson-12-levers",
    )
    assert (session / "sources").is_dir()


def test_create_writes_stub_frontmatter_so_find_works_before_synthesis(tmp_path):
    mod = load_module()
    result = create_session(mod, tmp_path)

    frontmatter = result["frontmatter"]
    assert frontmatter["schema"] == "lesson-log/v1"
    assert frontmatter["student"] == "eliana"
    assert frontmatter["grade"] == 3
    assert frontmatter["date"] == "2026-07-24"
    assert frontmatter["subject"] == "Science"
    # Times are absent until they are known; their absence is the pending set.
    assert "start_time" not in frontmatter
    assert result["has_times"] is False


def test_read_frontmatter_normalizes_an_unquoted_yaml_date_for_json(tmp_path):
    mod = load_module()
    log = tmp_path / "log.md"
    log.write_text(
        "---\n"
        "schema: lesson-log/v1\n"
        "student: eliana\n"
        "date: 2026-07-24\n"
        "subject: Science\n"
        "---\n",
        encoding="utf-8",
    )

    frontmatter = mod.read_frontmatter(log)
    assert frontmatter["date"] == "2026-07-24"
    json.dumps(frontmatter)


def test_session_needs_both_times_before_has_times_is_true(tmp_path):
    mod = load_module()
    result = create_session(mod, tmp_path)
    session = Path(result["path"])
    frontmatter = result["frontmatter"]
    frontmatter["start_time"] = "9:15 AM"
    body = yaml.safe_dump(frontmatter, sort_keys=False).strip()
    (session / "log.md").write_text(f"---\n{body}\n---\n", encoding="utf-8")

    assert mod.describe_session(session)["has_times"] is False

    frontmatter["end_time"] = "10:05 AM"
    body = yaml.safe_dump(frontmatter, sort_keys=False).strip()
    (session / "log.md").write_text(f"---\n{body}\n---\n", encoding="utf-8")
    assert mod.describe_session(session)["has_times"] is True


def test_create_is_idempotent_for_the_same_session(tmp_path):
    mod = load_module()
    first = create_session(mod, tmp_path)
    second = create_session(mod, tmp_path)

    assert second["created"] is False
    assert second["path"] == first["path"]


def test_two_sessions_in_one_subject_on_one_day(tmp_path):
    """Morning lesson and evening reading both log as Language Arts."""
    mod = load_module()
    morning = create_session(
        mod, tmp_path, subject="Language Arts & Literature", slug="lesson-112-guide-words"
    )
    evening = create_session(
        mod, tmp_path, subject="Language Arts & Literature", slug="charlottes-web-ch-8"
    )

    assert morning["created"] is True
    assert evening["created"] is True
    assert morning["path"] != evening["path"]
    assert evening["path"].endswith(
        "2026/07/24/language-arts-literature-charlottes-web-ch-8"
    )

    candidates = mod.find_sessions(
        Path(tmp_path / "lesson-logs"),
        "eliana",
        mod.parse_iso_date("2026-07-24"),
        "Language Arts & Literature",
    )
    assert len(candidates) == 2


def test_create_rejects_a_subject_the_student_does_not_have(tmp_path):
    mod = load_module()
    with pytest.raises(SystemExit) as excinfo:
        create_session(mod, tmp_path, subject="Astrophysics")
    assert "configured subjects" in str(excinfo.value)


def test_find_matches_on_student_date_and_subject(tmp_path):
    mod = load_module()
    create_session(mod, tmp_path)
    create_session(
        mod, tmp_path, subject="Language Arts & Literature", slug="lesson-112-guide-words"
    )

    args = make_args(tmp_path, student="eliana", date="2026-07-24", subject="Science")
    result = mod.cmd_find(args)

    assert result["count"] == 1
    assert result["sessions"][0]["subject"] == "Science"


def test_find_accepts_an_alias_and_returns_all_subjects_when_unfiltered(tmp_path):
    mod = load_module()
    create_session(mod, tmp_path)
    create_session(
        mod, tmp_path, subject="Language Arts & Literature", slug="lesson-112-guide-words"
    )

    args = make_args(tmp_path, student="eliana", date="2026-07-24", subject=None)
    assert mod.cmd_find(args)["count"] == 2


def test_find_searches_across_grade_directories(tmp_path):
    """A session written before a grade bump must still be findable."""
    mod = load_module()
    result = create_session(mod, tmp_path)
    session = Path(result["path"])

    moved = (
        tmp_path
        / "lesson-logs"
        / "eliana"
        / "grade-2"
        / "2026"
        / "07"
        / "24"
        / session.name
    )
    moved.parent.mkdir(parents=True)
    session.rename(moved)

    args = make_args(tmp_path, student="eliana", date="2026-07-24", subject="Science")
    assert mod.cmd_find(args)["count"] == 1


def test_find_returns_nothing_for_an_unused_date(tmp_path):
    mod = load_module()
    create_session(mod, tmp_path)

    args = make_args(tmp_path, student="eliana", date="2026-07-25", subject=None)
    assert mod.cmd_find(args)["count"] == 0


def test_add_numbers_files_by_role_and_preserves_extensions(tmp_path):
    mod = load_module()
    session = Path(create_session(mod, tmp_path)["path"])

    first = tmp_path / "a.JPG"
    first.write_bytes(b"page one")
    second = tmp_path / "b.jpg"
    second.write_bytes(b"page two")
    voice = tmp_path / "note.ogg"
    voice.write_bytes(b"spoken")

    pages = mod.cmd_add(
        argparse.Namespace(session=str(session), role="image", file=[str(first), str(second)])
    )
    voices = mod.cmd_add(
        argparse.Namespace(session=str(session), role="voice", file=[str(voice)])
    )

    assert [entry["name"] for entry in pages["added"]] == ["image-01.jpg", "image-02.jpg"]
    assert [entry["name"] for entry in voices["added"]] == ["voice-01.ogg"]


def test_add_continues_numbering_and_never_renumbers(tmp_path):
    """Photos arriving the next morning append; existing names never move."""
    mod = load_module()
    session = Path(create_session(mod, tmp_path)["path"])

    for index, payload in enumerate([b"one", b"two"], start=1):
        source = tmp_path / f"day1-{index}.jpg"
        source.write_bytes(payload)
        mod.cmd_add(
            argparse.Namespace(session=str(session), role="image", file=[str(source)])
        )

    late = tmp_path / "day2.jpg"
    late.write_bytes(b"three")
    result = mod.cmd_add(
        argparse.Namespace(session=str(session), role="image", file=[str(late)])
    )

    assert result["added"][0]["name"] == "image-03.jpg"
    assert (session / "sources" / "image-01.jpg").read_bytes() == b"one"


def test_add_dedupes_identical_content(tmp_path):
    mod = load_module()
    session = Path(create_session(mod, tmp_path)["path"])

    original = tmp_path / "page.jpg"
    original.write_bytes(b"same bytes")
    duplicate = tmp_path / "page-again.jpg"
    duplicate.write_bytes(b"same bytes")

    mod.cmd_add(
        argparse.Namespace(session=str(session), role="image", file=[str(original)])
    )
    second = mod.cmd_add(
        argparse.Namespace(session=str(session), role="image", file=[str(duplicate)])
    )

    assert second["added"][0] == {
        "source": str(duplicate),
        "name": "image-01.jpg",
        "deduped": True,
    }
    assert len(list((session / "sources").iterdir())) == 1


def test_add_leaves_the_original_in_place(tmp_path):
    """Sources are copied out of the inbox, never moved out of it."""
    mod = load_module()
    session = Path(create_session(mod, tmp_path)["path"])

    inbox_file = tmp_path / "attachment.jpg"
    inbox_file.write_bytes(b"payload")
    mod.cmd_add(
        argparse.Namespace(session=str(session), role="image", file=[str(inbox_file)])
    )

    assert inbox_file.is_file()
    assert (session / "sources" / "image-01.jpg").read_bytes() == b"payload"


def test_add_rejects_a_directory_that_is_not_a_session(tmp_path):
    mod = load_module()
    with pytest.raises(SystemExit):
        mod.cmd_add(
            argparse.Namespace(session=str(tmp_path), role="image", file=["missing.jpg"])
        )


def test_preschool_student_uses_a_non_numeric_grade_directory(tmp_path):
    mod = load_module()
    result = create_session(
        mod, tmp_path, student="sisi", subject="Handwriting", slug="letter-e"
    )

    assert Path(result["path"]).relative_to(tmp_path / "lesson-logs").parts[:2] == (
        "isamaya",
        "preschool",
    )
