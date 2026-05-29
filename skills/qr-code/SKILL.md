---
name: qr-code
description: Make a scannable QR code for any web URL — or for a known resource named by the user — and deliver it as an image through the active gateway (Telegram photo, web attachment, etc.). Use when the user asks to "make a QR code for <url>", "send me a QR for <page>", "QR this link", or names a homeschool resource they want on a tablet. Resolves a named page against the curated qr.known_links list in runtime.yaml first, then falls back to a pasted URL or web/knowledge lookup. For the local Charlotte info page specifically, use the charlotte-url skill instead.
---

# QR Code

Turn a URL into a scannable QR code image and hand it to the user, so they can open the page on a tablet or phone by pointing the camera at it. Useful in a Telegram chat with Charlotte: "make me a QR for the spelling app", "QR this: https://…".

Use this skill when the user asks any of:

- "Make a QR code for https://example.com"
- "Send me a QR for Ambleside" / "QR the spelling app"
- "Put this link on the tablet as a QR"

Do NOT use this skill for the **local Charlotte info page** (the `http://<lan-ip>:8788` page that `runtime/hermes/run.sh` serves) — that has its own skill, `charlotte-url`, which reads the current LAN URL. This skill is for arbitrary web URLs and curated known links.

## Resolving the target URL

Work out the URL in this order, stopping at the first that succeeds:

1. **Pasted URL.** If the user's message contains a URL, use it verbatim. (Accept bare hosts like `example.com` and add `https://` if no scheme is present.)
2. **Known links (checked first for named pages).** If the user names or describes a page rather than pasting a link, read `runtime.yaml` and look in `qr.known_links`. Match the user's phrase against each entry's `name` and `aliases`, case-insensitively. On a match, use that entry's `url`. This is a priority list, not a whitelist — it just saves guessing the URL of an esoteric resource.
3. **Fallback.** If the named page isn't in `known_links`, resolve it however you can — a web search or your own knowledge if the runtime allows it. If you cannot determine a trustworthy URL, ask the user to paste the link rather than guessing.

If the user names something ambiguous that matches more than one known link, ask which they meant before rendering.

## Rendering

Render a PNG QR for the resolved URL with the shared helper script. Choose a short, filesystem-safe slug for the filename (from the known-link `name`, or the URL's host):

```bash
.venv/bin/python scripts/qr_url.py "<resolved-url>" \
  --png ".logs/qr/<slug>.png" --quiet
```

The script prints the PNG path on stdout when `--quiet` is set. It works fully offline — rendering needs no network access; only *discovering* an unknown URL (step 3 above) might.

## Deliver

Send the user:

- The resolved URL as text (so it can be tapped, copied, or typed).
- The PNG at `.logs/qr/<slug>.png` as an attached image, through whatever gateway is in use.
- A short instruction: open the camera, point it at the QR, tap the notification.

If you had to fall back (step 3) or normalize the input, say briefly which URL you encoded so the user can correct it.

## Notes

- The QR encodes whatever URL you point it at; Charlotte does not need web access to *make* a QR, only to look up an unknown link.
- `.logs/` is ignored by git and treated as scratch; old QR PNGs there are disposable.
- To add a resource you reach for often, put it in `qr.known_links` in `runtime.yaml` (see `runtime.yaml.example`) so a name is enough next time.
