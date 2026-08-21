from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path


def load_provider(monkeypatch, tmp_path):
    agent = types.ModuleType("agent")
    contract = types.ModuleType("agent.image_gen_provider")

    class ImageGenProvider:
        pass

    def response(success, **values):
        return {"success": success, **values}

    contract.DEFAULT_ASPECT_RATIO = "landscape"
    contract.ImageGenProvider = ImageGenProvider
    contract.error_response = lambda **values: response(False, image=None, **values)
    def success_response(**values):
        extra = values.pop("extra", {})
        return response(True, **values, **extra)

    contract.success_response = success_response
    contract.normalize_reference_images = lambda value: value or None
    contract.resolve_aspect_ratio = (
        lambda value: value
        if value in {"landscape", "square", "portrait"}
        else "landscape"
    )
    monkeypatch.setitem(sys.modules, "agent", agent)
    monkeypatch.setitem(sys.modules, "agent.image_gen_provider", contract)

    constants = types.ModuleType("hermes_constants")
    constants.get_hermes_home = lambda: tmp_path / "hermes"
    monkeypatch.setitem(sys.modules, "hermes_constants", constants)

    path = (
        Path(__file__).resolve().parents[1]
        / "runtime"
        / "hermes"
        / "plugins"
        / "image_gen"
        / "gemini"
        / "__init__.py"
    )
    spec = importlib.util.spec_from_file_location("charlotte_hermes_gemini", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def prepare_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    (workspace / ".venv" / "bin").mkdir(parents=True)
    (workspace / ".venv" / "bin" / "python").write_text("", encoding="utf-8")
    (workspace / "scripts").mkdir()
    (workspace / "scripts" / "charlotte_image.py").write_text("", encoding="utf-8")
    (workspace / "image-generation.yaml").write_text(
        "image_generation: {}\n", encoding="utf-8"
    )
    return workspace


def test_provider_requires_key_and_workspace(monkeypatch, tmp_path):
    module = load_provider(monkeypatch, tmp_path)
    workspace = prepare_workspace(tmp_path)
    monkeypatch.setenv("CHARLOTTE_WORKSPACE", str(workspace))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    assert module.GeminiImageGenProvider().is_available() is False

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    assert module.GeminiImageGenProvider().is_available() is True


def test_provider_runs_quality_route_and_verifies_provenance(monkeypatch, tmp_path):
    module = load_provider(monkeypatch, tmp_path)
    workspace = prepare_workspace(tmp_path)
    monkeypatch.setenv("CHARLOTTE_WORKSPACE", str(workspace))
    monkeypatch.setenv("GOOGLE_API_KEY", "google-test-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    observed = {}

    def fake_run(command, **kwargs):
        observed["command"] = command
        observed["env"] = kwargs["env"]
        out = Path(command[command.index("--out") + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"\x89PNG\r\n\x1a\n")
        payload = {
            "path": str(out),
            "route": "quality",
            "source": "google",
            "model": "gemini-3-pro-image-preview",
            "prompt_mode": "full",
            "kind": "slide-background",
        }
        return types.SimpleNamespace(
            returncode=0, stdout=json.dumps(payload), stderr=""
        )

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    result = module.GeminiImageGenProvider().generate(
        "A quiet watercolor landscape",
        aspect_ratio="landscape",
        model="quality",
    )

    assert result["success"] is True
    assert result["provider"] == "gemini"
    assert result["model"] == "gemini-3-pro-image-preview"
    assert result["route"] == "quality"
    assert result["source"] == "google"
    assert result["prompt_mode"] == "full"
    assert observed["env"]["GEMINI_API_KEY"] == "google-test-key"
    assert observed["command"][observed["command"].index("--route") + 1] == "quality"
    assert (
        observed["command"][observed["command"].index("--aspect-ratio") + 1]
        == "16:9"
    )


def test_provider_fails_closed_on_wrong_route(monkeypatch, tmp_path):
    module = load_provider(monkeypatch, tmp_path)
    workspace = prepare_workspace(tmp_path)
    monkeypatch.setenv("CHARLOTTE_WORKSPACE", str(workspace))
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def fake_run(command, **kwargs):
        out = Path(command[command.index("--out") + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"\x89PNG\r\n\x1a\n")
        payload = {
            "path": str(out),
            "route": "quality",
            "source": "nanogpt",
            "model": "hidream",
            "prompt_mode": "none",
        }
        return types.SimpleNamespace(
            returncode=0, stdout=json.dumps(payload), stderr=""
        )

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    result = module.GeminiImageGenProvider().generate("A landscape", model="quality")

    assert result["success"] is False
    assert result["error_type"] == "route_mismatch"


def test_provider_rejects_image_editing(monkeypatch, tmp_path):
    module = load_provider(monkeypatch, tmp_path)
    result = module.GeminiImageGenProvider().generate(
        "Edit this",
        image_url="/tmp/source.png",
    )

    assert result["success"] is False
    assert result["error_type"] == "modality_unsupported"
