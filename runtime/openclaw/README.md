# OpenClaw Runtime Adapter

This adapter runs Charlotte inside a Docker image derived from the official
OpenClaw gateway image. The image build copies this repo to `/workspace`,
creates `/workspace/.venv` (uv-managed Python 3.12; the base image's Debian
Python is too old), and installs dependencies from `pyproject.toml` — the same
built-workspace pattern as the Hermes adapter.

Do not bind-mount the whole repo over `/workspace`. That would replace the
image's container-native `.venv` with the host checkout. Local ignored files
and content roots are mounted individually by `runtime/openclaw/run.sh`.

Status: **experimental**. The adapter follows the [runtime
contract](../../docs/runtime-contract.md), but OpenClaw's config schema moves
quickly — treat `openclaw.json.example` as a starting point and check startup
errors against the [configuration
reference](https://docs.openclaw.ai/gateway/configuration-reference) for the
image version you built. See the first-run checklist at the bottom.

## How the pieces map

| Contract requirement | OpenClaw feature |
| --- | --- |
| Skill discovery without duplicating skills | OpenClaw reads `<workspace>/skills` natively; the canonical `skills/` tree is the workspace skills dir. No symlink layer needed. |
| Operating instructions | OpenClaw reads `AGENTS.md` from the workspace root — same file, same role. |
| Sub-agent mechanism | `sessions_spawn(...)`; the abstract "spawn" verb in skills maps to it. `maxSpawnDepth: 2` in config covers curriculum → unit → lesson nesting. |
| Chat gateway with allowlist | OpenClaw channels (Telegram first), `dmPolicy: "allowlist"` + `allowFrom`. |
| File delivery to chat | `MEDIA:<absolute path>` in replies — the same convention `AGENTS.md` already teaches. |
| MCP / external tools | The bundled `mcporter` skill configures and calls stdio/HTTP MCP servers (Google Maps, Grok). See "MCP capabilities" below. |
| Scheduled work | OpenClaw cron/heartbeats. |
| Secrets | Repo-local `.env` passed via `--env-file`; config strings reference them as `${VAR_NAME}`. |

## Command sheet

Run all commands from the repo root.

```bash
# First-time local files
cp .env.example .env
chmod 600 .env
cp runtime.yaml.example runtime.yaml
cp image-generation.yaml.example image-generation.yaml

# Build or rebuild the Docker image. Pass your host IDs so files written to
# bind mounts stay host-owned.
docker build -f runtime/openclaw/Dockerfile \
  --build-arg CHARLOTTE_UID="$(id -u)" --build-arg CHARLOTTE_GID="$(id -g)" \
  -t charlotte-openclaw:local .

# Start the OpenClaw gateway in the foreground
runtime/openclaw/run.sh

# Check that the rebuilt image can see Charlotte scripts
runtime/openclaw/run.sh /workspace/.venv/bin/python /workspace/scripts/charlotte_image.py --help

# Inspect the resolved image route without generating
runtime/openclaw/run.sh /workspace/.venv/bin/python /workspace/scripts/charlotte_image.py \
  --prompt "simple watercolor oak leaf, no text, no labels" \
  --out /tmp/charlotte-image-test.png \
  --kind illustration \
  --route quality \
  --dry-run --json
```

After changing files copied into the image (skills, scripts, `AGENTS.md`),
rebuild and restart the gateway.

## Configure

Secrets live in the repo-local ignored `.env`:

```env
# Required by the gateway config; generate with: openssl rand -hex 32
OPENCLAW_GATEWAY_TOKEN=

# Telegram gateway (BotFather token; allowlist IDs go in openclaw.json)
TELEGRAM_BOT_TOKEN=

# Image routing keys as needed (see image-generation.yaml)
GEMINI_API_KEY=
XAI_API_KEY=
NANOGPT_API_KEY=
```

`runtime/openclaw/run.sh` installs `runtime/openclaw/openclaw.json.example`
to `~/.openclaw-charlotte/openclaw.json` only when that file does not already
exist. Edit the installed copy for local changes: model provider and default
model, Telegram `allowFrom` user IDs, and anything else. The installed copy is
outside the repo, so numeric IDs may be written there directly; keep API keys
in `.env` and reference them from config as `${VAR_NAME}`.

Override wrapper defaults in `.env` or the environment:

```env
CHARLOTTE_OPENCLAW_IMAGE=charlotte-openclaw:local
CHARLOTTE_OPENCLAW_HOME=~/.openclaw-charlotte
CHARLOTTE_OPENCLAW_UI_BIND=127.0.0.1
CHARLOTTE_OPENCLAW_UI_PORT=18789
```

The Control UI / gateway API is published on the host loopback by default.
Do not bind it beyond `127.0.0.1` unless you understand OpenClaw's gateway
auth model.

### Profile layout

`~/.openclaw-charlotte/` (override with `CHARLOTTE_OPENCLAW_HOME`) holds
everything stateful, mounted into the container:

| Host path | Container path | Purpose |
| --- | --- | --- |
| `~/.openclaw-charlotte/` | `/home/node/.openclaw` | Config, sessions, channel state |
| `~/.openclaw-charlotte/auth-secrets/` | `/home/node/.config/openclaw` | Auth-profile encryption keys |
| `~/.openclaw-charlotte/workspace-state/` | files/dirs under `/workspace` | Agent identity + memory (see below) |

### Workspace state: identity and memory

OpenClaw treats the workspace as the agent's home and writes identity and
memory files into it (`SOUL.md`, `IDENTITY.md`, `USER.md`, `TOOLS.md`,
`MEMORY.md`, `memory/`, `canvas/`). The workspace here is the baked image
checkout, and the gateway container is disposable (`--rm`), so those files
must live outside the container to survive.

`run.sh` seeds Charlotte-flavored starting versions from
`runtime/openclaw/workspace/` into `~/.openclaw-charlotte/workspace-state/`
once (never overwriting), and mounts that directory at
`/workspace/.agent-state`; symlinks baked into the image map
`/workspace/SOUL.md` etc. onto it. Edit the installed copies to customize the
persona — a running container picks the edits up immediately. (The directory
mount is deliberate: single-file bind mounts pin the inode and silently stop
tracking host edits once an editor or `install` replaces the file.)

`BOOT.md` and `HEARTBEAT.md` are symlinked but not seeded; create the file
in `workspace-state/` to enable the corresponding OpenClaw feature.

### Home-relative data mounts

Same mechanism as the Hermes adapter, one target path. `CHARLOTTE_HOME_MOUNTS`
entries are colon-separated, relative to `$HOME`, and mounted at the same
`~/...` path inside the container (`HOME` there is `/home/node`):

```env
CHARLOTTE_HOME_MOUNTS=Documents/Homeschool
```

mounts `$HOME/Documents/Homeschool` at `/home/node/Documents/Homeschool`, so
`students.yaml` paths like `~/Documents/Homeschool/<student>/Time.xlsx` keep
working unchanged.

### Signal capture: host-owned mode

Identical policy to the Hermes adapter. The host owns `signal-cli` and
`signal-sieve listen`; the container only lists and marks captured messages
through mounted state:

```env
CHARLOTTE_HOME_MOUNTS=Documents/Homeschool:.config/signal-sieve:.local/share/signal-sieve:.local/share/signal-cli/attachments
```

Do not run `signal-sieve listen` inside the container, and do not enable an
OpenClaw Signal channel for the same Signal account. Signal remains the
structured workflow queue per the [runtime
contract](../../docs/runtime-contract.md); OpenClaw's chat channels are for
general conversation.

## MCP capabilities

OpenClaw has no in-loop MCP client; the supported route is the bundled
`mcporter` skill (the `mcporter` CLI is baked into this image, which is also
what un-gates that skill). MCP servers are declared in
`~/.openclaw-charlotte/mcporter/mcporter.json`, installed once from
`runtime/openclaw/mcporter.json.example` and mounted at `~/.mcporter` in the
container. The example registers the same two servers the Hermes adapter
documents:

- **`google_maps`** (`mason-field-trip-planner`): the reference Google Maps
  MCP server via `npx`. Needs `GOOGLE_MAPS_API_KEY` in `.env`.
- **`grok`** (vision over Signal screenshots and book covers for
  `hsd-time-log` / `hsd-book-log`; live-search fallback for `hsd-book-log`):
  a local Grok MCP checkout run with `uv`. Mount the checkout home-relative
  with `CHARLOTTE_HOME_MOUNTS` and keep the `--directory` path in
  `mcporter.json` pointing at the `/home/node/...` location. Needs
  `XAI_API_KEY` in `.env`. The server entry pins `UV_PROJECT_ENVIRONMENT`
  to a profile-mounted path so uv never rebuilds the host checkout's own
  `.venv` with a container interpreter.

The config file carries no secrets: stdio servers inherit the container
environment, which gets its keys from `--env-file .env`.

Smoke test from the host (all three should succeed before blaming a skill):

```bash
docker run --rm --env-file .env \
  -v ~/.openclaw-charlotte/mcporter:/home/node/.mcporter \
  -v ~/Documents/Code/MCP/Grok-MCP:/home/node/Documents/Code/MCP/Grok-MCP \
  -e HOME=/home/node --entrypoint mcporter charlotte-openclaw:local list

# then a real call each way
... --entrypoint mcporter charlotte-openclaw:local \
  call 'google_maps.maps_geocode(address: "Field Museum, Chicago")'
... --entrypoint mcporter charlotte-openclaw:local call 'grok.list_models()'
```

Web search/fetch uses OpenClaw's native web tools. If a needed capability is
not configured, skills report it missing rather than guessing — that is
expected behavior.

## Voice

Voice mirrors the Hermes profile: local Whisper for inbound voice notes,
Edge TTS for spoken replies.

- **STT**: OpenClaw transcribes inbound audio before the agent sees the
  message (`tools.media.audio`). The config's first entry is a `type: "cli"`
  hook running `scripts/transcribe_media.py` — a thin wrapper around the
  `faster-whisper` engine already in the project venv (model `base`, CPU,
  same as the Hermes `stt` block). Gemini is the configured cloud fallback.
  The Whisper model downloads (~150MB) into the mounted
  `~/.openclaw-charlotte/hf-cache/` on first use and persists across
  container replacement.
- **TTS**: `messages.tts` with provider `microsoft` — OpenClaw's name for
  Edge TTS, the same free keyless Microsoft service the Hermes adapter uses
  via `edge-tts`, with the same `en-US-AriaNeural` voice. Voice-for-voice
  behavior uses `auto: "tagged"` plus a workspace `TOOLS.md` rule: the agent
  appends `[[tts:speed=1]]` when the inbound message carries the
  audio-transcript marker (the directive body is required — the parser's
  key=value pattern is `[[tts:([^\]]+)]]`, so a bare `[[tts:]]` is ignored
  and leaks into the visible reply). Do not use `auto: "inbound"` with CLI transcription — the
  transcript replaces the audio placeholder before dispatch, OpenClaw stops
  treating the message as inbound audio (upstream issue #65951), no TTS is
  attempted, and the whole reply delivery is skipped (the visible symptom:
  the streaming text preview appears, then is deleted, and no final reply
  arrives). Toggle per chat with `/tts chat on|off|default` (analog of
  Hermes' `/voice`).

## Safety contract mapping

OpenClaw defaults are permissive (full shell as the container user). The
container boundary is the outer wall: writes land only on the mounted content
roots, profile state, and `CHARLOTTE_HOME_MOUNTS` paths; everything else in
the container is disposable. Within that boundary, apply the [runtime
contract](../../docs/runtime-contract.md) safety tiers with OpenClaw's own
mechanisms as needed:

- Per-agent skill allowlists (`agents.list[].skills`) if a secondary agent
  should see only a subset of Charlotte's skills.
- Channel allowlists (`allowFrom`) kept narrow — one parent first, add family
  members deliberately.
- OpenClaw's sandbox/exec policy settings for stricter shells; see the
  OpenClaw docs. The canonical-record rules (spreadsheets only via invoked
  `hsd-*` workflows, `signal-sieve mark-processed` only after successful
  processing) are enforced by `AGENTS.md` and the skills themselves, exactly
  as in the Hermes runtime.

## Sub-agents

Skills use the neutral verb "spawn"; in this runtime it is `sessions_spawn`.
The config example sets `maxSpawnDepth: 2`, which exactly accommodates
Charlotte's deepest chain (curriculum → unit → lesson, with materials
inlined). Spawn prompts are self-contained per `AGENTS.md`; model/capability
mapping for spawned children follows `agents.defaults` and any per-spawn
`model` override the orchestrator requests.

## Local Charlotte info page

`run.sh` serves the same LAN info page as the Hermes adapter, in the same
managed `charlotte-info-page` container (from this image's Python), writes
the URL to `.logs/charlotte-info/url.txt`, and prints a QR. The
`charlotte-url` skill re-shares it on demand. The same `.env` keys apply:
`CHARLOTTE_INFO_PAGE`, `CHARLOTTE_INFO_HOST`, `CHARLOTTE_INFO_PORT`. Only one
runtime should manage this container at a time — the launcher replaces any
existing one.

## First-run checklist

Things to verify once against the OpenClaw version you actually built,
in order:

1. `runtime/openclaw/run.sh /workspace/.venv/bin/python -c "import weasyprint, playwright, openpyxl"` — toolchain imports.
2. Gateway starts: `runtime/openclaw/run.sh`, watch for config-key errors
   (schema drift shows up here; fix the installed `openclaw.json`).
3. Skills visible: from a paired chat or the Control UI, confirm the
   `mason-*` / `hsd-*` skills are listed from `/workspace/skills`.
4. Telegram DM from an allowlisted ID gets a reply; a non-allowlisted ID
   does not.
5. `MEDIA:` delivery: ask for a standalone image; confirm the generated file
   lands in `generated-images/` host-side, owned by your user, and arrives
   as a photo.
6. Spawn depth: run a small `mason-unit-builder` request and confirm lesson
   spawns work (depth 2).
7. If using Signal logging: `signal-sieve list` works in-container against
   the mounted host database.
