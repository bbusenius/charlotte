---
name: mindfeast-agent-alarm
description: Push a morning atmosphere to MindFeast Agent Alarm over LAN (status, wake audio, picture, notes/heading, theme, wake time/enable, clock format). Use when the user asks to set the agent alarm, push a wake song, morning picture, morning note, theme, or alarm time to a student's tablet. Reads per-student agent_alarm.remote_url and agent_alarm.remote_token from students.yaml; never prints the token.
argument-hint: "[student name|slug|alias] [--all] [--status|--dry-run] [--audio PATH] [--picture PATH] [--artist TEXT] [--title TEXT] [--notes TEXT] [--notes-heading TEXT] [--theme JSON|--theme-restore-default] [--time HH:MM] [--enable|--disable] [--use-24-hour|--use-12-hour]"
---

# MindFeast Agent Alarm

Talk to the **MindFeast Agent Alarm** Android app on the LAN. This is separate from MindFeast lock-screen slide sync (`mindfeast.remote_*`). Each student with an alarm has their own `agent_alarm` endpoint. Two students may share one URL when they share a tablet.

Use this skill when the user asks to set the agent alarm, push wake audio, a morning picture, morning notes, theme colors, or alarm time/enable.

Do not invent the tablet IP or token. Never print the bearer token. Never use MindFeast lock-screen `/api/sync` or `/api/trigger` here. Do not create slides or generate media in this skill; push existing files.

## Student Config

Read `students.yaml` at runtime. Resolve the student by slug, `display_name`, or `aliases`. Never hard-code names, paths, URLs, or tokens.

This skill expects:

```yaml
agent_alarm:
  remote_url: http://192.0.2.20:8787
  remote_token: "token from Agent Alarm → Welcome your agent"
```

`remote_url` is scheme + host + port only (default listen port `8787`). `remote_token` is the app bearer token. If either is missing or blank, skip that student and report that Agent Alarm is not configured — do not fall back to `mindfeast.remote_*` (that is the lock-screen app).

## Prerequisites on the tablet

- Same Wi-Fi as the machine running Charlotte
- **Welcome your agent** on, **Listening on your LAN** confirmed
- Token shown in Agent Alarm settings

## Workflow

1. Parse the prompt for a student name, slug, alias, `--all`, the operations below, `--dry-run`, and timeout. Multiple ops in one run are fine; order them: status (optional) → audio → picture → picture meta → notes → theme → clock → time → enable.
2. If a student is named, push only that student's alarm. If no student is named, push every student with both `agent_alarm.remote_url` and `agent_alarm.remote_token` configured. If more than one student is configured, report each result separately.
3. When the run includes a picture, inspect that image and derive `--theme` before calling the helper. See *Theme from the picture*. Do not push a picture without `--theme`. Do not restore the default theme on the same run as a picture. If no image-understanding capability can inspect the pixels, stop and leave the tablet unchanged.
4. From the repository root, use the helper (never embed the token in argv via shell `curl -H "Authorization: Bearer …"`):

```bash
.venv/bin/python skills/mindfeast-agent-alarm/scripts/push.py --student <student-slug-or-name> --status
.venv/bin/python skills/mindfeast-agent-alarm/scripts/push.py --student <student-slug-or-name> --dry-run --audio /path/to/wake.mp3
.venv/bin/python skills/mindfeast-agent-alarm/scripts/push.py \
  --student <student-slug-or-name> \
  --audio /path/to/wake.mp3 \
  --picture /path/to/morning.jpg \
  --artist "Artist Name" \
  --title "Work Title" \
  --notes-heading "A thought for the morning" \
  --notes $'Line one.\nLine two.' \
  --theme '<JSON derived from inspecting the picture>' \
  --time 07:30 \
  --enable
```

Every configured student:

```bash
.venv/bin/python skills/mindfeast-agent-alarm/scripts/push.py --all --status
```

Restore the app default theme (not with `--picture`):

```bash
.venv/bin/python skills/mindfeast-agent-alarm/scripts/push.py --student <student-slug-or-name> --theme-restore-default
```

