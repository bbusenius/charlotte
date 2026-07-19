# Runtime Tool Surface

Charlotte skills assume a small set of runtime capabilities. Runtime adapters can provide these through local CLIs, mounted files, MCP servers, native runtime tools, or a combination of those mechanisms.

## Core Tools

| Capability | Used by | Provider |
| --- | --- | --- |
| Workspace file read/write | All generation skills | Runtime filesystem access to the repo and ignored content roots |
| Python project CLIs | Logging, slides, sync, image routing | `.venv` installed from `pyproject.toml` |
| Image generation | Materials, tablet slides, standalone image requests | `scripts/charlotte_image.py` plus `image-generation.yaml` routes |
| HTML to PDF | `mason-print-design`, `mason-materials-builder` | WeasyPrint from `pyproject.toml` |
| SVG to PDF/PNG | `mason-print-design`, `mason-materials-builder` | System `inkscape` |
| Offline field-trip bundles | `scripts/build_offline_field_trips.py` | System `pandoc` >= 2.19 (`--embed-resources`; distro packages can be older — both Dockerfiles pin an upstream release) plus ImageMagick (`magick`/`convert`); ImageMagick also backs `mason-print-design` PDF previews |
| Browser automation | Lexile lookup | Playwright plus `tools.chrome_path` in `runtime.yaml` |
| Spreadsheet append | `hsd-time-log`, `hsd-book-log` | `xlsx-append` from `pyproject.toml` |
| Spreadsheet read | `hsd-records-read`, `mindfeast-weekly-slides` | `openpyxl` from `pyproject.toml` plus mounted workbook paths |
| Dashboard HTML generation | `hsd-dashboard-show` | `homeschool_dashboard` from `pyproject.toml` plus mounted workbook paths |
| Signal message state | `hsd-time-log`, `hsd-book-log` | `signal-sieve` CLI plus configured Signal capture state |
| Voice-note transcription | Chat-gateway voice input | `scripts/transcribe_media.py` (faster-whisper from `pyproject.toml`); Hermes uses its native `stt` layer instead, OpenClaw calls the script via its CLI transcription hook |
| MindFeast remote control | `mindfeast-slide-sync`, `mindfeast-slide-trigger`, `mindfeast-weekly-slides` | HTTP POST from the runtime network |

## External AI And Research Tools

| Capability | Used by | Required surface |
| --- | --- | --- |
| Google Maps places/geocoding/directions | `mason-field-trip-planner` | Google Maps MCP or equivalent runtime tools |
| Web search/fetch | `mason-field-trip-planner`, book lookup fallback, general research | Runtime web tools or equivalent MCP |
| Vision over local images | `hsd-time-log`, `hsd-book-log` | Grok Vision MCP or equivalent vision-capable runtime tool |
| Live search fallback | `hsd-book-log` | Grok live search MCP or equivalent search-capable runtime tool |
| Runtime-native image fallback | `mason-materials-builder`, `mindfeast-slide-builder` | Optional runtime image tool used only after `charlotte_image.py` exits `2` |

Skills should name the capability they need, not a host-specific installation path. Runtime adapters own the mapping from capability to tool names, MCP servers, environment variables, and permission policy.

## Hermes Status

The single-container Hermes adapter currently provisions the local CLI/toolchain layer:

- Installs Charlotte Python dependencies from `pyproject.toml`.
- Installs `inkscape` in the image.
- Mounts `.env`, `runtime.yaml`, `image-generation.yaml`, `students.yaml`, and ignored content roots at runtime.
- Supports configurable `~/...` host data mounts through `CHARLOTTE_HOME_MOUNTS`.
- Can consume host-owned `signal-sieve` state when the Signal config/database/attachments are mounted.

Hermes does not currently provision container-owned Signal capture. It also does not yet define a committed MCP server configuration for Google Maps or Grok tools. Those capabilities must be provided by the active Hermes toolset or treated as unavailable by the skill.

For stdio MCP servers, Hermes does not pass through arbitrary environment variables. MCP credentials must be configured in the server's own `env` mapping or provided by an equivalent remote service.

## OpenClaw Status

The Docker OpenClaw adapter ([runtime/openclaw/](../runtime/openclaw/), experimental) provisions the same local CLI/toolchain layer as Hermes:

- Installs Charlotte Python dependencies from `pyproject.toml` into `/workspace/.venv` (uv-managed Python 3.12 on the OpenClaw base image).
- Installs `inkscape`, Chromium, and `ffmpeg` in the image.
- Mounts `.env`, `runtime.yaml`, `image-generation.yaml`, `students.yaml`, and ignored content roots at runtime.
- Supports the same `CHARLOTTE_HOME_MOUNTS` host data mounts, at `/home/node/...`.
- Can consume host-owned `signal-sieve` state when the Signal config/database/attachments are mounted.

OpenClaw discovers the canonical `skills/` tree natively as its workspace skills directory, reads `AGENTS.md` as the workspace operating file, and delivers files with the `MEDIA:<absolute path>` convention `AGENTS.md` already teaches. Sub-agent spawns map to `sessions_spawn` with `maxSpawnDepth: 2` set in the adapter config.

OpenClaw has no in-loop MCP client; Google Maps and Grok capabilities go through the bundled `mcporter` skill, with stdio servers running inside the container. The image bakes the `mcporter` CLI, and the adapter seeds `mcporter.json` with the Google Maps and Grok servers (see [runtime/openclaw/README.md](../runtime/openclaw/README.md)); keys come from `.env` via the container environment. Vision and web search/fetch can also use OpenClaw's native tools. Capabilities not configured should be reported missing by the skill, per the contract.

When adding a new runtime adapter, use this page as the checklist before claiming that a skill is supported end to end.
