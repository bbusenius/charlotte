from __future__ import annotations

import importlib.util
from pathlib import Path


def load_charlotte_image_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "charlotte_image.py"
    spec = importlib.util.spec_from_file_location("charlotte_image", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_mason_prompt_uses_short_router_summary_without_examples():
    image = load_charlotte_image_module()

    prompt = image.prompt_with_mason_aesthetics("A snake fighting an Eagle")

    assert prompt.startswith(
        "Primary subject, must be followed exactly: A snake fighting an Eagle"
    )
    assert prompt.endswith("Render this exact subject: A snake fighting an Eagle")
    assert "natural-history illustration" in prompt
    assert "watercolor wash with ink linework" in prompt
    assert "No text or labels unless explicitly requested." in prompt

    # Keep example subjects and named-artist examples out of provider prompts.
    assert "Beatrix Potter" not in prompt
    assert "quetzal" not in prompt
    assert "monarch butterfly" not in prompt
    assert "milkweed" not in prompt
    assert "Prompt construction example" not in prompt


def test_write_image_bytes_returns_actual_extension(tmp_path):
    image = load_charlotte_image_module()
    requested = tmp_path / "image.png"
    jpeg_bytes = b"\xff\xd8\xff\xe0fake-jpeg"

    actual = image.write_image_bytes(jpeg_bytes, requested)

    assert actual == tmp_path / "image.jpg"
    assert actual.read_bytes() == jpeg_bytes
    assert not requested.exists()


def test_strict_preference_filters_routes():
    image = load_charlotte_image_module()
    config = {
        "capabilities": {
            "image_generation": {
                "routes": [
                    {"preference": "subscription", "source": "nanogpt"},
                    {"preference": "gemini", "source": "google"},
                    {"preference": "grok", "source": "xai"},
                ]
            }
        }
    }

    routes = image.image_routes(
        config, preference="gemini", strict=True, only_source=None
    )

    assert routes == [{"preference": "gemini", "source": "google"}]


def test_main_returns_2_when_only_runtime_fallback_is_available(monkeypatch, tmp_path):
    image = load_charlotte_image_module()
    config = {
        "capabilities": {
            "image_generation": {
                "routes": [
                    {"preference": "runtime", "source": "agent"},
                ]
            }
        }
    }

    monkeypatch.setenv("CHARLOTTE_IMAGE_DISABLE_DOTENV", "1")
    monkeypatch.setattr(image, "load_runtime_config", lambda: config)
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
        "capabilities": {
            "image_generation": {
                "routes": [
                    {"preference": "gemini", "source": "google"},
                    {"preference": "runtime", "source": "agent"},
                ]
            }
        }
    }

    def fake_run_route(route, prompt, out, size, aspect_ratio):
        if route["source"] == "google":
            raise image.ProviderFailed("backend exploded")
        raise image.ProviderUnavailable("runtime fallback is not script-callable")

    monkeypatch.setenv("CHARLOTTE_IMAGE_DISABLE_DOTENV", "1")
    monkeypatch.setattr(image, "load_runtime_config", lambda: config)
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