5. Prefer the helper over hand-rolled HTTP. If you must use curl, write the Authorization header to a temp file (`Authorization: Bearer <token>`) and pass `--header @file`, then delete the file.

## API contract (v1)

All routes require `Authorization: Bearer <token>` and a LAN peer. Mutations return the status object.

| Op | Route | Body |
| --- | --- | --- |
| Status | `GET /api/status` | — |
| Audio | `POST /api/audio` | raw bytes; `Content-Type: audio/*` or `application/octet-stream`; optional `X-Filename` (clears composer/title) |
| Audio meta | `POST /api/audio/meta` | `{"composer":"…","title":"…"}` (empty strings allowed; same sanitization/length as picture meta) |
| Picture | `POST /api/picture` | raw JPEG/PNG/WebP; optional `X-Filename` |
| Picture meta | `POST /api/picture/meta` | `{"artist":"…","title":"…"}` (empty strings allowed) |
| Notes | `POST /api/notes` | `notes` and/or `notesHeading` (at least one) |
| Notes heading only | `POST /api/notes/heading` | `{"notesHeading":"…"}` |
| Theme | `POST /api/theme` | partial object: `text`, `textSecondary`, `card`, `cardAlpha`, `accent` |
| Theme restore | `POST /api/theme/restore-default` | `{}` |
| Clock format | `POST /api/alarm/clock` | `{"use24Hour":true\|false}` (default app preference is 12-hour) |
| Time | `POST /api/alarm/time` | `{"time":"07:30"}` or `{"hour":7,"minute":30}` |
| Enable | `POST /api/alarm/enable` | `{"enabled":true\|false}` |

Limits worth respecting: audio ≤ 50 MiB; picture ≤ 10 MiB; JSON ≤ 4 KiB; notes ≤ 2 KiB UTF-8; heading/artist/title/composer/audio title ≤ 200 chars. Theme colors are `#RGB` / `#RRGGBB`; `cardAlpha` is 0–1. Accent-surface text is fixed white (not a token).

Helper flags for wake-sound attribution: `--composer` and `--audio-title` map to `POST /api/audio/meta` (`composer` / `title` JSON). Status exposes `audioComposer` and `audioTitle`. Importing or clearing audio clears those fields; empty strings are allowed.

## Theme from the picture

`--picture` requires `--theme` on the same invocation. The helper will reject a picture push with no theme, or with `--theme-restore-default`.

Inspect the picture file itself with the default image-understanding capability in the active environment. Require genuine pixel-level inspection; filename, artist/title metadata, dimensions, and a remembered palette do not satisfy this step. Do not name or directly call a provider when the environment already supplies an image-understanding capability.

From that inspection, build one coherent overlay that belongs to this image:

- Sample colors that actually appear: sky, ground, walls, garments, foliage, light, and shadow. Do not invent a generic teal, pastel, or brand palette, and do not reuse a previous run's theme.
- Choose light type on a dark card or dark type on a light card from the picture's value structure, not from habit. `text` must read at a glance on `card`; `textSecondary` is quieter and still readable.
- `card` is a muted field from the picture (shadow, paper, wall, sky). `accent` is a smaller distinct note from the picture (a garment, flower, roof, or highlight), not a decorative extra.
- Set `text`, `textSecondary`, `card`, `cardAlpha`, and `accent` together. `cardAlpha` should hold the type while still letting the painting be the atmosphere.
- Settings chrome on the phone stays high-contrast regardless of theme.

Pass the result as `--theme '{"text":"#RRGGBB","textSecondary":"#RRGGBB","card":"#RRGGBB","cardAlpha":0.72,"accent":"#RRGGBB"}'` with the hex values you derived. If inspection is unavailable, stop rather than guessing colors or pushing the picture unthemed.

## Delivery

Report:

- Student display name or slug
- Endpoint host and path only (never the token)
- Each operation attempted and HTTP success/failure
- When a picture was pushed: the derived theme tokens
- From status when useful: next fire, `audioPresent`, `pictureCustom`, `notesHeading`, `use24Hour`, theme tokens

If the listener is down, Wi-Fi differs, or auth fails, say so plainly and leave media on disk — do not claim the tablet updated.
