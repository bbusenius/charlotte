#!/usr/bin/env python3
"""Fetch a video's spoken text as JSON without downloading the video.

Used by the lesson-log skill so a watched video becomes a searchable account
of what was taught, not just a URL in a message. Prefers human captions, then
auto-captions. Leaves the video itself un-downloaded.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from typing import Any, Callable
from urllib.parse import urlparse


ENGLISH_LANGS = ("en", "en-US", "en-GB", "en-orig")
FORMAT_PREFERENCE = ("vtt", "srt", "json3", "ttml", "srv3", "srv2", "srv1")
TAG_RE = re.compile(r"</?[^>]+>")
CUE_META_RE = re.compile(
    r"\d{2}:\d{2}(?::\d{2})?[.,]\d{3}\s+-->\s+\d{2}:\d{2}(?::\d{2})?[.,]\d{3}"
)
XML_TEXT_RE = re.compile(r"<text\b[^>]*>(.*?)</text>", re.I | re.S)


def validate_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("video URL must be an HTTP or HTTPS URL")
    return value


def is_youtube_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host == "youtu.be" or host == "youtube.com" or host.endswith(".youtube.com")


def default_ydl_factory(options: dict[str, Any]):
    try:
        import yt_dlp
    except ImportError as exc:
        raise RuntimeError(
            "yt-dlp is not installed; rebuild/install the shared project dependencies"
        ) from exc
    return yt_dlp.YoutubeDL(options)


def extract_transcript_with_options(
    *,
    url: str,
    options: dict[str, Any],
    ydl_factory: Callable[[dict[str, Any]], Any],
    fetch: Callable[[Any, str], str],
) -> tuple[dict[str, Any], str | None, str | None, str]:
    with ydl_factory(options) as ydl:
        info = ydl.extract_info(url, download=False)
        if not isinstance(info, dict):
            raise RuntimeError("yt-dlp returned no video metadata")
        info = unwrap_info(info)
        formats, kind, language = pick_caption_source(info)
        transcript = ""
        if formats:
            transcript, _ext = read_caption_payload(ydl, formats, fetch)
        return info, kind, language, transcript


def unwrap_info(info: dict[str, Any]) -> dict[str, Any]:
    if info.get("_type") == "playlist":
        for entry in info.get("entries") or []:
            if isinstance(entry, dict):
                return entry
    return info


def collapse_caption_lines(lines: list[str]) -> str:
    collapsed: list[str] = []
    for line in lines:
        text = " ".join(line.split())
        if not text:
            continue
        if collapsed:
            prev = collapsed[-1]
            if text == prev:
                continue
            if text.startswith(prev) and len(text) > len(prev):
                collapsed[-1] = text
                continue
            if prev.startswith(text):
                continue
        collapsed.append(text)
    return " ".join(collapsed)


def json3_to_text(payload: str) -> str:
    data = json.loads(payload)
    lines: list[str] = []
    for event in data.get("events") or []:
        if not isinstance(event, dict):
            continue
        segs = event.get("segs") or []
        text = "".join(str(seg.get("utf8") or "") for seg in segs if isinstance(seg, dict))
        if text.strip():
            lines.append(text)
    return collapse_caption_lines(lines)


def xml_caption_to_text(payload: str) -> str:
    pieces = XML_TEXT_RE.findall(payload)
    if pieces:
        lines = [html.unescape(TAG_RE.sub(" ", piece)) for piece in pieces]
        return collapse_caption_lines(lines)
    return collapse_caption_lines([html.unescape(TAG_RE.sub(" ", payload))])


def timed_text_to_text(payload: str) -> str:
    stripped = payload.lstrip("\ufeff")
    if stripped.lstrip().startswith("<"):
        return xml_caption_to_text(stripped)
    lines: list[str] = []
    for raw in stripped.replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE", "STYLE", "REGION")):
            continue
        if line.isdigit():
            continue
        if CUE_META_RE.search(line) or "-->" in line:
            continue
        line = html.unescape(TAG_RE.sub(" ", line)).strip()
        if line:
            lines.append(line)
    return collapse_caption_lines(lines)


def caption_payload_to_text(payload: str, ext: str | None) -> str:
    kind = (ext or "").lower()
    text = payload.strip()
    if not text:
        return ""
    if kind == "json3" or text.startswith("{"):
        try:
            return json3_to_text(text)
        except json.JSONDecodeError:
            if kind == "json3":
                raise
    return timed_text_to_text(text)


def iter_lang_candidates(tracks: dict[str, Any]) -> list[str]:
    langs: list[str] = []
    for lang in ENGLISH_LANGS:
        if lang in tracks:
            langs.append(lang)
    for lang in tracks:
        if str(lang).lower().startswith("en") and lang not in langs:
            langs.append(lang)
    for lang in tracks:
        if lang not in langs:
            langs.append(lang)
    return langs


def pick_caption_source(
    info: dict[str, Any],
) -> tuple[list[dict[str, Any]] | None, str | None, str | None]:
    for kind, key in (("captions", "subtitles"), ("auto-captions", "automatic_captions")):
        tracks = info.get(key) or {}
        if not isinstance(tracks, dict):
            continue
        for lang in iter_lang_candidates(tracks):
            formats = tracks.get(lang) or []
            usable = [fmt for fmt in formats if isinstance(fmt, dict) and (fmt.get("data") or fmt.get("url"))]
            if usable:
                return usable, kind, str(lang)
    return None, None, None


def order_formats(formats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    preferred: dict[str, dict[str, Any]] = {}
    rest: list[dict[str, Any]] = []
    for fmt in formats:
        ext = str(fmt.get("ext") or "").lower()
        if ext in FORMAT_PREFERENCE and ext not in preferred:
            preferred[ext] = fmt
        else:
            rest.append(fmt)
    return [preferred[ext] for ext in FORMAT_PREFERENCE if ext in preferred] + rest


def decode_payload(raw: Any) -> str:
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return str(raw)


def default_fetch(ydl: Any, url: str) -> str:
    response = ydl.urlopen(url)
    return decode_payload(response.read())


def read_caption_payload(
    ydl: Any,
    formats: list[dict[str, Any]],
    fetch: Callable[[Any, str], str],
) -> tuple[str, str | None]:
    errors: list[str] = []
    for fmt in order_formats(formats):
        ext = str(fmt.get("ext") or "") or None
        try:
            if fmt.get("data") is not None:
                payload = decode_payload(fmt["data"])
            elif fmt.get("url"):
                payload = fetch(ydl, str(fmt["url"]))
            else:
                continue
            text = caption_payload_to_text(payload, ext)
            if text:
                return text, ext
        except Exception as exc:
            errors.append(str(exc))
    if errors:
        raise RuntimeError(errors[-1])
    return "", None


def fetch_video_transcript(
    url: str,
    *,
    ydl_factory: Callable[[dict[str, Any]], Any] = default_ydl_factory,
    fetch: Callable[[Any, str], str] | None = None,
) -> dict[str, Any]:
    validate_url(url)
    options: dict[str, Any] = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "ignoreconfig": True,
        "noplaylist": True,
    }
    fetch_payload = fetch or default_fetch
    strategy = "default"
    try:
        info, kind, language, transcript = extract_transcript_with_options(
            url=url,
            options=options,
            ydl_factory=ydl_factory,
            fetch=fetch_payload,
        )
    except Exception:
        if not is_youtube_url(url):
            raise
        fallback = dict(options)
        fallback["extractor_args"] = {
            "youtube": {"player_client": ["android", "web"]}
        }
        info, kind, language, transcript = extract_transcript_with_options(
            url=url,
            options=fallback,
            ydl_factory=ydl_factory,
            fetch=fetch_payload,
        )
        strategy = "youtube-player-client-fallback"

    source_url = str(info.get("webpage_url") or info.get("original_url") or url)
    return {
        "ok": True,
        "url": url,
        "source_url": source_url,
        "title": str(info.get("title") or ""),
        "channel": str(info.get("uploader") or info.get("channel") or ""),
        "duration": info.get("duration"),
        "description": str(info.get("description") or ""),
        "language": language,
        "transcript_kind": kind if transcript else None,
        "transcript": transcript,
        "extractor": str(info.get("extractor_key") or info.get("extractor") or ""),
        "download_strategy": strategy,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="HTTP or HTTPS URL of the video")
    args = parser.parse_args()
    print(json.dumps(fetch_video_transcript(args.url), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
