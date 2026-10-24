from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BUILDER_DIR = ROOT / "skills" / "mindfeast-slide-builder" / "scripts"


def test_narration_and_conversation_slides_get_images():
    skill = (ROOT / "skills" / "mindfeast-slide-builder" / "SKILL.md").read_text(encoding="utf-8")
    workflow = skill.split("## Workflow", 1)[1].split("## Question Slide Design", 1)[0]
    design = skill.split("## Narration and conversation design", 1)[1].split("## Gratitude Packages", 1)[0]
    assert "need no image" not in skill
    assert "decorative image" not in skill
    assert "Do this for narration and conversation slides as well as the other types." in workflow
    assert "Generate an image for both types" in design


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
    "context": "context.md",
}
TEXT_FILES = {"context.md": b"Roots absorb water and anchor a plant."}
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
        {"script": "script.md"},
        {"script.md": b"A seed grows roots."},
    ),
    slide_case(
        "narration-passage",
        "narration",
        {"passage": "passage.md"},
        {"passage.md": b"A seed grows roots."},
    ),
    slide_case("conversation", "conversation", CONVERSATION_FIELDS, TEXT_FILES),
    slide_case(
        "narration-two-sources",
        "narration",
        {"audio": "audio.mp3", "script": "script.md"},
        {"audio.mp3": b"audio", "script.md": b"Text"},
        "exactly one",
    ),
    slide_case(
        "narration-two-text-sources",
        "narration",
        {"script": "script.md", "passage": "passage.md"},
        {"script.md": b"Text", "passage.md": b"Text"},
        "exactly one",
    ),
    slide_case(
        "narration-three-sources",
        "narration",
        {"audio": "audio.mp3", "script": "script.md", "passage": "passage.md"},
        {"audio.mp3": b"audio", "script.md": b"Text", "passage.md": b"Text"},
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
            {field: "missing.md"},
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
                {**CONVERSATION_FIELDS, "context": "text.md"}
                if field == "context"
                else {field: "text.md"}
            ),
            {"text.md": b" \n\t"},
            f"{field} file is blank",
            schema_valid=True,
        )
        for field in ("script", "passage", "context")
    ],
    slide_case(
        "empty-script",
        "narration",
        {"script": "script.md"},
        {"script.md": b""},
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
            ("slash", "nested/file.md"),
            ("backslash", "nested\\file.md"),
        )
    ],
    slide_case(
        "conversation-no-intent",
        "conversation",
        {"turns": 3, "context": "context.md"},
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
        {"intent": "Explain.", "context": "context.md"},
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
                {**CONVERSATION_FIELDS, "context": "text.md"}
                if field == "context"
                else {field: "text.md"}
            ),
            {"text.md": b"\xff"},
            f"{field} file must be readable UTF-8 text",
            schema_valid=True,
        )
        for field in ("script", "passage", "context")
    ],
    slide_case(
        "narration-blank-prompt",
        "narration",
        {"script": "script.md"},
        {"script.md": b"Text"},
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
        {"script": "script.md"}
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
    for filename in ("script.md", "context.md", "audio.mp3"):
        (slide_dir / filename).write_text("Text", encoding="utf-8")

    errors, warnings = validator.validate(slide_dir)

    assert errors == []
    assert set(warnings) == {
        f"{slide_type} slides ignore {field}"
        for field in ("answer", "accept", "choices")
    }


@pytest.mark.parametrize("filename", ["text.unknown", "text.txt"])
@pytest.mark.parametrize("field", ["audio", "script", "passage", "context"])
def test_unknown_source_extension_is_a_warning(tmp_path, field, filename):
    validator = load_module("validate_slide.py", "validator_extensions")
    fields = (
        {**CONVERSATION_FIELDS, "context": filename}
        if field == "context"
        else {field: filename}
    )
    slide_dir = write_package(
        tmp_path,
        "example-slide",
        "conversation" if field == "context" else "narration",
        "Tell what you know.",
        *(f"{key}: {json.dumps(value)}" for key, value in fields.items()),
    )
    (slide_dir / filename).write_text("Text", encoding="utf-8")

    errors, warnings = validator.validate(slide_dir)

    assert errors == []
    assert warnings == [f"{field} file has an unknown extension: {filename}"]


def run_builder(monkeypatch, output, slide_type, *flags):
    builder = load_module("make_slide.py", "builder_cli")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "make_slide.py", "--out", str(output), "--id", "example-slide",
            "--type", slide_type, "--orientation", "portrait",
            "--question", "What did you learn about roots?", *flags,
        ],
    )
    return builder.main()


