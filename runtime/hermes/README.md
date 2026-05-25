# Hermes Runtime Adapter

This adapter runs Charlotte inside the official Hermes container image. The image build copies this repo to `/workspace`, creates `/workspace/.venv`, and installs dependencies from `pyproject.toml`.

Do not bind-mount the whole repo over `/workspace` for the normal runtime path. That would replace the image's container-native `.venv` with the host checkout.

Hermes runs from its own internal Python environment. Charlotte project scripts should be invoked through `/workspace/.venv/bin/...` or repo-relative `.venv/bin/...` so they use the dependencies installed from `pyproject.toml`.

## Command Sheet

Run all commands from the repo root.

```bash
# First-time local files
cp .env.example .env
chmod 600 .env
cp runtime.yaml.example runtime.yaml

# Build or rebuild the Docker image
docker build -f runtime/hermes/Dockerfile -t charlotte-hermes:local .

# Run an interactive Hermes chat
runtime/hermes/run.sh chat

# Start the Telegram gateway in the foreground
runtime/hermes/run.sh gateway run

# Check that the rebuilt image can see Charlotte scripts
runtime/hermes/run.sh .venv/bin/python scripts/charlotte_image.py --help

# Test image routing locally, outside Docker
.venv/bin/python scripts/charlotte_image.py \
  --prompt "simple watercolor oak leaf, no text, no labels" \
  --out /tmp/charlotte-image-test.png \
  --preference gemini \
  --json

# Test image routing inside Docker
runtime/hermes/run.sh .venv/bin/python scripts/charlotte_image.py \
  --prompt "simple watercolor oak leaf, no text, no labels" \
  --out /tmp/charlotte-image-test.png \
  --preference gemini \
  --json
```

After changing files copied into the image, rebuild and restart the gateway:

```bash
docker build -f runtime/hermes/Dockerfile -t charlotte-hermes:local .
# Stop the old foreground gateway with Ctrl+C, then:
runtime/hermes/run.sh gateway run
```

Files copied into the image include `skills/`, `scripts/`, `README.md`, `AGENTS.md`, `pyproject.toml`, and runtime adapter files. Local ignored files such as `.env`, `runtime.yaml`, `students.yaml`, and generated content roots are mounted or passed at runtime.

Standalone image requests should save under `generated-images/`. Tablet slide packages belong under `tablet-slides/`.

`runtime/hermes/run.sh` installs `runtime/hermes/config.yaml.example` to `~/.hermes-charlotte/config.yaml` only when that profile config does not already exist. If you change the example later, update the live profile config intentionally.

To compare the tracked example with the live profile config:

```bash
diff -u runtime/hermes/config.yaml.example ~/.hermes-charlotte/config.yaml
```

To reset the live profile config from the tracked example, back it up first, then reinstall the example and reapply any local profile edits:

```bash
cp ~/.hermes-charlotte/config.yaml ~/.hermes-charlotte/config.yaml.bak
install -m 600 runtime/hermes/config.yaml.example ~/.hermes-charlotte/config.yaml
```

## Build

Run from the repo root:

```bash
docker build -f runtime/hermes/Dockerfile -t charlotte-hermes:local .
```

## Configure

Secrets are loaded from the repo-local ignored `.env` at runtime:

```bash
cp .env.example .env
chmod 600 .env
```

Fill only the keys and local mount settings your runtime needs. The image build excludes `.env`; do not bake secrets into the image.

The default Hermes config uses NanoGPT's subscription API with MiniMax M2.7 as the model driver:

```env
NANOGPT_API_KEY=
```

Charlotte image generation is routed by `scripts/charlotte_image.py` using `runtime.yaml`. Useful `.env` keys:

```env
NANOGPT_IMAGE_MODEL_SUBSCRIPTION=
NANOGPT_IMAGE_MODEL_GEMINI=
NANOGPT_IMAGE_MODEL_GROK=
GEMINI_API_KEY=
XAI_API_KEY=
XAI_IMAGE_MODEL=
GOOGLE_MAPS_API_KEY=
```

NanoGPT subscription chat uses `https://nano-gpt.com/api/subscription/v1`. NanoGPT subscription images use `https://nano-gpt.com/api/generate-image` with models from the subscription image model list. NanoGPT's OpenAI-compatible `/v1/images/generations` endpoint may require separate USD balance.

For quality-first image generation, keep direct Gemini first and direct Grok second in local `runtime.yaml`; use NanoGPT subscription images as a lower-cost fallback. Standalone Telegram image requests should pass the user's requested subject plainly to `--prompt` and use `--mason-aesthetics`; that flag reads the compact image-router summary from `skills/mason-aesthetics/SKILL.md`.

`GOOGLE_MAPS_API_KEY` is for Maps-capable MCP/runtime tools. It is separate from Gemini image-generation keys and is only useful when the active Hermes toolset exposes a Google Maps capability.

## Tool Surface

The adapter's support checklist is tracked in [../../docs/runtime-tool-surface.md](../../docs/runtime-tool-surface.md).

This image currently provisions Charlotte's local CLI layer: the Python `.venv` from `pyproject.toml`, `signal-sieve`, `xlsx-append`, WeasyPrint, `inkscape`, and repo scripts such as `scripts/charlotte_image.py`. Runtime files and family data are mounted at startup by `runtime/hermes/run.sh`.

MCP-style capabilities are a separate layer. Field trip planning needs Google Maps plus web search/fetch; Signal image logging and last-resort book lookup need vision/search capability. If Hermes exposes equivalent native tools, the skills can use those. If it does not, those workflows should report the missing capability instead of guessing.

