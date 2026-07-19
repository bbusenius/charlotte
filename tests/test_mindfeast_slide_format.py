from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BUILDER_DIR = ROOT / "skills" / "mindfeast-slide-builder" / "scripts"


def load_module(filename: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, BUILDER_DIR / filename)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_package(
    root: Path,
    slide_id: str,
    slide_type: str,
    body: str,
    *fields: str,
    media: bool = False,
) -> Path:
    slide_dir = root / slide_id
    slide_dir.mkdir()
    if media:
        (slide_dir / "example.jpg").write_bytes(b"test fixture")
    frontmatter = "\n".join(
        [
            "---",
            f"id: {slide_id}",
            f"type: {slide_type}",
            *fields,
            "orientation: landscape",
            "---",
        ]
    )
    (slide_dir / "slide.md").write_text(
        f"{frontmatter}\n\n{body}\n", encoding="utf-8"
    )
    return slide_dir


@pytest.mark.parametrize(
    ("slide_id", "slide_type", "body", "fields", "media"),
    [
        (
            "capital-question",
            "question",
            "What is the capital of France?",
            ("image: example.jpg", 'answer: "Paris"'),
            True,
        ),
        (
            "moon-context",
            "informational",
            "The Moon reflects sunlight.",
            (),
            False,
        ),
        (
            "cloud-observation",
            "essay",
            "Describe the cloud shapes you notice.",
            ("image: example.jpg",),
            True,
        ),
        (
            "gratitude-noticing",
            "gratitude",
            "What is one good thing you noticed today?",
            ("image: example.jpg",),
            True,
        ),
    ],
)
def test_validator_accepts_each_supported_type(
    tmp_path, slide_id, slide_type, body, fields, media
):
    validator = load_module("validate_slide.py", f"validator_{slide_type}")
    slide_dir = write_package(
        tmp_path, slide_id, slide_type, body, *fields, media=media
    )

    errors, warnings = validator.validate(slide_dir)

    assert errors == []
    assert warnings == []


def test_builder_creates_valid_gratitude_variation(tmp_path, monkeypatch, capsys):
    builder = load_module("make_slide.py", "mindfeast_make_slide")
    validator = load_module("validate_slide.py", "mindfeast_validate_slide")
    source_image = tmp_path / "source.jpg"
    source_image.write_bytes(b"test fixture")
    output = tmp_path / "slides"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "make_slide.py",
            "--out",
            str(output),
            "--id",
            "gratitude-noticing",
            "--type",
            "gratitude",
            "--subject",
            "reflection",
            "--image",
            str(source_image),
            "--orientation",
            "landscape",
            "--question",
            "What is one good thing you noticed today?",
        ],
    )

    assert builder.main() == 0
    slide_dir = output / "gratitude-noticing"
    markdown = (slide_dir / "slide.md").read_text(encoding="utf-8")
    errors, warnings = validator.validate(slide_dir)

    assert "type: gratitude" in markdown
    assert "format_version" not in markdown
    assert "answer:" not in markdown
    assert errors == []
    assert warnings == []
    assert str(slide_dir) in capsys.readouterr().out


def test_v1_schema_describes_existing_unversioned_frontmatter():
    schema = json.loads(
        (ROOT / "docs" / "mindfeast-slide-frontmatter-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )

    assert schema["properties"]["type"]["enum"] == [
        "question",
        "informational",
        "essay",
        "gratitude",
    ]
    assert "format_version" not in schema["properties"]
