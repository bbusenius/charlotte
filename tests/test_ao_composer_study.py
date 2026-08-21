from __future__ import annotations

import importlib.util
import re
from datetime import date
from pathlib import Path


def load_module():
    path = Path(__file__).resolve().parents[1] / "skills/ao-composer-study/scripts/rotation.py"
    spec = importlib.util.spec_from_file_location("ao_composer_rotation", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SAMPLE_HTML = """
<html><body>
<p id="term-one"><strong>2026-2027 TERM 1</strong> Composer A (1900-1980; French)</p>
<p>
1. First Work <a href="https://youtu.be/first">YouTube</a><br>
2, 3. Long Work (for 4 weeks) <a href="https://youtube.com/watch?v=primary">YouTube</a>
OR <a href="https://youtu.be/alternate">alternate</a><br>
4. Fourth Work <a href="https://archive.org/details/fourth">Archive</a><br>
</p>
<p id="term-two"><strong>2026-2027 TERM 2</strong> Composer B (1870-1930)</p>
<p>
1. Another Long Work (spend four weeks) <a href="https://youtu.be/another">YouTube</a><br>
2. Last Work <a href="https://youtu.be/last">YouTube</a><br>
</p>
</body></html>
"""


def test_parser_honors_combined_slots_alternatives_and_four_weeks():
    mod = load_module()
    schedules = mod.parse_rotation(SAMPLE_HTML)

    assert len(schedules) == 2
    first = schedules[0]
    assert first["composer"] == "Composer A"
    assert first["composer_details"] == "1900-1980; French"
    assert [work["title"] for work in first["works"]] == [
        "First Work",
        "Long Work",
        "Fourth Work",
    ]
    long_work = first["works"][1]
    assert long_work["slot_numbers"] == [2, 3]
    assert long_work["presentation_count"] == 2
    assert long_work["recording_urls"] == [
        "https://youtube.com/watch?v=primary",
        "https://youtu.be/alternate",
    ]
    assert schedules[1]["works"][0]["presentation_count"] == 2


def test_cursor_reselects_long_work_then_advances_without_duplicate_ids(tmp_path):
    mod = load_module()
    schedules = mod.parse_rotation(SAMPLE_HTML)

    first = mod.resolve_next(schedules, None, date(2026, 8, 15))
    assert first["title"] == "First Work"
    cursor_path = tmp_path / "student.yaml"
    mod.commit_cursor(cursor_path, "student", first, first["suggested_work_slide_id"], first["suggested_podcast_slide_id"])

    long_first = mod.resolve_next(schedules, mod.load_cursor(cursor_path), date(2026, 8, 15))
    assert long_first["title"] == "Long Work"
    assert long_first["presentation"] == 1
    mod.commit_cursor(cursor_path, "student", long_first, long_first["suggested_work_slide_id"], long_first["suggested_podcast_slide_id"])

    repeated = mod.resolve_next(schedules, mod.load_cursor(cursor_path), date(2026, 8, 15))
    assert repeated["title"] == "Long Work"
    assert repeated["repeat_presentation"] is True
    assert repeated["presentation"] == 2
    assert repeated["suggested_work_slide_id"] == long_first["suggested_work_slide_id"]
    assert repeated["suggested_podcast_slide_id"] == long_first["suggested_podcast_slide_id"]
    mod.commit_cursor(cursor_path, "student", repeated, repeated["suggested_work_slide_id"], repeated["suggested_podcast_slide_id"])

    fourth = mod.resolve_next(schedules, mod.load_cursor(cursor_path), date(2026, 8, 15))
    assert fourth["title"] == "Fourth Work"
    assert fourth["presentation"] == 1


def test_skill_keeps_music_primary_and_is_harness_agnostic():
    skill = (Path(__file__).resolve().parents[1] / "skills/ao-composer-study/SKILL.md").read_text(encoding="utf-8")
    assert "Music is the primary encounter" in skill
    assert "secondary podcast slide" in skill
    assert "Do not select the podcast slide" in skill
    assert "Do not turn the podcast into a guided-listening inventory" in skill
    assert "Biblical, literary, dramatic, historical, and liturgical meaning is welcome" in skill
    assert "Never install software" in skill
    assert "Search is only for discovering candidate URLs" in skill
    assert "before writing the claim ledger" in skill
    assert "Do not discard a stronger source" in skill
    assert "Never pipe a network response into a shell or interpreter" in skill
    assert "never use a retrieval method that requires interactive approval" in skill
    assert "Before calling TTS, complete a transcript preflight" in skill
    assert "Generate TTS only after this preflight passes" in skill
    assert "Inspect the actual pixels of both generated images" in skill
    assert "Correct only the failed content or composition constraint" in skill
    assert "The capability order is mandatory" in skill
    assert "do not probe or attempt `scripts/charlotte_image.py` first" in skill
    for harness in ("Hermes", "OpenClaw", "Codex", "Gemini", "Grok"):
        assert re.search(rf"\b{harness}\b", skill) is None
