from __future__ import annotations

import argparse
import importlib.util
import re
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
            "lesson_log_read", scripts_dir / "lesson_log_read.py"
        )
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(scripts_dir))


def build_env(tmp_path: Path) -> dict[str, str]:
    registry = {
        "students": {
            "eliana": {
                "display_name": "Eliana",
                "grade": 3,
                "aliases": ["eliana"],
                "subjects": ["Science", "Language Arts & Literature"],
            }
        }
    }
    path = tmp_path / "students.yaml"
    path.write_text(yaml.safe_dump(registry), encoding="utf-8")
    return {"root": str(tmp_path / "lesson-logs"), "registry": str(path)}


def write_session(
    env: dict[str, str],
    *,
    date: str,
    subject: str,
    slug: str,
    did: str = "We read the chapter and narrated it back.",
    went: str = "Went smoothly.",
    grade_dir: str = "grade-3",
    images: str | None = None,
    messages: str | None = None,
    videos: str | None = None,
    lesson_number: int | None = None,
    lesson_title: str | None = None,
    curriculum: str | None = None,
    source: str | None = None,
    pages: str | None = None,
) -> Path:
    year, month, day = date.split("-")
    subject_slug = re.sub(r"[^a-z0-9]+", "-", subject.lower()).strip("-")
    session = (
        Path(env["root"])
        / "eliana"
        / grade_dir
        / year
        / month
        / day
        / f"{subject_slug}-{slug}"
    )
    (session / "sources").mkdir(parents=True)
    frontmatter = {
        "schema": "lesson-log/v1",
        "student": "eliana",
        "grade": 3,
        "date": date,
        "subject": subject,
        "lesson": {
            "curriculum": curriculum,
            "number": lesson_number,
            "title": lesson_title,
            "source": source,
            "pages": pages,
        },
        "teacher": "Brad",
        "concepts": ["narration"],
    }
    body = yaml.safe_dump(frontmatter, sort_keys=False).strip()
    (session / "log.md").write_text(
        f"---\n{body}\n---\n\n# {subject}\n\n## What we did\n\n{did}\n\n"
        f"## How it went\n\n{went}\n\n## What comes next\n\nKeep going.\n",
        encoding="utf-8",
    )
    if images:
        (session / "images.md").write_text(images, encoding="utf-8")
    if messages:
        (session / "messages.md").write_text(messages, encoding="utf-8")
    if videos:
        (session / "videos.md").write_text(videos, encoding="utf-8")
    return session


def list_args(env: dict[str, str], **kwargs) -> argparse.Namespace:
    base = {
        "root": env["root"],
        "registry": env["registry"],
        "student": "eliana",
        "subject": None,
        "date_from": None,
        "date_to": None,
        "latest": None,
        "limit": 20,
        "include_section": None,
    }
    base.update(kwargs)
    return argparse.Namespace(**base)


def search_args(env: dict[str, str], query: str, **kwargs) -> argparse.Namespace:
    base = {
        "root": env["root"],
        "registry": env["registry"],
        "student": "eliana",
        "query": query,
        "subject": None,
        "date_from": None,
        "date_to": None,
        "limit": 10,
        "snippets": 3,
    }
    base.update(kwargs)
    return argparse.Namespace(**base)


def test_list_returns_newest_first(tmp_path):
    mod = load_module()
    env = build_env(tmp_path)
    write_session(env, date="2026-07-20", subject="Science", slug="science-early")
    write_session(env, date="2026-07-24", subject="Science", slug="science-late")

    result = mod.cmd_list(list_args(env))
    assert [s["date"] for s in result["sessions"]] == ["2026-07-24", "2026-07-20"]


def test_list_latest_one_answers_what_did_she_last_do(tmp_path):
    mod = load_module()
    env = build_env(tmp_path)
    write_session(env, date="2026-07-20", subject="Science", slug="plot")
    write_session(env, date="2026-07-24", subject="Language Arts & Literature", slug="la")

    result = mod.cmd_list(list_args(env, subject="Science", latest=1))
    assert result["returned"] == 1
    assert result["sessions"][0]["subject"] == "Science"


