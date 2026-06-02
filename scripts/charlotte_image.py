#!/usr/bin/env python3
"""Generate an image through routes configured in image-generation.yaml.

Skills describe the image job and this router resolves the configured route,
builds the Charlotte prompt, and calls the configured provider.

Exit codes:
  0  success
  1  configured providers were called but failed
  2  no configured script-callable provider was available
  3  a provider rejected the prompt for policy/safety reasons; do not fallback
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import requests
import yaml


class ProviderUnavailable(Exception):
    pass


class ProviderFailed(Exception):
    pass


class PolicyRejected(Exception):
    pass


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_dotenv() -> None:
    if os.environ.get("CHARLOTTE_IMAGE_DISABLE_DOTENV"):
        return
    path = repo_root() / ".env"
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip().strip('"').strip("'")
        os.environ[key] = value


def load_image_config() -> dict[str, Any]:
    configured = os.environ.get("CHARLOTTE_IMAGE_CONFIG")
    path = (
        Path(configured).expanduser()
        if configured
        else repo_root() / "image-generation.yaml"
    )
    if not path.is_absolute():
        path = repo_root() / path
    if not path.exists():
        raise ProviderUnavailable(f"image generation config not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        loaded = yaml.safe_load(fh) or {}
    if not isinstance(loaded, dict):
        raise ProviderUnavailable(f"{path} must contain a YAML mapping")
    return loaded


def env_value(route: dict[str, Any], key: str) -> str | None:
    direct = route.get(key)
    if direct:
        return str(direct)
    env_key = route.get(f"{key}_env")
    if env_key:
        return os.environ.get(str(env_key)) or None
    return None


def configured_route(
    config: dict[str, Any], route_name: str | None, only_source: str | None
) -> tuple[str, dict[str, Any]]:
    image_config = config.get("image_generation", {})
    if not isinstance(image_config, dict):
        raise ProviderUnavailable("image_generation must be a YAML mapping")

    routes = image_config.get("routes", {})
    if not isinstance(routes, dict):
        raise ProviderUnavailable("image_generation.routes must be a YAML mapping")

    selected_name = route_name or str(image_config.get("default_route", "")).strip()
    if not selected_name:
        raise ProviderUnavailable("image_generation.default_route is not configured")
    route = routes.get(selected_name)
    if not isinstance(route, dict):
        raise ProviderUnavailable(f"image route {selected_name!r} is not configured")
    if only_source and str(route.get("source", "")).strip() != only_source:
        raise ProviderUnavailable(
            f"image route {selected_name!r} does not use source {only_source!r}"
        )
    return selected_name, dict(route)


def output_path(path: str) -> Path:
    out = Path(path).expanduser()
    if not out.is_absolute():
        out = repo_root() / out
    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


def openai_size(size: str, aspect_ratio: str) -> str:
    if aspect_ratio == "16:9":
        return "1792x1024"
    if aspect_ratio == "9:16":
        return "1024x1792"
    if size == "2K":
        return "2048x2048"
    return "1024x1024"


def is_policy_message(message: str) -> bool:
    lowered = message.lower()
    return any(
        word in lowered
        for word in (
            "policy",
            "safety",
            "unsafe",
            "disallowed",
            "prohibited",
            "moderation",
        )
    )


def image_extension(image_bytes: bytes) -> str | None:
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return ".webp"
    return None


def write_image_bytes(image_bytes: bytes, out: Path) -> Path:
    actual_ext = image_extension(image_bytes)
    actual_out = out
    if actual_ext and out.suffix.lower() != actual_ext:
        actual_out = out.with_suffix(actual_ext)
    actual_out.write_bytes(image_bytes)
    return actual_out


def markdown_section(text: str, heading: str) -> str:
    lines = text.splitlines()
    start: int | None = None
    heading_level = 0

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == heading:
            start = index
            heading_level = len(stripped) - len(stripped.lstrip("#"))
            break

    if start is None:
        raise ProviderUnavailable(f"Could not find {heading!r} in mason-aesthetics")

    end = len(lines)
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()
        if not stripped.startswith("#"):
            continue
        level = len(stripped) - len(stripped.lstrip("#"))
        if level <= heading_level:
            end = index
            break

    return "\n".join(lines[start:end]).strip()


def mason_aesthetics_path() -> Path:
    path = repo_root() / "skills" / "mason-aesthetics" / "SKILL.md"
    if not path.exists():
        raise ProviderUnavailable("skills/mason-aesthetics/SKILL.md is not available")
    return path


def mason_compact_guidance() -> str:
    text = mason_aesthetics_path().read_text(encoding="utf-8")
    section = markdown_section(text, "#### Image-router summary")
    return "\n".join(section.splitlines()[1:]).strip()


def mason_full_guidance() -> str:
    text = mason_aesthetics_path().read_text(encoding="utf-8")
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                return "\n".join(lines[index + 1 :]).strip()
    return text.strip()


def prompt_mode_for_route(route_name: str, override: str) -> str:
    if override != "auto":
        return override
    if route_name == "fast":
        return "compact"
    return "full"


def prompt_with_mason_aesthetics(prompt: str, kind: str, mode: str) -> str:
    if mode == "none":
        return prompt
    if mode == "compact":
        guidance = mason_compact_guidance()
    elif mode == "full":
        guidance = mason_full_guidance()
    else:
        raise ProviderUnavailable(f"unknown prompt mode: {mode}")
    return (
        f"Image request kind: {kind}\n\n"
        f"Primary request, must be followed exactly:\n{prompt}\n\n"
        f"Charlotte aesthetic profile:\n{guidance}\n\n"
        f"Render this exact request:\n{prompt}"
    )


def result_base(
    route_name: str,
    route: dict[str, Any],
    kind: str,
    prompt_mode: str,
) -> dict[str, str]:
    return {
        "route": route_name,
        "kind": kind,
        "prompt_mode": prompt_mode,
        "source": str(route.get("source", "")),
        "model": env_value(route, "model") or "",
    }


def write_image_response(data: dict[str, Any], out: Path) -> Path:
    images = data.get("data")
    if not images:
        raise ProviderFailed("response did not include image data")

    image = images[0]
    if image.get("b64_json"):
        return write_image_bytes(base64.b64decode(image["b64_json"]), out)

    if image.get("url"):
        response = requests.get(image["url"], timeout=180)
        response.raise_for_status()
        return write_image_bytes(response.content, out)

    raise ProviderFailed("response did not include b64_json or url")


def run_openai_image(
    route: dict[str, Any], prompt: str, out: Path, size: str, aspect_ratio: str
) -> dict[str, str]:
    api_key = env_value(route, "api_key")
    if not api_key:
        raise ProviderUnavailable("API key is not configured")

    base_url = env_value(route, "base_url")
    if not base_url:
        raise ProviderUnavailable("base_url is not configured")

    model = env_value(route, "model")
    if not model:
        raise ProviderUnavailable("model is not configured")

    response = requests.post(
        base_url.rstrip("/") + "/images/generations",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": openai_size(size, aspect_ratio),
            "response_format": "b64_json",
        },
        timeout=240,
    )

    if response.status_code >= 400:
        message = response.text[:1500]
        if is_policy_message(message):
            raise PolicyRejected(message)
        if response.status_code in {401, 403, 404}:
            raise ProviderUnavailable(f"HTTP {response.status_code}: {message}")
        raise ProviderFailed(f"HTTP {response.status_code}: {message}")

    actual_out = write_image_response(response.json(), out)
    return {"source": str(route.get("source")), "model": model, "path": str(actual_out)}


def run_nanogpt_subscription_image(
    route: dict[str, Any], prompt: str, out: Path, size: str, aspect_ratio: str
) -> dict[str, str]:
    api_key = env_value(route, "api_key")
    if not api_key:
        raise ProviderUnavailable("API key is not configured")

    endpoint = env_value(route, "endpoint") or "https://nano-gpt.com/api/generate-image"
    model = env_value(route, "model")
    if not model:
        raise ProviderUnavailable("model is not configured")

    pixel_size = 2048 if size == "2K" else 1024
    if aspect_ratio == "16:9":
        width, height = 1792, 1024
    elif aspect_ratio == "9:16":
        width, height = 1024, 1792
    else:
        width = height = pixel_size

    response = requests.post(
        endpoint,
        headers={
            "x-api-key": api_key,
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "prompt": prompt,
            "nImages": 1,
            "width": width,
            "height": height,
            "resolution": f"{width}x{height}",
        },
        timeout=240,
    )

    if response.status_code >= 400:
        message = response.text[:1500]
        if is_policy_message(message):
            raise PolicyRejected(message)
        if response.status_code in {401, 403, 404, 402}:
            raise ProviderUnavailable(f"HTTP {response.status_code}: {message}")
        raise ProviderFailed(f"HTTP {response.status_code}: {message}")

    actual_out = write_image_response(response.json(), out)
    return {"source": str(route.get("source")), "model": model, "path": str(actual_out)}


def run_google(
    route: dict[str, Any], prompt: str, out: Path, size: str, aspect_ratio: str
) -> dict[str, str]:
    api_key = os.environ.get(str(route.get("api_key_env", "GEMINI_API_KEY")))
    if not api_key:
        raise ProviderUnavailable("GEMINI_API_KEY is not set")
    model = env_value(route, "model")
    if not model:
        raise ProviderUnavailable("model is not configured")

    cmd = [
        sys.executable,
        str(repo_root() / "scripts" / "gemini_image.py"),
        "--prompt",
        prompt,
        "--out",
        str(out),
        "--size",
        size,
        "--aspect-ratio",
        aspect_ratio,
        "--model",
        model,
    ]
    api = env_value(route, "api")
    if api:
        cmd.extend(["--api", api])

    result = subprocess.run(cmd, cwd=repo_root(), text=True, capture_output=True)
    if result.returncode == 0:
        actual_path = (result.stdout or "").strip().splitlines()[-1:] or [str(out)]
        return {
            "source": "google",
            "model": model,
            "path": actual_path[0],
        }

    message = (result.stderr or result.stdout or "").strip()
    if result.returncode == 2:
        raise ProviderUnavailable(message or "Google/Gemini backend is unavailable")
    if is_policy_message(message):
        raise PolicyRejected(message)
    raise ProviderFailed(message or f"Google/Gemini backend exited {result.returncode}")


def run_route(
    route: dict[str, Any], prompt: str, out: Path, size: str, aspect_ratio: str
) -> dict[str, str]:
    source = str(route.get("source", "")).strip()
    api_mode = str(route.get("api_mode", "")).strip()
    if source == "nanogpt" and api_mode == "subscription_images":
        return run_nanogpt_subscription_image(route, prompt, out, size, aspect_ratio)
    if source in {"nanogpt", "xai", "openai_compatible"}:
        return run_openai_image(route, prompt, out, size, aspect_ratio)
    if source == "google":
        return run_google(route, prompt, out, size, aspect_ratio)
    if source in {"agent", "runtime"}:
        raise ProviderUnavailable(
            "runtime-native image tools are not callable from this script"
        )
    raise ProviderUnavailable(f"unknown image source: {source or '<missing>'}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--size", default="1K", choices=["1K", "2K", "4K"])
    parser.add_argument("--aspect-ratio", default="1:1")
    parser.add_argument(
        "--route",
        default=None,
        help="Named route from image-generation.yaml. Defaults to image_generation.default_route.",
    )
    parser.add_argument(
        "--kind",
        default="illustration",
        help="Image job kind, e.g. illustration, slide-background, diagram, or image-with-text.",
    )
    parser.add_argument(
        "--prompt-mode",
        choices=["auto", "full", "compact", "none"],
        default="auto",
        help="Mason prompt profile. Auto uses compact for the fast route and full otherwise.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve the route and print the final provider prompt without calling a provider or writing files.",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--only-source",
        default=None,
        help="Debug/testing aid: try only routes with this source name, e.g. nanogpt.",
    )
    args = parser.parse_args()
    load_dotenv()

    try:
        config = load_image_config()
        route_name, route = configured_route(config, args.route, args.only_source)
        prompt_mode = prompt_mode_for_route(route_name, args.prompt_mode)
    except ProviderUnavailable as exc:
        print(str(exc), file=sys.stderr)
        return 2

    try:
        prompt = prompt_with_mason_aesthetics(args.prompt, args.kind, prompt_mode)
    except ProviderUnavailable as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.dry_run:
        result = result_base(route_name, route, args.kind, prompt_mode)
        result.update(
            dry_run=True,
            requested_path=args.out,
            size=args.size,
            aspect_ratio=args.aspect_ratio,
            prompt_length=len(prompt),
            prompt=prompt,
        )
        if args.json:
            print(json.dumps(result, ensure_ascii=True))
        else:
            print(
                f"dry_run=true route={result['route']} source={result['source']} "
                f"model={result['model']} prompt_mode={result['prompt_mode']} "
                f"kind={result['kind']} size={result['size']} aspect_ratio={result['aspect_ratio']}"
            )
            print()
            print(prompt)
        return 0

    out = output_path(args.out)
    unavailable: list[str] = []
    failed: list[str] = []

    label = f"{route_name}/{route.get('source', '<missing>')}"
    try:
        metadata = run_route(route, prompt, out, args.size, args.aspect_ratio)
    except ProviderUnavailable as exc:
        unavailable.append(f"{label}: {exc}")
    except PolicyRejected as exc:
        print(f"Image prompt rejected by provider policy: {exc}", file=sys.stderr)
        return 3
    except Exception as exc:
        failed.append(f"{label}: {exc}")
    else:
        result = result_base(route_name, route, args.kind, prompt_mode)
        result.update(
            path=metadata.get("path", str(out)),
            source=metadata["source"],
            model=metadata["model"],
        )
        if args.json:
            result["unavailable"] = unavailable
            result["failed"] = failed
        if args.json:
            print(json.dumps(result, ensure_ascii=True))
        else:
            print(result["path"])
            print(
                f"provider={result['source']} route={result['route']} model={result['model']} prompt_mode={result['prompt_mode']}"
            )
        return 0

    if failed:
        print("Configured image providers failed:", file=sys.stderr)
        for item in failed:
            print(f"- {item}", file=sys.stderr)
        if unavailable:
            print("Unavailable image providers:", file=sys.stderr)
            for item in unavailable:
                print(f"- {item}", file=sys.stderr)
        return 1

    print("No configured script-callable image provider is available.", file=sys.stderr)
    for item in unavailable:
        print(f"- {item}", file=sys.stderr)
    print(
        "If the active agent runtime exposes an image tool, use it as the runtime fallback.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
