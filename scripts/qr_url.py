#!/usr/bin/env python3
"""Render a QR code for a local URL, for terminal preview and PNG export.

Two callers share this helper:

- `runtime/hermes/run.sh` prints the UTF-8 QR to the host terminal when the
  local Charlotte info page comes up, so a tablet camera can scan it immediately.
- The `charlotte-url` skill writes a PNG (via `--png`) for the AI to deliver
  through whatever gateway the user is on (Telegram, web, etc.).

Defaults to printing the UTF-8 QR. Pass `--png PATH` to also write a PNG, and
`--quiet` to suppress the terminal QR (the skill uses both flags together).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def render_terminal(url: str) -> None:
    import qrcode

    qr = qrcode.QRCode(border=1, error_correction=qrcode.constants.ERROR_CORRECT_L)
    qr.add_data(url)
    qr.make()
    # Half-block rendering (1 char wide per module, 2 modules per line) is the
    # smallest reliably scannable QR in a monospace terminal: tighter packings
    # (quadrant blocks, braille) break the continuous per-module fill that
    # phone cameras need to lock on.  invert=True draws light modules as
    # foreground glyphs, which reads best on dark terminals.
    qr.print_ascii(out=sys.stdout, invert=True)


def render_png(url: str, path: Path) -> None:
    import qrcode

    path.parent.mkdir(parents=True, exist_ok=True)
    img = qrcode.make(url)
    img.save(str(path))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument(
        "--png",
        type=Path,
        help="Also write a PNG QR code to this path.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Skip the UTF-8 QR preview on stdout.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.url.strip():
        print("qr_url.py: empty URL", file=sys.stderr)
        return 2

    if not args.quiet:
        render_terminal(args.url)

    if args.png:
        render_png(args.url, args.png)
        if args.quiet:
            # Emit the path so callers (the skill) can pick it up from stdout.
            print(str(args.png))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