def test_list_matches_subject_case_insensitively(tmp_path):
    mod = load_module()
    env = build_env(tmp_path)
    write_session(env, date="2026-07-24", subject="Science", slug="plot")

    assert mod.cmd_list(list_args(env, subject="science"))["count"] == 1


def test_list_includes_a_bounded_excerpt_not_the_whole_log(tmp_path):
    mod = load_module()
    env = build_env(tmp_path)
    write_session(env, date="2026-07-24", subject="Science", slug="plot", did="x " * 400)

    summary = mod.cmd_list(list_args(env))["sessions"][0]["summary"]
    assert len(summary) <= mod.SUMMARY_CHARS + 1
    assert summary.endswith("…")


def test_list_answers_what_page_are_we_on(tmp_path):
    """The real book page, from the summary, without opening the session."""
    mod = load_module()
    env = build_env(tmp_path)
    write_session(env, date="2026-07-20", subject="Language Arts & Literature",
                  slug="lesson-111", lesson_number=111, pages="44-46")
    write_session(env, date="2026-07-24", subject="Language Arts & Literature",
                  slug="lesson-112", lesson_number=112, pages="47-48")

    latest = mod.cmd_list(
        list_args(env, subject="Language Arts & Literature", latest=1)
    )["sessions"][0]

    assert latest["pages"] == "47-48"
    assert latest["lesson_number"] == 112


def test_list_surfaces_exact_curriculum_provenance(tmp_path):
    mod = load_module()
    env = build_env(tmp_path)
    write_session(
        env,
        date="2026-07-24",
        subject="Art",
        slug="the-four-freedoms",
        curriculum="ao-picture-study",
        source=(
            "curricula/art/ao-picture-study/artists/"
            "norman-rockwell/the-four-freedoms.md"
        ),
    )

    latest = mod.cmd_list(list_args(env))["sessions"][0]
    assert latest["curriculum"] == "ao-picture-study"
    assert latest["source"].endswith("the-four-freedoms.md")


def test_list_can_fold_in_observations_for_a_whole_week(tmp_path):
    """Weekly slide selection needs 'how it went' without a call per session."""
    mod = load_module()
    env = build_env(tmp_path)
    write_session(env, date="2026-07-24", subject="Science", slug="plot",
                  went="Confused 6s and 9s; wanted to redo the last four.")

    result = mod.cmd_list(list_args(env, include_section=["how it went"]))
    session = result["sessions"][0]
    assert session["sections"]["How it went"].startswith("Confused 6s and 9s")


def test_list_omits_the_sections_key_when_nothing_was_requested(tmp_path):
    mod = load_module()
    env = build_env(tmp_path)
    write_session(env, date="2026-07-24", subject="Science", slug="plot")

    assert "sections" not in mod.cmd_list(list_args(env))["sessions"][0]


def test_list_honours_a_date_range(tmp_path):
    mod = load_module()
    env = build_env(tmp_path)
    write_session(env, date="2026-07-01", subject="Science", slug="old")
    write_session(env, date="2026-07-24", subject="Science", slug="new")

    result = mod.cmd_list(list_args(env, date_from="2026-07-20", date_to="2026-07-31"))
    assert [s["date"] for s in result["sessions"]] == ["2026-07-24"]


def test_list_spans_grade_directories(tmp_path):
    """What she covered in a previous grade is still part of her history."""
    mod = load_module()
    env = build_env(tmp_path)
    write_session(env, date="2025-11-04", subject="Science", slug="old", grade_dir="grade-2")
    write_session(env, date="2026-07-24", subject="Science", slug="new")

    assert mod.cmd_list(list_args(env))["count"] == 2


def test_search_finds_the_log_body(tmp_path):
    mod = load_module()
    env = build_env(tmp_path)
    write_session(
        env,
        date="2026-07-24",
        subject="Language Arts & Literature",
        slug="guide-words",
        did="Practiced guide words in the dictionary.",
    )
    write_session(env, date="2026-07-23", subject="Science", slug="plot")

    result = mod.cmd_search(search_args(env, "guide words"))
    assert result["count"] == 1
    assert "log.md" in result["sessions"][0]["matches"]