@pytest.mark.parametrize("field", ["script", "passage", "context", "audio"])
@pytest.mark.parametrize("from_file", [False, True])
@pytest.mark.parametrize("with_media", [False, True])
def test_builder_new_sources_validate_and_preserve_content(
    tmp_path, monkeypatch, field, from_file, with_media
):
    import wave

    validator = load_module("validate_slide.py", "validator_builder_sources")
    output = tmp_path / "slides"
    content = "# Roots\n\nRoots absorb **water** and anchor the plant.\n\nMore roots grow.\n"
    source = tmp_path / "source.txt"
    source.write_text(content, encoding="utf-8")
    audio = tmp_path / "provided.wav"
    with wave.open(str(audio), "wb") as wav:
        wav.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
        wav.writeframes(b"\x00\x00" * 800)
    slide_type = "conversation" if field == "context" else "narration"
    flags = (
        ["--audio", str(audio)] if field == "audio" else
        [f"--{field}-file", str(source)] if from_file else
        [f"--{field}-text", content]
    )
    if slide_type == "conversation":
        flags += ["--intent", "Explain roots to an early reader.", "--turns", "1"]
    if with_media:
        image = tmp_path / "image.png"
        image.write_bytes(b"test fixture")
        flags += ["--image", str(image)]
        if slide_type == "conversation":
            flags += ["--audio", str(audio)]

    assert run_builder(monkeypatch, output, slide_type, *flags) == 0
    slide_dir = output / "example-slide"
    assert validator.validate(slide_dir) == ([], [])
    markdown = (slide_dir / "slide.md").read_text(encoding="utf-8")
    data, body = validator.parse_frontmatter(markdown)
    assert body == "What did you learn about roots?"
    assert data[field] == ("provided.wav" if field == "audio" else f"{field}.md")
    if field == "audio":
        assert (slide_dir / "provided.wav").read_bytes() == audio.read_bytes()
    else:
        assert (slide_dir / f"{field}.md").read_text(encoding="utf-8") == content
    if with_media:
        assert (slide_dir / "image.png").read_bytes() == image.read_bytes()
        if slide_type == "conversation":
            assert (slide_dir / "provided.wav").read_bytes() == audio.read_bytes()
    else:
        assert "image" not in data
    keys = ["id", "type"] + (["image"] if with_media else [])
    if slide_type == "conversation":
        keys += (["audio"] if with_media else []) + ["intent", "turns", "context"]
    else:
        keys += [field]
    assert list(data) == keys + ["difficulty", "orientation"]
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((ROOT / "docs/mindfeast-slide-frontmatter-v1.schema.json").read_text())
    jsonschema.validate(data, schema)


def test_builder_intent_round_trips_yaml_and_frontmatter_delimiters(tmp_path, monkeypatch):
    intent = 'Explain "roots": # facts\\notes\n---\r\t- café\x01\x7f\x85\u2028\u2029'
    output = tmp_path / "slides"
    assert run_builder(
        monkeypatch, output, "conversation", "--context-text", "Roots absorb water.",
        "--intent", intent, "--turns", "3",
    ) == 0
    validator = load_module("validate_slide.py", "validator_intent")
    slide_dir = output / "example-slide"
    markdown = (slide_dir / "slide.md").read_text(encoding="utf-8")
    data, _ = validator.parse_frontmatter(markdown)
    assert data["intent"] == intent
    assert markdown.count("---") == 2
    assert '\\u002d\\u002d\\u002d' in markdown
    assert validator.validate(slide_dir) == ([], [])


