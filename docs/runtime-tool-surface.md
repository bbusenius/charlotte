# Runtime Tool Surface

Charlotte skills assume a small set of runtime capabilities. Runtime adapters can provide these through local CLIs, mounted files, MCP servers, native runtime tools, or a combination of those mechanisms.

## Core Tools

| Capability | Used by | Provider |
| --- | --- | --- |
| Workspace file read/write | All generation skills | Runtime filesystem access to the repo and ignored content roots |
| Python project CLIs | Logging, slides, sync, image routing | `.venv` installed from `pyproject.toml` |
| Image generation | Materials, tablet slides, standalone image requests | `scripts/charlotte_image.py` plus `runtime.yaml` routes |
| HTML to PDF | `mason-print-design`, `materials-builder` | WeasyPrint from `pyproject.toml` |
| SVG to PDF/PNG | `mason-print-design`, `materials-builder` | System `inkscape` |
| Browser automation | Lexile lookup | Playwright plus `tools.chrome_path` in `runtime.yaml` |
| Spreadsheet append | `hsd-time-log`, `hsd-book-log` | `xlsx-append` from `pyproject.toml` |
| Signal message state | `hsd-time-log`, `hsd-book-log` | `signal-sieve` CLI plus configured Signal capture state |
| MindFeast remote sync | `mindfeast-slide-sync`, `mindfeast-weekly-slides` | HTTP POST from the runtime network |

## External AI And Research Tools

| Capability | Used by | Required surface |
| --- | --- | --- |
| Google Maps places/geocoding/directions | `field-trip-planner` | Google Maps MCP or equivalent runtime tools |
| Web search/fetch | `field-trip-planner`, book lookup fallback, general research | Runtime web tools or equivalent MCP |
| Vision over local images | `hsd-time-log`, `hsd-book-log` | Grok Vision MCP or equivalent vision-capable runtime tool |
| Live search fallback | `hsd-book-log` | Grok live search MCP or equivalent search-capable runtime tool |
| Runtime-native image fallback | `materials-builder`, `tablet-slide-builder` | Optional runtime image tool used only after `charlotte_image.py` exits `2` |

Skills should name the capability they need, not a host-specific installation path. Runtime adapters own the mapping from capability to tool names, MCP servers, environment variables, and permission policy.

## Hermes Status

The single-container Hermes adapter currently provisions the local CLI/toolchain layer:

- Installs Charlotte Python dependencies from `pyproject.toml`.
- Installs `inkscape` in the image.
- Mounts `.env`, `runtime.yaml`, `students.yaml`, and ignored content roots at runtime.
- Supports configurable `~/...` host data mounts through `CHARLOTTE_HOME_MOUNTS`.
- Can consume host-owned `signal-sieve` state when the Signal config/database/attachments are mounted.

Hermes does not currently provision container-owned Signal capture. It also does not yet define a committed MCP server configuration for Google Maps or Grok tools. Those capabilities must be provided by the active Hermes toolset or treated as unavailable by the skill.

For stdio MCP servers, Hermes does not pass through arbitrary environment variables. MCP credentials must be configured in the server's own `env` mapping or provided by an equivalent remote service.

When adding a new runtime adapter, use this page as the checklist before claiming that a skill is supported end to end.
