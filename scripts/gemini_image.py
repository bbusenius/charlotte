#!/usr/bin/env python3
"""Generate an image via Gemini / Imagen and save to disk.

Usage:
    gemini_image.py --prompt "..." --out PATH --model MODEL_ID [--size 1K|2K|4K]
                    [--aspect-ratio 1:1|4:3|3:4|16:9|9:16]
                    [--api auto|generate-content|generate-images]

Reads GEMINI_API_KEY from the environment.

Prints the absolute output path on success; nonzero exit on failure. If the
provider returns a different image format than the requested extension, the
saved path is adjusted to match the image bytes.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def image_extension(image_bytes: bytes) -> str | None:
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return ".webp"
    return None


def write_image_bytes(image_bytes: bytes, out_path: Path) -> Path:
    actual_ext = image_extension(image_bytes)
    actual_path = out_path
    if actual_ext and out_path.suffix.lower() != actual_ext:
        actual_path = out_path.with_suffix(actual_ext)
    actual_path.write_bytes(image_bytes)
    if actual_path != out_path and out_path.exists():
        out_path.unlink()
    return actual_path


def _imagen(client, model, prompt, size, aspect_ratio, out_path):
    from google.genai import types

    config = types.GenerateImagesConfig(
        number_of_images=1,
        aspect_ratio=aspect_ratio,
        image_size=size,
    )
    response = client.models.generate_images(
        model=model, prompt=prompt, config=config
    )
    images = getattr(response, "generated_images", None) or []
    if not images:
        raise RuntimeError(
            "No images returned. Possible causes: policy violation, invalid prompt, rate limit."
        )
    return write_image_bytes(images[0].image.image_bytes, out_path)


def _gemini_content_image(client, model, prompt, aspect_ratio, out_path, size="4K"):
    from google.genai import types

    config = types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=types.ImageConfig(
            aspect_ratio=aspect_ratio,
            image_size=size,
        ),
    )
    response = client.models.generate_content(
        model=model, contents=prompt, config=config
    )
    for cand in getattr(response, "candidates", []) or []:
        parts = getattr(getattr(cand, "content", None), "parts", []) or []
        for part in parts:
            blob = getattr(part, "inline_data", None)
            if blob and getattr(blob, "data", None):
                return write_image_bytes(blob.data, out_path)
    raise RuntimeError(
        "No inline image data in response. Possible causes: policy violation, invalid prompt, rate limit."
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--prompt", required=True, help="Prompt.")
    p.add_argument("--out", required=True, help="Requested output file path.")
    p.add_argument(
        "--size",
        default="1K",
        choices=["1K", "2K", "4K"],
        help="Requested output size.",
    )
    p.add_argument(
        "--aspect-ratio",
        default="1:1",
        help="Aspect ratio (e.g. 1:1, 4:3, 3:4, 16:9, 9:16).",
    )
    p.add_argument(
        "--model",
        required=True,
        help="Google model id.",
    )
    p.add_argument(
        "--api",
        default="auto",
        choices=["auto", "generate-content", "generate-images"],
        help=(
            "Google API method. Auto uses generate_images for imagen-* models "
            "and generate_content otherwise."
        ),
    )
    args = p.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY is not set in the environment.", file=sys.stderr)
        return 2

    try:
        from google import genai
    except ImportError as exc:
        print(f"google-genai is not installed: {exc}", file=sys.stderr)
        return 2

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    client = genai.Client(api_key=api_key)
    api = args.api
    if api == "auto":
        api = (
            "generate-images"
            if args.model.startswith("imagen-")
            else "generate-content"
        )

    try:
        if api == "generate-images":
            actual_path = _imagen(
                client, args.model, args.prompt, args.size, args.aspect_ratio, out_path
            )
        else:
            actual_path = _gemini_content_image(
                client, args.model, args.prompt, args.aspect_ratio, out_path, size=args.size
            )
    except Exception as exc:
        print(f"Image generation failed: {exc}", file=sys.stderr)
        return 1

    print(str(actual_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