Hermes MCP servers are configured in the profile config at `~/.hermes-charlotte/config.yaml`, mounted inside the container as `/opt/data/config.yaml`. `terminal.env_passthrough` is not enough for MCP credentials; stdio MCP subprocesses receive only safe baseline variables plus variables explicitly listed in that server's `env`.

Add servers under `mcp_servers` using Hermes' standard shape:

```yaml
mcp_servers:
  some_stdio_server:
    command: "server-command"
    args: ["--flag", "value"]
    env:
      SOME_SERVER_KEY: "..."

  some_http_server:
    url: "https://example.invalid/mcp"
    headers:
      Authorization: "Bearer ..."
```

MCP servers create toolsets named `mcp-<server>`. Add the needed MCP toolset to each platform that should be able to use it:

```yaml
platform_toolsets:
  cli: [hermes-cli, mcp-google_maps, mcp-grok_mcp]
  telegram: [terminal, file, web, vision, skills, todo, cronjob, mcp-google_maps, mcp-grok_mcp]
```

One useful local pattern is to mount a home-relative MCP server checkout with `CHARLOTTE_HOME_MOUNTS`, then point the MCP command at the corresponding `/opt/data/...` path:

```env
CHARLOTTE_HOME_MOUNTS=Documents/Homeschool:path/to/local-grok-mcp
```

```yaml
mcp_servers:
  grok_mcp:
    command: "uv"
    args: ["run", "--directory", "/opt/data/path/to/local-grok-mcp", "python", "-m", "src.server"]
    env:
      XAI_API_KEY: "${XAI_API_KEY}"
```

Keep real MCP credentials out of tracked repo files. Because `runtime/hermes/run.sh` only installs `runtime/hermes/config.yaml.example` when the live profile config is missing, changes to this example do not overwrite an existing `~/.hermes-charlotte/config.yaml`.

### Home-Relative Data Mounts

Some skills need host files referenced from `students.yaml`. The current `hsd-time-log` and `hsd-book-log` skills write to Homeschool-Dashboard-compatible time and reading spreadsheets, but the runtime mount mechanism is generic.

Use `CHARLOTTE_HOME_MOUNTS` to mount one or more host directories under `$HOME` into the Hermes container at the same `~/...` path. Entries are colon-separated and must be relative to `$HOME`:

```env
CHARLOTTE_HOME_MOUNTS=Documents/Homeschool
```

That mounts:

```text
host:      $HOME/Documents/Homeschool
container: /opt/data/home/Documents/Homeschool
           /opt/data/Documents/Homeschool
```

Hermes terminal subprocesses use `/opt/data/home` as `HOME`, so `students.yaml` paths such as `~/Documents/Homeschool/<student>/Time.xlsx` keep working in both local Codex/Claude usage and Docker runtime usage. The wrapper also mounts each entry under `/opt/data` for profile-level config and explicit MCP command paths. Add only the directories needed by your local records or other host data.

The run wrapper creates `~/.hermes-charlotte`, its isolated `home/` directory, installs `runtime/hermes/config.yaml.example` there if no config exists, and creates the ignored local data roots if needed.

### Signal Capture: Host-Owned Mode

The single-container Hermes adapter can consume Signal messages captured by a host-owned `signal-sieve` listener. In this mode, the host owns Signal capture and Hermes mounts the host `signal-sieve` config, database, and attachments.

Example:

```env
CHARLOTTE_HOME_MOUNTS=Documents/Homeschool:.config/signal-sieve:.local/share/signal-sieve:.local/share/signal-cli/attachments
```

That gives Hermes access to:

- Homeschool-Dashboard-compatible spreadsheets referenced from `students.yaml`
- `signal-sieve` aliases and capture config
- The captured-message SQLite database
- Signal attachments used by image-based logging workflows

With those mounts present, Hermes can run `signal-sieve list` and `signal-sieve mark-processed` against the same database the host listener writes. Do not run `signal-sieve listen` inside this Hermes container while the host listener owns the same Signal account and group/contact set.

In host-owned mode, `daemon_url: "http://localhost:8080"` in the host `signal-sieve` config points at the host, not the container. Listing and marking messages do not need the daemon, but daemon-dependent commands such as listener startup, send/reply, and full daemon status remain host-side concerns in the currently supported runtime.

## Run

Run Hermes commands through the wrapper:

```bash
runtime/hermes/run.sh skills list
runtime/hermes/run.sh chat
```

With no arguments, the wrapper runs `hermes chat`.

The wrapper passes `HERMES_UID` and `HERMES_GID` so files written through mounted volumes are owned by the host user. It mounts `~/.hermes-charlotte` to `/opt/data`, mounts `students.yaml` and local `runtime.yaml` read-only when present, mounts the ignored Charlotte data roots to `/workspace`, and mounts any configured `CHARLOTTE_HOME_MOUNTS` entries into both `/opt/data/home` and `/opt/data`.

Override defaults with `CHARLOTTE_HERMES_IMAGE`, `CHARLOTTE_HERMES_HOME`, or `CHARLOTTE_HOME_MOUNTS`.

## Telegram Gateway

The first supported Telegram setup is direct-message only: open Telegram, message the bot, and treat every message as intended for Charlotte. Group chats and mention-based behavior are deferred.

Create a Telegram bot with BotFather, then put the token and allowed numeric Telegram user IDs in the repo-local `.env`:

```env
NANOGPT_API_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_USERS=
```

`TELEGRAM_ALLOWED_USERS` is a comma-separated list. Start with one user ID and add family members later as needed.

Run the gateway in the foreground:

```bash
runtime/hermes/run.sh gateway run
```

The gateway runs inside the Charlotte Hermes container, so `/workspace` paths are visible to the gateway. Generated files should still land under mounted local data roots such as `tablet-slides/`, `generated-images/`, `curricula/`, `field-trips/`, `.backups/`, and `.logs/`.