@pytest.mark.parametrize(
    "slide_type,flags,error",
    [
        ("narration", [], "exactly one"),
        ("narration", ["--script-text", "Roots.", "--passage-text", "Roots."], "exactly one"),
        ("narration", ["--audio", "missing.wav", "--script-text", "Roots."], "exactly one"),
        ("narration", ["--audio", "missing.wav", "--passage-text", "Roots."], "exactly one"),
        ("narration", ["--audio", "missing.wav", "--script-text", "Roots.", "--passage-text", "Roots."], "exactly one"),
        ("narration", ["--audio", "missing.wav"], "media file not found"),
        ("narration", ["--audio", ""], "media file not found"),
        ("narration", ["--script-text", " \n\t"], "non-blank Markdown"),
        ("narration", ["--passage-text", ""], "non-blank Markdown"),
        ("narration", ["--script-text", "Roots.", "--question", " "], "non-blank --question"),
        ("narration", ["--script-text", "Roots.", "--text", " "], "non-blank --question"),
        ("conversation", ["--intent", "Explain.", "--turns", "1"], "provide --context"),
        ("conversation", ["--intent", "Explain.", "--turns", "1", "--context-text", " "], "non-blank Markdown"),
        ("conversation", ["--context-text", "Roots.", "--turns", "1"], "non-blank --intent"),
        ("conversation", ["--context-text", "Roots.", "--turns", "1", "--intent", " "], "non-blank --intent"),
        ("conversation", ["--context-text", "Roots.", "--intent", "Explain."], "integer >= 1"),
        ("conversation", ["--context-text", "Roots.", "--intent", "Explain.", "--turns", "0"], "integer >= 1"),
        ("conversation", ["--context-text", "Roots.", "--intent", "Explain.", "--turns", "-1"], "integer >= 1"),
        ("conversation", ["--turns", "3.0"], "invalid int value"),
        ("conversation", ["--turns", "two"], "invalid int value"),
        ("conversation", ["--question", " "], "non-blank --question"),
    ],
)
@pytest.mark.parametrize("existing", [False, True])
def test_builder_rejects_invalid_input_before_writing(
    tmp_path, monkeypatch, capsys, slide_type, flags, error, existing
):
    output = tmp_path / "slides"
    slide_dir = output / "example-slide"
    if existing:
        slide_dir.mkdir(parents=True)
        (slide_dir / "slide.md").write_text("Original package", encoding="utf-8")
        (slide_dir / "context.md").write_text("Original context", encoding="utf-8")
    before = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}
    with pytest.raises(SystemExit) as exc:
        run_builder(monkeypatch, output, slide_type, *flags, "--force")
    assert error in str(exc.value) + capsys.readouterr().err
    after = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}
    assert before == after
    assert output.exists() is existing


@pytest.mark.parametrize("field", ["script", "passage", "context"])
@pytest.mark.parametrize("content", [b" \n\t", b"\xff", None])
def test_builder_rejects_blank_unreadable_or_missing_source_files(
    tmp_path, monkeypatch, field, content
):
    source = tmp_path / "source.md"
    if content is not None:
        source.write_bytes(content)
    output = tmp_path / "slides"
    slide_type = "conversation" if field == "context" else "narration"
    flags = [f"--{field}-file", str(source)]
    if field == "context":
        flags += ["--intent", "Explain.", "--turns", "2"]
    with pytest.raises(SystemExit, match="non-blank Markdown|cannot read"):
        run_builder(monkeypatch, output, slide_type, *flags)
    assert not output.exists()


@pytest.mark.parametrize("field", ["script", "passage", "context"])
def test_builder_rejects_both_text_and_file(tmp_path, monkeypatch, capsys, field):
    output = tmp_path / "slides"
    slide_type = "conversation" if field == "context" else "narration"
    with pytest.raises(SystemExit):
        run_builder(monkeypatch, output, slide_type, f"--{field}-text", "Roots.", f"--{field}-file", "source.md")
    assert "not allowed with argument" in capsys.readouterr().err
    assert not output.exists()


@pytest.mark.parametrize("slide_type", ["narration", "conversation"])
@pytest.mark.parametrize("flag", ["--answer", "--accept", "--choice", "--hint"])
def test_builder_new_types_reject_question_only_flags(tmp_path, monkeypatch, slide_type, flag):
    output = tmp_path / "slides"
    with pytest.raises(SystemExit, match="slides do not use"):
        run_builder(monkeypatch, output, slide_type, flag, "Unused")
    assert not output.exists()


@pytest.mark.parametrize("slide_type", ["narration", "conversation"])
def test_builder_new_types_require_force_to_overwrite(tmp_path, monkeypatch, slide_type):
    output = tmp_path / "slides"
    flags = (
        ["--script-text", "Roots absorb water."] if slide_type == "narration" else
        ["--context-text", "Roots absorb water.", "--intent", "Explain.", "--turns", "2"]
    )
    assert run_builder(monkeypatch, output, slide_type, *flags) == 0
    slide_md = output / "example-slide" / "slide.md"
    original = slide_md.read_bytes()
    with pytest.raises(SystemExit, match="already exists; pass --force"):
        run_builder(monkeypatch, output, slide_type, *flags, "--question", "Tell me more.")
    assert slide_md.read_bytes() == original
    assert run_builder(monkeypatch, output, slide_type, *flags, "--question", "Tell me more.", "--force") == 0
    assert slide_md.read_text().endswith("\n\nTell me more.\n")
