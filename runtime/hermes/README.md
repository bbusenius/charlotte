# Hermes Runtime Adapter

This adapter runs Charlotte inside the official Hermes container image. The image build copies this repo to `/workspace`, creates `/workspace/.venv`, and installs dependencies from `pyproject.toml`.

Do not bind-mount the whole repo over `/workspace` for the normal runtime path. That would replace the image's container-native `.venv` with the host checkout.

Hermes runs from its own internal Python environment. Charlotte project scripts should be invoked through `/workspace/.venv/bin/...` or repo-relative `.venv/bin/...` so they use the dependencies installed from `pyproject.toml`.

The image installs Chromium for the Lexile lookup used by book logging. A host `runtime.yaml` can still set `tools.chrome_path`, but `scripts/lexile/lookup.py` will ignore that path inside Hermes if it does not exist and fall back to the container's Chromium executable.

## Command Sheet

Run all commands from the repo root.

```bash
# First-time local files
cp .env.example .env
chmod 600 .env
cp runtime.yaml.example runtime.yaml
cp image-generation.yaml.example image-generation.yaml

# Build or rebuild the Docker image
docker build -f runtime/hermes/Dockerfile -t charlotte-hermes:local .

# Run an interactive Hermes chat
runtime/hermes/run.sh chat

# Start the Telegram gateway in the foreground
runtime/hermes/run.sh gateway run

# Check that the rebuilt image can see Charlotte scripts
runtime/hermes/run.sh .venv/bin/python scripts/charlotte_image.py --help

# Inspect the resolved route and final provider prompt without generating
runtime/hermes/run.sh .venv/bin/python scripts/charlotte_image.py \
  --prompt "simple watercolor oak leaf, no text, no labels" \
  --out /tmp/charlotte-image-test.png \
  --kind illustration \
  --route quality \
  --dry-run \
  --json

# Test image routing locally, outside Docker
.venv/bin/python scripts/charlotte_image.py \
  --prompt "simple watercolor oak leaf, no text, no labels" \
  --out /tmp/charlotte-image-test.png \
  --kind illustration \
  --route quality \
  --json

# Test image routing inside Docker
runtime/hermes/run.sh .venv/bin/python scripts/charlotte_image.py \
  --prompt "simple watercolor oak leaf, no text, no labels" \
  --out /tmp/charlotte-image-test.png \
  --kind illustration \
  --route quality \
  --json
```

After changing files copied into the image, rebuild and restart the gateway:

```bash
docker build -f runtime/hermes/Dockerfile -t charlotte-hermes:local .
# Stop the old foreground gateway with Ctrl+C, then:
runtime/hermes/run.sh gateway run
```

Files copied into the image include `skills/`, `scripts/`, `README.md`, `AGENTS.md`, `pyproject.toml`, and runtime adapter files. Local ignored files such as `.env`, `runtime.yaml`, `image-generation.yaml`, `students.yaml`, and generated content roots are mounted or passed at runtime.

The wrapper also mounts the ignored root `.state/` and `.scratch/` directories. `.state/` preserves workflow cursors across container rebuilds and across Charlotte runtimes; `.scratch/` holds disposable working files. Both are writable by Hermes, but neither is a finished-content root.

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

The supplied example profile uses Gemini 2.5 Flash as its main model and auxiliary vision fallback, and uses the same direct Google credential for Charlotte image generation:

```env
GEMINI_API_KEY=
# or GOOGLE_API_KEY=
```

With `agent.image_input_mode: auto`, a vision-capable main model inspects images directly and the auxiliary model is not called. Provider credentials do not belong in `terminal.env_passthrough`; Hermes deliberately scrubs them from model-authored subprocesses.

The custom image backend baked into the Charlotte Hermes image registers as `image_gen.provider: gemini`. It runs `scripts/charlotte_image.py` from Hermes's trusted provider process, so `image-generation.yaml`, the configured aesthetics skill, and route provenance remain authoritative without exposing the Gemini key to terminal commands. The shipped profile selects the `quality` route:

```yaml
image_gen:
  provider: "gemini"
  model: "quality"
```

For quality-first image generation, keep the local `quality` route pointed at the desired direct Google model. Use the `fast` route for fast/simple generation. The provider rejects any result that does not report the requested route, `source: google`, and the expected aesthetics prompt mode.

`GOOGLE_MAPS_API_KEY` is for Maps-capable MCP/runtime tools. It is separate from Gemini image-generation keys and is only useful when the active Hermes toolset exposes a Google Maps capability.

### Local Charlotte Info Page

