#!/usr/bin/env python3
"""Transcribe one audio file to plain text on stdout.

Thin faster-whisper wrapper for runtime STT hooks (e.g. OpenClaw's
tools.media.audio CLI provider). faster-whisper decodes Telegram's Ogg/Opus
voice notes directly, no ffmpeg CLI needed. The model downloads to the
Hugging Face cache on first use; runtime adapters should persist that cache
across container restarts.
"""

from __future__ import annotations

import argparse

from faster_whisper import WhisperModel


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="Audio file to transcribe")
    parser.add_argument(
        "--model",
        default="base",
        help="faster-whisper model size or path (default: base)",
    )
    args = parser.parse_args()

    model = WhisperModel(args.model, device="cpu", compute_type="int8")
    segments, _info = model.transcribe(args.path)
    text = "".join(segment.text for segment in segments).strip()
    print(text)


if __name__ == "__main__":
    main()
