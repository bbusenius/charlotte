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
        "narration",
        "conversation",
    ]
    assert "format_version" not in schema["properties"]


def slide_case(
    name,
    slide_type,
    fields,
    files,
    error=None,
    *,
    schema_valid=None,
    body="Tell what you know.",
):
    if schema_valid is None:
        schema_valid = error is None
    return pytest.param(slide_type, fields, files, body, error, schema_valid, id=name)


CONVERSATION_FIELDS = {
    "intent": "Explain how roots help a plant grow.",
    "turns": 3,
    "context": "context.txt",
}
TEXT_FILES = {"context.txt": b"Roots absorb water and anchor a plant."}
NEW_TYPE_CASES = [
    slide_case(
        "narration-audio",
        "narration",
        {"audio": "audio.mp3"},
        {"audio.mp3": b"audio fixture"},
    ),
    slide_case(
        "narration-script",
        "narration",
        {"script": "script.txt"},
        {"script.txt": b"A seed grows roots."},
    ),
    slide_case(
        "narration-passage",
        "narration",
        {"passage": "passage.txt"},
        {"passage.txt": b"A seed grows roots."},
    ),
    slide_case("conversation", "conversation", CONVERSATION_FIELDS, TEXT_FILES),
    slide_case(
        "narration-two-sources",
        "narration",
        {"audio": "audio.mp3", "script": "script.txt"},
        {"audio.mp3": b"audio", "script.txt": b"Text"},
        "exactly one",
    ),
    slide_case(
        "narration-two-text-sources",
        "narration",
        {"script": "script.txt", "passage": "passage.txt"},
        {"script.txt": b"Text", "passage.txt": b"Text"},
        "exactly one",
    ),
    slide_case(
        "narration-three-sources",
        "narration",
        {"audio": "audio.mp3", "script": "script.txt", "passage": "passage.txt"},
        {"audio.mp3": b"audio", "script.txt": b"Text", "passage.txt": b"Text"},
        "exactly one",
    ),
    slide_case("narration-no-source", "narration", {}, {}, "exactly one"),
    slide_case(
        "narration-missing-file",
        "narration",
        {"audio": "missing.mp3"},
        {},
        "audio file missing",
        schema_valid=True,
    ),
    *[
        slide_case(
            f"{field}-missing-file",
            "narration",
            {field: "missing.txt"},
            {},
            f"{field} file missing",
            schema_valid=True,
        )
        for field in ("script", "passage")
    ],
    *[
        slide_case(
            f"blank-{field}",
            "conversation" if field == "context" else "narration",
            (
                {**CONVERSATION_FIELDS, "context": "text.txt"}
                if field == "context"
                else {field: "text.txt"}
            ),
            {"text.txt": b" \n\t"},
            f"{field} file is blank",
            schema_valid=True,
        )
        for field in ("script", "passage", "context")
    ],
    slide_case(
        "empty-script",
        "narration",
        {"script": "script.txt"},
        {"script.txt": b""},
        "script file is blank",
        schema_valid=True,
    ),
    *[
        slide_case(
            f"{field}-path-{separator}",
            "conversation" if field == "context" else "narration",
            (
                {**CONVERSATION_FIELDS, "context": filename}
                if field == "context"
                else {field: filename}
            ),
            {},
            f"{field} must be a filename, not a path",
        )
        for field in ("audio", "script", "passage", "context")
        for separator, filename in (
            ("slash", "nested/file.txt"),
            ("backslash", "nested\\file.txt"),
        )
    ],
    slide_case(
        "conversation-no-intent",
        "conversation",
        {"turns": 3, "context": "context.txt"},
        TEXT_FILES,
        "intent must be a non-blank string",
    ),
    *[
        slide_case(
            f"conversation-intent-{name}",
            "conversation",
            {**CONVERSATION_FIELDS, "intent": value},
            TEXT_FILES,
            "intent must be a non-blank string",
        )
        for name, value in (
            ("empty", ""),
            ("blank", " \t"),
            ("number", 3),
            ("null", None),
        )
    ],
    slide_case(
        "conversation-no-turns",
        "conversation",
        {"intent": "Explain.", "context": "context.txt"},
        TEXT_FILES,
        "turns must be an integer >= 1",
    ),
    *[
        slide_case(
            f"conversation-turns-{name}",
            "conversation",
            {**CONVERSATION_FIELDS, "turns": value},
            TEXT_FILES,
            "turns must be an integer >= 1",
            schema_valid=name == "whole-float",
        )
        for name, value in (
            ("zero", 0),
            ("negative", -1),
            ("string", "3"),
            ("true", True),
            ("false", False),
            ("fraction", 1.5),
            ("whole-float", 3.0),
            ("null", None),
        )
    ],
    slide_case(
        "conversation-one-turn",
        "conversation",
        {**CONVERSATION_FIELDS, "turns": 1},
        TEXT_FILES,
    ),
    slide_case(
        "conversation-missing-context",
        "conversation",
        {"intent": "Explain.", "turns": 3},
        {},
        "context missing",
    ),
    slide_case(
        "conversation-missing-context-file",
        "conversation",
        CONVERSATION_FIELDS,
        {},
        "context file missing",
        schema_valid=True,
    ),
    *[
        slide_case(
            f"{field}-invalid-filename-{name}",
            "conversation" if field == "context" else "narration",
            (
                {**CONVERSATION_FIELDS, "context": value}
                if field == "context"
                else {field: value}
            ),
            {},
            f"{field} must be a non-blank filename",
        )
        for field in ("audio", "script", "passage", "context")
        for name, value in (
            ("empty", ""),
            ("blank", "  "),
            ("null", None),
            ("number", 3),
        )
    ],
    *[
        slide_case(
            f"{field}-invalid-utf8",
            "conversation" if field == "context" else "narration",
            (
                {**CONVERSATION_FIELDS, "context": "text.txt"}
                if field == "context"
                else {field: "text.txt"}
            ),
            {"text.txt": b"\xff"},
            f"{field} file must be readable UTF-8 text",
            schema_valid=True,
        )
        for field in ("script", "passage", "context")
    ],
    slide_case(
        "narration-blank-prompt",
        "narration",
        {"script": "script.txt"},
        {"script.txt": b"Text"},
        "prompt body missing",
        schema_valid=True,
        body=" \n\t",
    ),
    slide_case(
        "conversation-blank-question",
        "conversation",
        CONVERSATION_FIELDS,
        TEXT_FILES,
        "question body missing",
        schema_valid=True,
        body=" \n\t",
    ),
]