`runtime/hermes/run.sh` serves a small static Charlotte info page over plain HTTP in a managed `charlotte-info-page` container, then starts Hermes. The page has a short blurb about Charlotte and a Tools section linking to the spelling helper app. No microphone is involved, so it needs no HTTPS or certificate. Configure it in the repo-local ignored `.env`:

```env
CHARLOTTE_INFO_PAGE=1
CHARLOTTE_INFO_HOST=
CHARLOTTE_INFO_PORT=8788
```

Leave `CHARLOTTE_INFO_HOST` blank for the normal path: the wrapper detects the current LAN IP, serves the page, prints the URL plus a scannable QR, and writes the URL to `.logs/charlotte-info/url.txt`. The `charlotte-url` skill re-shares that URL and QR on demand. Set `CHARLOTTE_INFO_PAGE=0` to disable serving it.

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

Configured MCP servers are discovered automatically. To enable one for a
platform, add its raw server name—not `mcp-<server>`—to
`platform_toolsets`. Hermes resolves those aliases after discovery:

```yaml
platform_toolsets:
  cli: [hermes-cli, browser, image_gen, delegation, google_maps, grok_mcp]
  telegram: [terminal, file, web, browser, vision, image_gen, tts, skills, todo, cronjob, delegation, google_maps, grok_mcp]
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

The wrapper passes `HERMES_UID` and `HERMES_GID` so files written through mounted volumes are owned by the host user. It mounts `~/.hermes-charlotte` to `/opt/data`, mounts `students.yaml` and local `runtime.yaml` / `image-generation.yaml` read-only when present, mounts the ignored Charlotte data roots to `/workspace`, and mounts any configured `CHARLOTTE_HOME_MOUNTS` entries into both `/opt/data/home` and `/opt/data`.

Hermes' native `write_file` tool applies an additional application-level path check beyond ordinary container filesystem permissions. The wrapper sets `HERMES_WRITE_SAFE_ROOT` to `/opt/data` and the specific writable Charlotte content roots under `/workspace`; it does not authorize the whole source tree. When adding a writable content-root mount, add its container path to that list as well.

The wrapper quiets s6 supervisor chatter by default with `S6_VERBOSITY=0` and `S6_LOGGING=0`. To debug container boot, set `CHARLOTTE_HERMES_S6_VERBOSITY=1` or `CHARLOTTE_HERMES_S6_LOGGING=1` in the shell or `.env` before running `runtime/hermes/run.sh`.

Override defaults with `CHARLOTTE_HERMES_IMAGE`, `CHARLOTTE_HERMES_HOME`, or `CHARLOTTE_HOME_MOUNTS`.

## HTTP API

Hermes can expose Charlotte as a local HTTP API on the same gateway process that serves Telegram and Discord. Clients reach Charlotte’s configured agent environment — workspace, `AGENTS.md`, skills, memory, and tools. They do not receive Charlotte’s provider credentials.

This is opt-in. Uncomment the API keys in the repo-local `.env`, or set the same variables in the live profile `.env` at `~/.hermes-charlotte/.env` (or `$CHARLOTTE_HERMES_HOME/.env`):

```env
API_SERVER_ENABLED=true
API_SERVER_PORT=8642
API_SERVER_KEY=
API_SERVER_MODEL_NAME=charlotte
```

Generate the bearer token with `openssl rand -hex 32`. The token is a local credential shared with API clients; keep it out of tracked files. Rotate it on both the server and every client.

When the API is enabled, `runtime/hermes/run.sh` binds the listener on `0.0.0.0` inside the container (Docker port publishing cannot reach a container-local `127.0.0.1` bind) and publishes `127.0.0.1:8642` on the host. Override the host bind with `CHARLOTTE_HERMES_API_BIND` only when you have a trusted tunnel; the default keeps the API off the LAN. The bearer token is required.

The example profile gives API clients the same tools as `cli`:

```yaml
platform_toolsets:
  api_server: [hermes-cli, browser, image_gen, delegation]
```

`runtime/hermes/run.sh` installs `config.yaml.example` only when the live profile config is missing. Existing profiles need this `api_server` entry added by hand. Match your live `cli` list, including any MCP servers already configured there; those servers must exist in the profile.

The API is served by the gateway. After changing these settings, restart it:

```bash
runtime/hermes/run.sh gateway run
```

A restart briefly interrupts Telegram and Discord. Do not start a second gateway against the same live profile.

Clients use `http://127.0.0.1:8642`. OpenAI-compatible callers append `/v1`; Hermes-native run submission uses `POST /v1/runs` on the same listener. A cheap check:

```bash
curl -sS http://127.0.0.1:8642/health
curl -sS -H "Authorization: Bearer $API_SERVER_KEY" http://127.0.0.1:8642/v1/models
```

