from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "skills"
        / "ao-picture-study"
        / "scripts"
        / "write_study.py"
    )
    spec = importlib.util.spec_from_file_location("ao_picture_writer", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(mod, tmp_path: Path, **overrides):
    image = tmp_path / "source.JPG"
    image.write_bytes(b"artwork")
    values = {
        "entrypoint": tmp_path / "curricula/art/ao-picture-study/curriculum.md",
        "curriculum_id": "ao-picture-study",
        "artist": "Artist A",
        "artist_details": "1900-1980; Painter",
        "title": "First Work",
        "artwork_date": "c. 1943",
        "ao_url": "https://example.test/ao",
        "image": image,
        "image_source": "https://example.test/image",
        "transcript": "Look quietly at the picture. What will you remember?",
        "anchor_sources": [
            ("Example Museum — First Work object record", "https://example.test/museum")
        ],
        "research_sources": [
            ("Example University — Artist A essay", "https://university.test/artist-a")
        ],
    }
    values.update(overrides)
    return mod.write_study(**values)


def test_creates_study_artwork_and_index(tmp_path):
    mod = load_module()
    result = write(mod, tmp_path)

    assert result["created"] is True
    study = Path(result["study_path"])
    artwork = Path(result["image_path"])
    index = Path(result["curriculum_entrypoint"])
    assert study.relative_to(index.parent).as_posix() == (
        "artists/artist-a/first-work.md"
    )
    assert artwork.name == "first-work.jpg"
    assert artwork.read_bytes() == b"artwork"
    text = study.read_text(encoding="utf-8")
    assert "## Picture study" in text
    assert "Look quietly at the picture" in text
    assert "[Example Museum — First Work object record]" in text
    assert "https://example.test/museum" in text
    assert "artists/artist-a/first-work.md" in index.read_text(encoding="utf-8")


def test_retry_reuses_study_and_does_not_duplicate_index_link(tmp_path):
    mod = load_module()
    first = write(mod, tmp_path)
    second = write(mod, tmp_path)

    assert second["created"] is False
    assert second["image_created"] is False
    assert second["index_updated"] is False
    index = Path(first["curriculum_entrypoint"]).read_text(encoding="utf-8")
    assert index.count("artists/artist-a/first-work.md") == 1


def test_existing_conflicting_study_is_not_overwritten(tmp_path):
    mod = load_module()
    result = write(mod, tmp_path)
    study = Path(result["study_path"])
    study.write_text(
        study.read_text(encoding="utf-8").replace(
            "title: First Work", "title: Different Work"
        ),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="conflicts on title"):
        write(mod, tmp_path)


def test_requires_an_anchor_source(tmp_path):
    mod = load_module()

    with pytest.raises(SystemExit, match="anchor source is required"):
        write(mod, tmp_path, anchor_sources=[])


@pytest.mark.parametrize(
    "url",
    [
        "https://en.wikipedia.org/wiki/First_Work",
        "https://commons.wikimedia.org/wiki/File:First.jpg",
        "https://amblesideonline.org/example",
    ],
)
def test_discovery_sites_cannot_be_anchor_sources(tmp_path, url):
    mod = load_module()

    with pytest.raises(SystemExit, match="discovery sources cannot be anchor"):
        write(mod, tmp_path, anchor_sources=[("Discovery page", url)])


def test_source_specs_require_descriptive_labels_and_urls():
    mod = load_module()

    assert mod.parse_source_spec(
        "Example Museum — object record|https://museum.example/object"
    ) == (
        "Example Museum — object record",
        "https://museum.example/object",
    )
    with pytest.raises(Exception, match="descriptive label"):
        mod.parse_source_spec("https://museum.example/object")
