#!/usr/bin/env python3
"""Download one web recording as an MP3 using the project's yt-dlp dependency."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse


def validate_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("recording URL must be an HTTP or HTTPS URL")
    return value


def validate_stem(value: str) -> str:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,119}", value):
        raise ValueError("output stem must contain only lowercase letters, digits, and hyphens")
    return value


def default_ydl_factory(options: dict[str, Any]):
    try:
        import yt_dlp
    except ImportError as exc:
        raise RuntimeError(
            "yt-dlp is not installed; rebuild/install the shared project dependencies"
        ) from exc
    return yt_dlp.YoutubeDL(options)


def is_youtube_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host == "youtu.be" or host == "youtube.com" or host.endswith(".youtube.com")


def extract_with_options(
    *,
    url: str,
    options: dict[str, Any],
    ydl_factory: Callable[[dict[str, Any]], Any],
) -> dict[str, Any]:
    with ydl_factory(options) as downloader:
        info = downloader.extract_info(url, download=True)
    if not isinstance(info, dict):
        raise RuntimeError("yt-dlp returned no recording metadata")
    return info


def download_audio(
    *,
    url: str,
    output_dir: Path,
    stem: str,
    ydl_factory: Callable[[dict[str, Any]], Any] = default_ydl_factory,
) -> dict[str, Any]:
    validate_url(url)
    validate_stem(stem)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(output_dir / f"{stem}.%(ext)s")
    options: dict[str, Any] = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "ignoreconfig": True,
        "outtmpl": output_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }
    strategy = "default"
    try:
        info = extract_with_options(
            url=url, options=options, ydl_factory=ydl_factory
        )
    except Exception:
        if not is_youtube_url(url):
            raise
        fallback_options = dict(options)
        fallback_options.update(
            {
                "format": "18/bestaudio/best",
                "extractor_args": {
                    "youtube": {"player_client": ["android", "web"]}
                },
            }
        )
        info = extract_with_options(
            url=url, options=fallback_options, ydl_factory=ydl_factory
        )
        strategy = "youtube-player-client-fallback"
    output_path = output_dir / f"{stem}.mp3"
    if not output_path.is_file():
        raise RuntimeError(f"yt-dlp did not create the expected MP3: {output_path}")
    source_url = str(info.get("webpage_url") or info.get("original_url") or url)
    return {
        "ok": True,
        "path": str(output_path),
        "source_url": source_url,
        "title": str(info.get("title") or ""),
        "performer": str(info.get("uploader") or info.get("channel") or ""),
        "duration": info.get("duration"),
        "extractor": str(info.get("extractor_key") or info.get("extractor") or ""),
        "recording_id": str(info.get("id") or ""),
        "download_strategy": strategy,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--stem", required=True)
    args = parser.parse_args()
    print(json.dumps(download_audio(url=args.url, output_dir=args.output_dir, stem=args.stem), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