See the [Hermes API server reference](https://hermes-agent.nousresearch.com/docs/user-guide/features/api-server) for the rest of the surface.

## Walkietalk

[Walkietalk](https://github.com/bbusenius/walkietalk) is a radio bridge that can
use Charlotte for answers and, optionally, her configured Hermes speech
provider for the voice. Charlotte retains her workspace instructions, skills,
memory, tools, and chosen model. Walkietalk owns radio capture, wake matching,
conversation limits, playback, and push-to-talk.

Agent, speech recognition, and voice are independent settings in Walkietalk.
Using Charlotte for answers does not require Hermes speech: you can keep Piper
or another supported voice. This integration does not expose Hermes speech
recognition; choose a supported Walkietalk STT backend separately.

### Connect Walkietalk to Charlotte

1. Enable the [HTTP API](#http-api), set a private `API_SERVER_KEY`, and add
   `platform_toolsets.api_server` to an existing profile as described above.
   Restart the gateway through your normal startup procedure after changing
   its API settings. New profiles inherit the example's API toolset; existing
   profiles are not overwritten by `run.sh`.
2. Install [Walkietalk](https://github.com/bbusenius/walkietalk#readme) on the
   radio host and configure its audio devices, PTT, wake phrase, and STT there.
3. Set the following fields in Walkietalk's config. These are **selected fields**;
   retain the other required fields from Walkietalk's `config.example.yaml`.

   ```yaml
   agent:
     backend: "hermes"
     hermes_url: "http://127.0.0.1:8642"
     hermes_token_env: "WALKIETALK_HERMES_TOKEN"
   ```

4. Make the same bearer token available to the **Walkietalk process** as
   `WALKIETALK_HERMES_TOKEN`. Charlotte reads `API_SERVER_KEY` on the server;
   configuring that variable in Charlotte does not automatically export a
   variable to a separate client process. For a terminal session, enter the
   existing token without putting it in shell history:

   ```bash
   read -rsp 'Hermes connection token: ' WALKIETALK_HERMES_TOKEN
   printf '\n'
   export WALKIETALK_HERMES_TOKEN
   ```

   Skip this if your Walkietalk launch environment already supplies the token.
   For persistent launches, supply it through your launcher's private environment
   configuration (for example, an owner-readable systemd `EnvironmentFile`).
   Walkietalk reads the variable named in its YAML; it does not automatically
   discover Charlotte's `.env` or load arbitrary dotenv files. Never put the
   token itself in YAML or a tracked file. This is a local connection credential;
   Charlotte keeps the model-provider credentials.

5. From the Walkietalk directory, check the connection without opening radio
   hardware:

   ```bash
   .venv/bin/walkietalk -c config.local.yaml agent-check \
     'Introduce yourself in one short sentence.'
   ```

   Expect a Hermes agent label and a short `Reply:` from Charlotte. Authentication
   errors require checking the matching token on both sides. Connection errors
   require checking the gateway, its published port, and the client URL.

The loopback URL assumes both applications run on the same host. For a separate
radio host, use an SSH tunnel or an authenticated HTTPS reverse proxy and set
the client URL accordingly. Keep the default loopback Docker publishing unless
you deliberately configure another access path.

### Use the Hermes speech provider

The Hermes agent API used here does not provide a speech endpoint. Optional
`tts.backend: hermes` uses a separate, authenticated companion supplied by
Walkietalk. It accepts final text, invokes Hermes's configured speech tool, and
returns a bounded WAV. It does not run another agent turn or choose Charlotte's
model. This companion is distinct from the gateway API on port 8642.

Prerequisites:

- A Walkietalk checkout containing
  `src/walkietalk/hermes_speech_service.py`; see its
  [Hermes speech documentation](https://github.com/bbusenius/walkietalk/blob/main/docs/HERMES-TTS.md).
- A Charlotte Hermes image with `ffmpeg` and the dependencies for your speech
  provider. The supplied Dockerfile includes `ffmpeg` and Edge TTS.
- An explicit `tts.provider` in the **live Hermes profile's** `config.yaml`.
  The example uses Edge with `en-US-AriaNeural`; keep or change that to your
  chosen provider and voice. Provider keys belong in Charlotte's private
  environment/profile, not in Walkietalk. Built-in and configured command
  speech providers are supported by the companion; plugin-only providers are
  not currently supported. Provider account limits and billing still apply.

The following setup runs the speech companion in a separate container using
Charlotte's image and profile mounts. It does not replace or restart the
messaging gateway. The companion publishes only host loopback port 8643 and
uses the existing `API_SERVER_KEY`. Its source is mounted read-only from the
Walkietalk checkout; keep that checkout at the configured location.

From the **Charlotte repository root**, identify the running gateway container:

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}'
```

Set the gateway container name and an absolute path to your Walkietalk checkout,
then start the companion. These values are installation-specific; the two
repositories do not have to be adjacent.

```bash
CHARLOTTE_CONTAINER="your-running-charlotte-container"
WALKIETALK_DIR="/absolute/path/to/walkietalk"
CHARLOTTE_IMAGE="$(docker inspect --format '{{.Image}}' "$CHARLOTTE_CONTAINER")"

speech_env=()
if [ -f .env ]; then
  speech_env+=(--env-file "$PWD/.env")
fi

docker run -d \
  --name charlotte-walkietalk-speech \
  --restart unless-stopped \
  --user "$(id -u):$(id -g)" \
  --volumes-from "$CHARLOTTE_CONTAINER" \
  "${speech_env[@]}" \
  -e HERMES_HOME=/opt/data \
  -e HOME=/opt/data/home \
  -p 127.0.0.1:8643:8643 \
  --mount "type=bind,source=$WALKIETALK_DIR/src/walkietalk/hermes_speech_service.py,target=/opt/walkietalk/hermes_speech_service.py,readonly" \
  --workdir /workspace \
  --entrypoint /opt/hermes/.venv/bin/python \
  "$CHARLOTTE_IMAGE" \
  /opt/walkietalk/hermes_speech_service.py \
  --hermes-root /opt/hermes --host 0.0.0.0
```

Run this as the user who owns the Hermes profile. `--volumes-from` reuses the
existing gateway's profile and workspace mounts. The image ID selects the same
built image; the helper uses Hermes's Python, not Charlotte's project venv.
The repo `.env`, when present, supplies the same environment-file credentials as
the gateway, and the helper also loads the mounted profile's `.env`. If your
gateway obtains credentials from a different private environment file, pass
that file instead. Configuration or packages changed only inside a running
container are not part of its image; put required dependencies in your image
before using them in the companion.

Check startup with:

```bash
docker logs --tail 20 charlotte-walkietalk-speech
```

Expect `Hermes speech service listening on 0.0.0.0:8643`. A missing-token error
means `API_SERVER_KEY` was not supplied through the companion's environment or
profile. The helper refuses to start without a suitable token. A provider error
means the selected Hermes speech provider, its dependencies, or its credentials
need attention; Walkietalk does not substitute another backend.

Set these **selected fields** in Walkietalk, retaining the rest of its required
`tts` fields:

```yaml
tts:
  backend: "hermes"
  hermes_url: "http://127.0.0.1:8643"
  hermes_token_env: "WALKIETALK_HERMES_TOKEN"
```

The voice and provider are set in Hermes, independently of `agent.backend` and
Walkietalk's `tts.grok_*` settings. The same client token can authenticate both
connections. From the Walkietalk directory, generate a WAV without opening radio
hardware:

```bash
mkdir -p recordings
.venv/bin/walkietalk -c config.local.yaml tts-check \
  'Hello. This is the voice configured in Hermes.' \
  --output recordings/hermes-voice.wav
```

Expect a Hermes voice label and `Speech WAV: ... 48000 Hz, mono PCM16 ... No
hardware opened.` Choose a new output filename when repeating the check.
Continue with Walkietalk's documented radio setup once both connections work.

### Manage the speech companion

The companion's restart policy restarts it with Docker unless you explicitly
stop it. Its lifecycle is independent of the messaging gateway:

```bash
docker stop charlotte-walkietalk-speech
docker start charlotte-walkietalk-speech
```

After upgrading its source/image, changing mount locations, or changing
credentials supplied through Docker's environment file, stop and remove **only
the companion**, then repeat the launch command with the current gateway name,
image, and checkout path:

```bash
docker stop charlotte-walkietalk-speech
docker rm charlotte-walkietalk-speech
```

Removing the companion does not remove the gateway or its bind-mounted profile.
Do not use `docker rm -v` or delete the profile. To stop using Hermes speech,
select another Walkietalk voice backend and remove the companion; Charlotte's
agent API and messaging integrations can continue running.

## Telegram Gateway

The first supported Telegram setup is direct-message only: open Telegram, message the bot, and treat every message as intended for Charlotte. Group chats and mention-based behavior are deferred.

Create a Telegram bot with BotFather, then put the token and allowed numeric Telegram user IDs in the repo-local `.env`:

```env
GEMINI_API_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_USERS=
```

`TELEGRAM_ALLOWED_USERS` is a comma-separated list. Start with one user ID and add family members later as needed.

Run the gateway in the foreground:

```bash
runtime/hermes/run.sh gateway run
```

The gateway runs inside the Charlotte Hermes container, so `/workspace` paths are visible to the gateway. Durable records and generated files should still land under mounted local data roots such as `lesson-logs/`, `tablet-slides/`, `generated-images/`, `curricula/`, `field-trips/`, `.backups/`, and `.logs/`.

### Voice Messages

Incoming Telegram voice messages are handled by Hermes' STT layer before they reach Charlotte. The default Charlotte profile config enables local transcription and keyless Edge TTS:

```yaml
stt:
  enabled: true
  provider: "local"
  local:
    model: "base"

tts:
  provider: "edge"
  edge:
    voice: "en-US-AriaNeural"
```

The default Charlotte profile sets `voice.auto_tts: true`, so voice-originating gateway messages get spoken replies by default. Typed messages still get plain text replies. Use `/voice off` in a chat to opt out, `/voice on` to opt back in, or `/voice tts` only when you intentionally want every reply spoken.

The Docker image installs `faster-whisper` and `edge-tts` into Hermes' own runtime venv, and installs `ffmpeg` for audio handling. Charlotte's shared project environment installs `yt-dlp` from `pyproject.toml`; the image supplies Node.js as its JavaScript runtime for full YouTube extraction support. It also installs `libopus0` so the image has the codec needed for future Discord voice-channel support. After changing this runtime image, rebuild and restart the gateway:

```bash
docker build -f runtime/hermes/Dockerfile -t charlotte-hermes:local .
runtime/hermes/run.sh gateway run
```

Hermes caches incoming voice audio under its profile data directory. In this Docker adapter, the host profile directory is bind-mounted into the container:

```text
host:      ~/.hermes-charlotte
container: /opt/data
```

On existing profiles that already have the legacy cache directory, incoming Telegram voice files are saved as `.ogg` files here:

```text
host:      ~/.hermes-charlotte/audio_cache/
container: /opt/data/audio_cache/
```

These are the same files, not separate copies. To flush the cached audio while keeping the directory in place:

```bash
runtime/hermes/clean-audio-cache.sh
```

New Hermes profiles may use `~/.hermes-charlotte/cache/audio/` instead if no legacy `audio_cache/` directory exists.

### Audio Cache Cleanup

Hermes stores gateway voice files in the profile data directory, not under `tablet-slides/` or other curriculum output roots:

```text
host:      ~/.hermes-charlotte/audio_cache/
container: /opt/data/audio_cache/

host:      ~/.hermes-charlotte/cache/audio/
container: /opt/data/cache/audio/
```

Inbound Telegram and Discord voice recordings are saved as files such as `audio_*.ogg`. Gateway TTS replies are saved as files such as `tts_*.mp3` or `tts_*.ogg`. Grok MCP does not store local audio files in the Charlotte setup; it may be called by the agent for reasoning/search, but Hermes handles STT/TTS through the gateway cache above.

Delete all cached gateway audio:

```bash
runtime/hermes/clean-audio-cache.sh
```

Preview what would be deleted:

```bash
runtime/hermes/clean-audio-cache.sh --dry-run
```

## Discord Gateway

The recommended Discord setup is a private, single-purpose `Charlotte` server with one text channel and one voice channel. In that setup, use numeric Discord user IDs for the allowlist:

```env
DISCORD_BOT_TOKEN=
DISCORD_ALLOWED_USERS=
```

Set `discord.require_mention: false` in the Hermes profile config for this private-server pattern. The Charlotte example config uses that behavior so the dedicated Discord channel works like a direct conversation.

Create the bot in the Discord Developer Portal, enable Message Content Intent, and invite it to the private server with `bot` and `applications.commands` scopes. For text testing, the bot needs View Channels, Send Messages, Send Messages in Threads, Read Message History, Use Slash Commands, and Attach Files.

Run the same Hermes gateway command used for Telegram:

```bash
runtime/hermes/run.sh gateway run
```

Test Discord text first. Once text works, test voice-channel joining. Discord slash commands must be selected from the command autocomplete UI; typing literal text such as `/voice join` may not invoke the command. Type `/voice`, choose Charlotte's command, then choose `join`.

### Discord Voice Rooms

The runtime image includes the Opus codec dependency needed for Discord voice-channel support, and `.env.example` includes placeholders for the Discord bot token and numeric allowlist.

For Discord voice rooms, add Connect, Speak, and Use Voice Activity permissions to the bot invite/server permissions. Keep `DISCORD_ALLOWED_USERS` narrow.
