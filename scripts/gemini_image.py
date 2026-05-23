#!/usr/bin/env python3
"""Generate an image via Gemini / Imagen and save to disk.

Usage:
    gemini_image.py --prompt "..." --out PATH [--size 1K|2K|4K]
                    [--aspect-ratio 1:1|4:3|3:4|16:9|9:16]
                    [--model MODEL_ID]

Reads GEMINI_API_KEY from the environment.

Size routing:
    1K, 2K  -> imagen-4.0-generate-001 (generate_images)
    4K      -> gemini-3-pro-image-preview (generate_content, IMAGE modality)

Prints the absolute output path on success; nonzero exit on failure.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


IMAGEN_MODEL = "imagen-4.0-generate-001"
GEMINI_3_PRO_IMAGE = "gemini-3-pro-image-preview"


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
    out_path.write_bytes(images[0].image.image_bytes)


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
                out_path.write_bytes(blob.data)
                return
    raise RuntimeError(
        "No inline image data in response. Possible causes: policy violation, invalid prompt, rate limit."
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--prompt", required=True, help="Prompt. Do not ask for text in the image.")
    p.add_argument("--out", required=True, help="Output file path (.png).")
    p.add_argument(
        "--size",
        default="1K",
        choices=["1K", "2K", "4K"],
        help="Output size. 4K routes to Gemini 3 Pro preview; others to Imagen 4.",
    )
    p.add_argument(
        "--aspect-ratio",
        default="1:1",
        help="Aspect ratio (e.g. 1:1, 4:3, 3:4, 16:9, 9:16).",
    )
    p.add_argument(
        "--model",
        default=None,
        help="Override model id. If it starts with 'imagen-', uses generate_images; else generate_content.",
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

    if args.model:
        model = args.model
    elif args.size == "4K":
        model = GEMINI_3_PRO_IMAGE
    else:
        model = IMAGEN_MODEL

    client = genai.Client(api_key=api_key)

    try:
        if model.startswith("imagen-"):
            _imagen(client, model, args.prompt, args.size, args.aspect_ratio, out_path)
        else:
            _gemini_content_image(
                client, model, args.prompt, args.aspect_ratio, out_path, size=args.size
            )
    except Exception as exc:
        print(f"Image generation failed: {exc}", file=sys.stderr)
        return 1

    print(str(out_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