def test_search_reads_captured_page_text(tmp_path):
    """The point of keeping a text layer: captured pages are searchable."""
    mod = load_module()
    env = build_env(tmp_path)
    write_session(
        env,
        date="2026-07-24",
        subject="Science",
        slug="plot",
        images="## sources/image-01.jpg\nkind: page\nref: Workbook p. 47\n\nDecomposers break down fallen wood.\n",
    )

    result = mod.cmd_search(search_args(env, "decomposers"))
    assert result["count"] == 1
    assert "images.md" in result["sessions"][0]["matches"]


def test_search_reads_video_transcripts(tmp_path):
    """A watched video is searchable by what it said, not only its URL."""
    mod = load_module()
    env = build_env(tmp_path)
    write_session(
        env,
        date="2026-07-24",
        subject="Science",
        slug="bees",
        videos=(
            "## https://www.youtube.com/watch?v=example\n"
            "title: How Bees Make Honey\n\n"
            "Bees collect nectar and fan the water off until it becomes honey.\n"
        ),
    )

    result = mod.cmd_search(search_args(env, "fan the water"))
    assert result["count"] == 1
    assert "videos.md" in result["sessions"][0]["matches"]


def test_search_reads_the_parents_own_messages(tmp_path):
    mod = load_module()
    env = build_env(tmp_path)
    write_session(
        env,
        date="2026-07-24",
        subject="Science",
        slug="plot",
        messages="## 2026-07-24 10:22 · Brad · signal\n\nShe called it a fern forest.\n",
    )

    result = mod.cmd_search(search_args(env, "fern forest"))
    assert "messages.md" in result["sessions"][0]["matches"]


def test_search_is_case_insensitive_and_bounds_snippets(tmp_path):
    mod = load_module()
    env = build_env(tmp_path)
    write_session(env, date="2026-07-24", subject="Science", slug="plot",
                  did="Fulcrum. " + ("filler " * 200) + "fulcrum again.")

    result = mod.cmd_search(search_args(env, "FULCRUM", snippets=1))
    snippets = result["sessions"][0]["matches"]["log.md"]
    assert len(snippets) == 1
    assert len(snippets[0]) <= mod.SNIPPET_CHARS + 1


def test_search_returns_nothing_for_an_absent_term(tmp_path):
    mod = load_module()
    env = build_env(tmp_path)
    write_session(env, date="2026-07-24", subject="Science", slug="plot")

    assert mod.cmd_search(search_args(env, "photosynthesis"))["count"] == 0


def test_show_returns_only_the_requested_section(tmp_path):
    mod = load_module()
    env = build_env(tmp_path)
    session = write_session(env, date="2026-07-24", subject="Science", slug="plot",
                            did="Staked the plot.", went="Confused 6s and 9s.")

    result = mod.cmd_show(
        argparse.Namespace(session=str(session), file="log.md",
                           section=["how it went"], full=False)
    )
    assert list(result["sections"]) == ["How it went"]
    assert result["sections"]["How it went"] == "Confused 6s and 9s."


def test_show_lists_available_sections_when_none_requested(tmp_path):
    mod = load_module()
    env = build_env(tmp_path)
    session = write_session(env, date="2026-07-24", subject="Science", slug="plot")

    result = mod.cmd_show(
        argparse.Namespace(session=str(session), file="log.md", section=None, full=False)
    )
    assert result["available_sections"] == ["What we did", "How it went", "What comes next"]
    assert "sections" not in result


def test_show_full_returns_the_body_without_frontmatter(tmp_path):
    mod = load_module()
    env = build_env(tmp_path)
    session = write_session(env, date="2026-07-24", subject="Science", slug="plot")

    result = mod.cmd_show(
        argparse.Namespace(session=str(session), file="log.md", section=None, full=True)
    )
    assert "schema: lesson-log/v1" not in result["content"]
    assert "## What we did" in result["content"]


def test_show_errors_on_a_missing_file(tmp_path):
    mod = load_module()
    env = build_env(tmp_path)
    session = write_session(env, date="2026-07-24", subject="Science", slug="plot")

    with pytest.raises(SystemExit):
        mod.cmd_show(
            argparse.Namespace(session=str(session), file="images.md",
                               section=None, full=False)
        )
