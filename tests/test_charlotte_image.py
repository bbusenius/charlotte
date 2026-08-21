from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_charlotte_image_module():
    module_path = ROOT / "scripts" / "charlotte_image.py"
    spec = importlib.util.spec_from_file_location("charlotte_image", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_project_instructions_make_configured_aesthetics_authoritative():
    instructions = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "For every Charlotte-backed image generation call" in instructions
    assert "standalone or inside any skill or workflow" in instructions
    assert "Do not invent medium, style adjectives, lighting, palette" in instructions
    assert "The configured `pedagogy.aesthetics` skill owns" in instructions


def test_compact_prompt_uses_short_router_summary_without_examples():
    image = load_charlotte_image_module()

    prompt = image.prompt_with_aesthetics(
        "A snake fighting an Eagle", "illustration", "compact"
    )

    assert "Primary request, must be followed exactly:\nA snake fighting an Eagle" in prompt
    assert prompt.endswith("Render this exact request:\nA snake fighting an Eagle")
    assert "natural-history illustration" in prompt
    assert "watercolor wash with ink linework" in prompt
    assert "No text or labels unless explicitly requested." in prompt

    # Keep example subjects and named-artist examples out of provider prompts.
    assert "Beatrix Potter" not in prompt
    assert "quetzal" not in prompt
    assert "monarch butterfly" not in prompt
    assert "milkweed" not in prompt
    assert "Prompt construction example" not in prompt


def test_prompt_mode_none_passes_prompt_through():
    image = load_charlotte_image_module()

    assert (
        image.prompt_with_aesthetics("oak leaf", "illustration", "none") == "oak leaf"
    )


def test_aesthetics_path_defaults_to_mason_skill():
    image = load_charlotte_image_module()

    path = image.aesthetics_path()

    assert path == image.repo_root() / "skills" / "mason-aesthetics" / "SKILL.md"


def test_aesthetics_path_honors_runtime_config(monkeypatch, tmp_path):
    image = load_charlotte_image_module()
    pack = tmp_path / "my-aesthetics"
    pack.mkdir()
    skill = pack / "SKILL.md"
    skill.write_text(
        "# My register\n\n"
        "#### Image-router summary\n\n"
        "Bold folk-art register with saturated color.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        image, "load_runtime_yaml", lambda: {"pedagogy": {"aesthetics": str(pack)}}
    )

    assert image.aesthetics_path() == skill

    prompt = image.prompt_with_aesthetics("oak leaf", "illustration", "compact")
    assert "Bold folk-art register with saturated color." in prompt


def test_aesthetics_file_without_router_summary_works_as_is(monkeypatch, tmp_path):
    """A ported aesthetics file needs no special sections: full mode uses the
    whole text, and compact mode falls back to the full text too so the
    user's register is never dropped on the fast route."""
    image = load_charlotte_image_module()
    skill = tmp_path / "my-register.md"
    skill.write_text(
        "# My register\n\nBold folk-art register with saturated color.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        image, "load_runtime_yaml", lambda: {"pedagogy": {"aesthetics": str(skill)}}
    )

    full = image.prompt_with_aesthetics("oak leaf", "illustration", "full")
    assert "Bold folk-art register with saturated color." in full

    assert image.aesthetics_compact_guidance() is None
    compact = image.prompt_with_aesthetics("oak leaf", "illustration", "compact")
    assert compact == full


def test_write_image_bytes_returns_actual_extension(tmp_path):
    image = load_charlotte_image_module()
    requested = tmp_path / "image.png"
    jpeg_bytes = b"\xff\xd8\xff\xe0fake-jpeg"

    actual = image.write_image_bytes(jpeg_bytes, requested)

    assert actual == tmp_path / "image.jpg"
    assert actual.read_bytes() == jpeg_bytes
    assert not requested.exists()


def test_configured_route_selects_named_route():
    image = load_charlotte_image_module()
    config = {
        "image_generation": {
            "default_route": "quality",
            "routes": {
                "quality": {"source": "google"},
                "fast": {"source": "nanogpt"},
            },
        }
    }

    name, route = image.configured_route(config, None, None)
    assert (name, route["source"]) == ("quality", "google")

    name, route = image.configured_route(config, "fast", None)
    assert (name, route["source"]) == ("fast", "nanogpt")


def test_configured_route_rejects_only_source_mismatch():
    image = load_charlotte_image_module()
    config = {
        "image_generation": {
            "default_route": "quality",
            "routes": {"quality": {"source": "google"}},
        }
    }

    try:
        image.configured_route(config, None, "nanogpt")
    except image.ProviderUnavailable:
        pass
    else:
        raise AssertionError("expected ProviderUnavailable")


def test_main_returns_2_when_only_runtime_fallback_is_available(monkeypatch, tmp_path):
    image = load_charlotte_image_module()
    config = {
        "image_generation": {
            "default_route": "quality",
            "routes": {"quality": {"source": "agent"}},
        }
    }

    monkeypatch.setenv("CHARLOTTE_IMAGE_DISABLE_DOTENV", "1")
    monkeypatch.setattr(image, "load_image_config", lambda: config)
    monkeypatch.setattr(image, "output_path", lambda _: tmp_path / "out.png")
    monkeypatch.setattr(
        image.sys,
        "argv",
        [
            "charlotte_image.py",
            "--prompt",
            "oak leaf",
            "--out",
            str(tmp_path / "out.png"),
        ],
    )

    assert image.main() == 2


def test_main_returns_1_when_configured_provider_fails(monkeypatch, tmp_path):
    image = load_charlotte_image_module()
    config = {
        "image_generation": {
            "default_route": "quality",
            "routes": {"quality": {"source": "google"}},
        }
    }

    def fake_run_route(route, prompt, out, size, aspect_ratio):
        raise image.ProviderFailed("backend exploded")

    monkeypatch.setenv("CHARLOTTE_IMAGE_DISABLE_DOTENV", "1")
    monkeypatch.setattr(image, "load_image_config", lambda: config)
    monkeypatch.setattr(image, "output_path", lambda _: tmp_path / "out.png")
    monkeypatch.setattr(image, "run_route", fake_run_route)
    monkeypatch.setattr(
        image.sys,
        "argv",
        [
            "charlotte_image.py",
            "--prompt",
            "oak leaf",
            "--out",
            str(tmp_path / "out.png"),
        ],
    )

    assert image.main() == 1