@pytest.mark.parametrize(
    "slide_type,fields,files,body,error,schema_valid", NEW_TYPE_CASES
)
def test_new_type_package_validation(
    tmp_path, slide_type, fields, files, body, error, schema_valid
):
    validator = load_module("validate_slide.py", "validator_new_types")
    slide_dir = write_package(
        tmp_path,
        "example-slide",
        slide_type,
        body,
        *(f"{key}: {json.dumps(value)}" for key, value in fields.items()),
    )
    for filename, content in files.items():
        (slide_dir / filename).write_bytes(content)

    errors, warnings = validator.validate(slide_dir)

    if error is None:
        assert errors == []
        assert warnings == []
    else:
        assert any(error in message for message in errors), errors


@pytest.mark.parametrize(
    "slide_type,fields,files,body,error,schema_valid", NEW_TYPE_CASES
)
def test_new_type_frontmatter_schema(
    slide_type, fields, files, body, error, schema_valid
):
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(
        (ROOT / "docs" / "mindfeast-slide-frontmatter-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    jsonschema.Draft202012Validator.check_schema(schema)
    frontmatter = {"id": "example-slide", "type": slide_type, **fields}
    assert jsonschema.Draft202012Validator(schema).is_valid(frontmatter) is schema_valid


@pytest.mark.parametrize("slide_type", ["narration", "conversation"])
def test_new_types_allow_optional_media_and_warn_about_ignored_fields(
    tmp_path, slide_type
):
    validator = load_module("validate_slide.py", "validator_optional_media")
    fields = (
        {"script": "script.txt"}
        if slide_type == "narration"
        else {**CONVERSATION_FIELDS, "audio": "audio.mp3"}
    )
    fields.update(
        {
            "image": "example.jpg",
            "answer": "Text",
            "accept": ["Text"],
            "choices": ["Text"],
        }
    )
    slide_dir = write_package(
        tmp_path,
        "example-slide",
        slide_type,
        "Tell what you know.",
        *(f"{key}: {json.dumps(value)}" for key, value in fields.items()),
        media=True,
    )
    for filename in ("script.txt", "context.txt", "audio.mp3"):
        (slide_dir / filename).write_text("Text", encoding="utf-8")

    errors, warnings = validator.validate(slide_dir)

    assert errors == []
    assert set(warnings) == {
        f"{slide_type} slides ignore {field}"
        for field in ("answer", "accept", "choices")
    }


@pytest.mark.parametrize("field", ["audio", "script", "passage", "context"])
def test_unknown_source_extension_is_a_warning(tmp_path, field):
    validator = load_module("validate_slide.py", "validator_extensions")
    fields = (
        {**CONVERSATION_FIELDS, "context": "text.unknown"}
        if field == "context"
        else {field: "text.unknown"}
    )
    slide_dir = write_package(
        tmp_path,
        "example-slide",
        "conversation" if field == "context" else "narration",
        "Tell what you know.",
        *(f"{key}: {json.dumps(value)}" for key, value in fields.items()),
    )
    (slide_dir / "text.unknown").write_text("Text", encoding="utf-8")

    errors, warnings = validator.validate(slide_dir)

    assert errors == []
    assert warnings == [f"{field} file has an unknown extension: text.unknown"]
