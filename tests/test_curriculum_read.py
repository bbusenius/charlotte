from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def load_module():
    repo = Path(__file__).resolve().parents[1]
    scripts = repo / "scripts"
    sys.path.insert(0, str(scripts))
    try:
        spec = importlib.util.spec_from_file_location(
            "curriculum_read", scripts / "curriculum_read.py"
        )
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(scripts))


def test_composite_index_lists_native_components_and_roles(tmp_path):
    mod = load_module()
    root = tmp_path / "curricula"
    folder = root / "publisher" / "course"
    folder.mkdir(parents=True)
    (folder / "Course.pdf").write_bytes(b"%PDF-placeholder")
    (folder / "Reader.txt").write_text("Chapter 1", encoding="utf-8")
    index = folder / "anything.md"
    index.write_text(
        """---
id: example
components:
  - path: Course.pdf
    role: primary-lessons
  - path: Reader.txt
    role: reader
---
# Example

- [Course](Course.pdf)
- [Reader](Reader.txt)
""",
        encoding="utf-8",
    )

    metadata, components = mod.index_components(index, root)

    assert metadata["id"] == "example"
    assert [(item.path.name, item.role) for item in components] == [
        ("Course.pdf", "primary-lessons"),
        ("Reader.txt", "reader"),
    ]


def test_body_link_index_remains_supported(tmp_path):
    mod = load_module()
    root = tmp_path / "curricula"
    folder = root / "art" / "ao"
    study = folder / "artists" / "painting.md"
    study.parent.mkdir(parents=True)
    study.write_text("# Painting", encoding="utf-8")
    index = folder / "curriculum.md"
    index.write_text("# Studies\n- [Painting](artists/painting.md)\n", encoding="utf-8")

    _, components = mod.index_components(index, root)

    assert len(components) == 1
    assert components[0].path == study
    assert components[0].role == "linked-source"


def test_frontmatter_component_cannot_escape_curricula_root(tmp_path):
    mod = load_module()
    root = tmp_path / "curricula"
    folder = root / "course"
    folder.mkdir(parents=True)
    index = folder / "curriculum.md"
    index.write_text(
        "---\ncomponents:\n  - path: ../../outside.pdf\n---\n",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="escapes curricula_dir"):
        mod.index_components(index, root)


def test_navigation_links_outside_curricula_are_not_components(tmp_path):
    mod = load_module()
    root = tmp_path / "curricula"
    folder = root / "generated"
    folder.mkdir(parents=True)
    index = folder / "curriculum.md"
    index.write_text(
        "[Pedagogy](../../pedagogies/concept.md)\n",
        encoding="utf-8",
    )

    _, components = mod.index_components(index, root)

    assert components == [mod.Component(index, "primary-lessons", "curriculum")]


def test_temporary_normalization_finds_broken_spacing():
    mod = load_module()

    assert mod.text_matches("LESSO N   5", ["Lesson 5"])
    assert mod.text_matches("Lección\n5", ["Lección 5"])
    assert not mod.text_matches("Lesson 50", ["Lesson 5"])
    assert not mod.text_matches("Check this lesson" + " " * 80 + "5. Cut paper", ["Lesson 5"])


def test_markdown_search_returns_complete_heading_section(tmp_path):
    mod = load_module()
    source = tmp_path / "book.md"
    source.write_text(
        "# Book\n\n## Lesson 4\nOld\n\n## Lesson 5\nFirst\nSecond\n\n## Lesson 6\nNext\n",
        encoding="utf-8",
    )
    component = mod.Component(source, "primary-lessons")

    matches = mod.search_text(component, ["Lesson 5"], tmp_path)

    assert len(matches) == 1
    assert matches[0]["text"] == "## Lesson 5\nFirst\nSecond\n"


def test_section_lookup_finds_one_markdown_section(tmp_path):
    mod = load_module()
    lines = "# Book\n\n## Lesson 5\nFirst\nSecond\n\n## Lesson 6\nNext\n".splitlines()
    matched = [index for index, line in enumerate(lines) if mod.text_matches(line, ["Lesson 5"])]
    ranges = {mod._markdown_section(lines, index) for index in matched}

    assert ranges == {(2, 6)}


def test_pdf_search_returns_page_windows_without_persisting_text(tmp_path, monkeypatch):
    mod = load_module()
    source = tmp_path / "course.pdf"
    source.write_bytes(b"%PDF-placeholder")
    component = mod.Component(source, "primary-lessons")
    monkeypatch.setattr(
        mod,
        "extract_pdf_pages",
        lambda path: ["front matter", "LESSO N 5\nFirst page", "Second page", "Lesson 6"],
    )

    matches = mod.search_pdf(
        component,
        ["Lesson 5"],
        tmp_path,
        context_pages=1,
        max_results=12,
    )

    assert matches[0]["pdf_pages"] == [1, 3]
    assert matches[0]["matched_pdf_pages"] == [2]
    assert "LESSO N 5" in matches[0]["text"]


def test_source_path_accepts_reader_output_and_rejects_escape(tmp_path):
    mod = load_module()
    registry_dir = tmp_path
    curricula_dir = tmp_path / "curricula"
    curricula_dir.mkdir()
    source = curricula_dir / "course.pdf"
    source.write_bytes(b"%PDF-placeholder")

    assert mod._source_path(curricula_dir, registry_dir, "curricula/course.pdf") == source
    assert mod._source_path(curricula_dir, registry_dir, "course.pdf") == source
    with pytest.raises(SystemExit, match="escapes curricula_dir"):
        mod._source_path(curricula_dir, registry_dir, "../outside.pdf")


def test_missing_and_unsupported_components_are_reported(tmp_path):
    mod = load_module()
    registry_dir = tmp_path
    missing = mod.Component(tmp_path / "missing.pdf", "primary-lessons")
    unsupported_path = tmp_path / "deck.pptx"
    unsupported_path.write_bytes(b"placeholder")
    unsupported = mod.Component(unsupported_path, "slides")

    assert mod.component_record(missing, registry_dir)["exists"] is False
    assert mod.component_record(unsupported, registry_dir)["supported"] is False
