"""Direct Google Gemini image generation through Charlotte's image router.

This provider runs inside Hermes's trusted process, where provider credentials
remain available. It delegates prompt construction, pedagogy aesthetics, route
selection, file handling, and provenance to ``charlotte_image.py``.
"""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.image_gen_provider import (
    DEFAULT_ASPECT_RATIO,
    ImageGenProvider,
    error_response,
    normalize_reference_images,
    resolve_aspect_ratio,
    success_response,
)


_ASPECT_RATIOS = {
    "landscape": "16:9",
    "square": "1:1",
    "portrait": "9:16",
}
_ROUTES = ("quality", "fast")


def _workspace_root() -> Path:
    configured = os.environ.get("CHARLOTTE_WORKSPACE", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    workspace = Path("/workspace")
    if workspace.is_dir():
        return workspace
    return Path.cwd().resolve()


def _python_path(workspace: Path) -> Path:
    configured = os.environ.get("CHARLOTTE_PYTHON", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return workspace / ".venv" / "bin" / "python"


def _cache_dir() -> Path:
    from hermes_constants import get_hermes_home

    path = get_hermes_home() / "cache" / "images"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _parse_router_result(stdout: str) -> Dict[str, Any]:
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("Charlotte image router did not return JSON")


class GeminiImageGenProvider(ImageGenProvider):
    """Gemini image backend using Charlotte's configured Google routes."""

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def display_name(self) -> str:
        return "Google Gemini (Charlotte)"

    def is_available(self) -> bool:
        workspace = _workspace_root()
        return bool(
            (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
            and _python_path(workspace).is_file()
            and (workspace / "scripts" / "charlotte_image.py").is_file()
            and (workspace / "image-generation.yaml").is_file()
        )

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "quality",
                "display": "Charlotte quality route",
                "strengths": "Full configured pedagogy aesthetics",
            },
            {
                "id": "fast",
                "display": "Charlotte fast route",
                "strengths": "Compact configured pedagogy aesthetics",
            },
        ]

    def default_model(self) -> str:
        return "quality"

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": self.display_name,
            "badge": "direct",
            "tag": "Direct Google image generation through Charlotte's configured router",
            "env_vars": [
                {
                    "key": "GEMINI_API_KEY",
                    "prompt": "Google AI Studio / Gemini API key",
                    "url": "https://aistudio.google.com/app/apikey",
                }
            ],
        }

    def capabilities(self) -> Dict[str, Any]:
        return {"modalities": ["text"], "max_reference_images": 0}

    def generate(
        self,
        prompt: str,
        aspect_ratio: str = DEFAULT_ASPECT_RATIO,
        *,
        image_url: Optional[str] = None,
        reference_image_urls: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        provider = self.name
        aspect = resolve_aspect_ratio(aspect_ratio)
        requested_route = str(kwargs.get("model") or self.default_model()).strip()
        if requested_route not in _ROUTES:
            return error_response(
                error=(
                    f"Unsupported Charlotte image route {requested_route!r}; "
                    f"choose one of {', '.join(_ROUTES)}"
                ),
                error_type="invalid_model",
                provider=provider,
                model=requested_route,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        refs = normalize_reference_images(reference_image_urls)
        if (isinstance(image_url, str) and image_url.strip()) or refs:
            return error_response(
                error="The direct Charlotte Gemini provider is text-to-image only",
                error_type="modality_unsupported",
                provider=provider,
                model=requested_route,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        api_key = (
            os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
            or ""
        ).strip()
        if not api_key:
            return error_response(
                error="GEMINI_API_KEY or GOOGLE_API_KEY is not configured",
                error_type="missing_api_key",
                provider=provider,
                model=requested_route,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        workspace = _workspace_root()
        python = _python_path(workspace)
        router = workspace / "scripts" / "charlotte_image.py"
        if not python.is_file() or not router.is_file():
            return error_response(
                error="Charlotte image router is not installed in the Hermes workspace",
                error_type="router_unavailable",
                provider=provider,
                model=requested_route,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        out = _cache_dir() / f"charlotte_gemini_{uuid.uuid4().hex}.png"
        command = [
            str(python),
            str(router),
            "--prompt",
            prompt,
            "--out",
            str(out),
            "--size",
            "1K",
            "--aspect-ratio",
            _ASPECT_RATIOS[aspect],
            "--kind",
            "slide-background",
            "--route",
            requested_route,
            "--json",
        ]
        child_env = os.environ.copy()
        child_env["GEMINI_API_KEY"] = api_key

        try:
            completed = subprocess.run(
                command,
                cwd=workspace,
                env=child_env,
                text=True,
                capture_output=True,
                timeout=300,
                check=False,
            )
        except Exception as exc:
            return error_response(
                error=f"Charlotte image router could not run: {exc}",
                error_type=type(exc).__name__,
                provider=provider,
                model=requested_route,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()
            error_type = {
                2: "provider_unavailable",
                3: "policy_rejected",
            }.get(completed.returncode, "provider_error")
            return error_response(
                error=detail or f"Charlotte image router exited {completed.returncode}",
                error_type=error_type,
                provider=provider,
                model=requested_route,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        try:
            result = _parse_router_result(completed.stdout)
            actual_path = Path(str(result["path"])).expanduser().resolve()
        except (KeyError, TypeError, ValueError) as exc:
            return error_response(
                error=f"Invalid Charlotte image router result: {exc}",
                error_type="provider_contract",
                provider=provider,
                model=requested_route,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        expected_prompt_mode = "compact" if requested_route == "fast" else "full"
        if (
            result.get("route") != requested_route
            or result.get("source") != "google"
            or result.get("prompt_mode") != expected_prompt_mode
        ):
            return error_response(
                error=(
                    "Charlotte image route verification failed: expected "
                    f"route={requested_route}, source=google, "
                    f"prompt_mode={expected_prompt_mode}"
                ),
                error_type="route_mismatch",
                provider=provider,
                model=str(result.get("model") or requested_route),
                prompt=prompt,
                aspect_ratio=aspect,
            )
        if not actual_path.is_file() or actual_path.parent != out.parent:
            return error_response(
                error="Charlotte image router did not create the expected cache artifact",
                error_type="missing_output",
                provider=provider,
                model=str(result.get("model") or requested_route),
                prompt=prompt,
                aspect_ratio=aspect,
            )

        return success_response(
            image=str(actual_path),
            model=str(result.get("model") or requested_route),
            prompt=prompt,
            aspect_ratio=aspect,
            provider=provider,
            extra={
                "route": result["route"],
                "source": result["source"],
                "prompt_mode": result["prompt_mode"],
                "kind": result.get("kind", "slide-background"),
            },
        )


def register(ctx) -> None:
    ctx.register_image_gen_provider(GeminiImageGenProvider())
