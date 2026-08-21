from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def load_module():
    path = Path(__file__).resolve().parents[1] / "skills/ao-composer-study/scripts/write_study.py"
    spec = importlib.util.spec_from_file_location("ao_composer_writer", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(mod, tmp_path: Path, **overrides):
    media = {}
    for field, suffix, data in (
        ("work_audio", ".mp3", b"music"),
        ("work_image", ".png", b"work image"),
        ("podcast_audio", ".mp3", b"podcast"),
        ("podcast_image", ".jpg", b"podcast image"),
    ):
        path = tmp_path / f"source-{field}{suffix}"
        path.write_bytes(data)
        media[field] = path
    values = {
        "entrypoint": tmp_path / "curricula/music/ao-composer-study/curriculum.md",
        "curriculum_id": "ao-composer-study",
        "composer": "Composer A",
        "composer_details": "1900-1980; French",
        "title": "First Work",
        "ao_url": "https://example.test/ao",
        "presentation_count": 2,
        **media,
        "transcript": "A living account of the composer and this work.",
        "recording_source": "https://youtu.be/example",
        "recording_title": "First Work",
        "recording_performer": "Example Orchestra",
        "recording_duration": 321.5,
        "anchor_sources": [("Example Orchestra — program note", "https://orchestra.test/note")],
        "research_sources": [("AO schedule", "https://example.test/ao")],
    }
    values.update(overrides)
    return mod.write_study(**values)


def test_creates_all_media_study_and_index(tmp_path):
    mod = load_module()
    result = write(mod, tmp_path)

    study = Path(result["study_path"])
    assert study.relative_to(Path(result["curriculum_entrypoint"]).parent).as_posix() == "composers/composer-a/first-work.md"
    assert all(result["media_created"].values())
    for field in ("work_audio", "work_image", "podcast_audio", "podcast_image"):
        assert Path(result[f"{field}_path"]).is_file()
    text = study.read_text(encoding="utf-8")
    assert "presentation_count: 2" in text
    assert "## Composer study" in text
    assert "## Listening" in text
    assert "Example Orchestra" in text


def test_retry_is_idempotent_and_restores_missing_media(tmp_path):
    mod = load_module()
    first = write(mod, tmp_path)
    missing = Path(first["podcast_image_path"])
    missing.unlink()
    second = write(mod, tmp_path)

    assert second["created"] is False
    assert second["index_updated"] is False
    assert second["media_created"]["podcast_image"] is True
    assert missing.is_file()
    index = Path(first["curriculum_entrypoint"]).read_text(encoding="utf-8")
    assert index.count("composers/composer-a/first-work.md") == 1


@pytest.mark.parametrize("url", ["https://youtube.com/watch?v=x", "https://en.wikipedia.org/wiki/X", "https://amblesideonline.org/composers"])
def test_discovery_sources_cannot_be_anchors(tmp_path, url):
    mod = load_module()
    with pytest.raises(SystemExit, match="discovery sources cannot be anchor"):
        write(mod, tmp_path, anchor_sources=[("Discovery", url)])
