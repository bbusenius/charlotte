---
name: charlotte-url
description: Get the current LAN URL for the local Charlotte info page and deliver a scannable QR code image so the user can open it on a tablet with the camera. The info page has a short note about Charlotte and a Tools section that links to the spelling helper app. Use when the user asks for the Charlotte page URL, the tablet URL, the spelling helper URL, the spelling app URL, a QR code for the tablet, or how to open the page on the tablet. Reads the URL saved by the active runtime launcher (runtime/<runtime>/run.sh) and renders a QR PNG; the URL changes whenever the LAN IP changes, so this skill is the one-stop way to re-share it.
---

# Charlotte URL

Deliver the current LAN URL for the local Charlotte info page as both text and a QR code image, so the user can open it on a tablet by pointing the camera at the QR. The info page is a small static page (a note about Charlotte plus a Tools section that links to the spelling helper app).

Use this skill when the user asks any of:

- "What's the Charlotte page URL?"
- "Send me the tablet URL / QR code"
- "What's the spelling helper URL?" (it lives in the Tools section of this page)
- "How do I open the Charlotte page on the tablet?"
- "The tablet can't load the page — send me the URL again"

Do NOT use this skill to start, stop, or reconfigure the page server itself; this skill only surfaces the URL that the active runtime launcher (`runtime/hermes/run.sh` or `runtime/openclaw/run.sh`) last published.

## Workflow

1. Read the saved page URL from `.logs/charlotte-info/url.txt` (this file is written by the runtime launcher whenever it serves the info page). If the file is missing or empty, tell the user the info page has not been started yet (run the active runtime's `run.sh`) and stop — do not invent a URL.

2. Render a PNG QR code for that URL into `.logs/charlotte-info/qr.png` using the shared helper script:

   ```bash
   .venv/bin/python scripts/qr_url.py "$(cat .logs/charlotte-info/url.txt)" \
     --png .logs/charlotte-info/qr.png --quiet
   ```

   The script prints the PNG path on stdout when `--quiet` is set. Reuse the path you wrote.

3. Deliver to the user:

   - The URL text (so it can also be tapped, copied, or typed if needed).
   - The PNG at `.logs/charlotte-info/qr.png` as an attached image, through whatever gateway is in use (Telegram photo, web message attachment, etc.).
   - A short instruction: open the tablet camera, point it at the QR, tap the notification.

## Notes

- The page is plain HTTP and LAN-local. It only works when the tablet is on the same network as the Charlotte host. No certificate or HTTPS setup is required.
- The URL changes whenever the host's LAN IP changes (DHCP renewal, router reboot, etc.). Re-run this skill any time the tablet stops loading the page — the runtime launcher re-saves the file at every launch.
- The page has no auth. It is only meant for a trusted home network; do not expose it beyond the LAN.
