# TOOLS

Local tool conventions for the Charlotte OpenClaw runtime. `AGENTS.md` is the
full contract; these are the container-specific notes.

- Project Python lives at `/workspace/.venv`. Run Charlotte scripts as
  `/workspace/.venv/bin/python /workspace/scripts/<script>.py ...`.
- Standalone images go through the router, never a creative fallback first:
  `/workspace/.venv/bin/python /workspace/scripts/charlotte_image.py --prompt "..." --out /workspace/generated-images/<slug>.png --kind illustration --route quality --json`
- Deliver files to chat with `MEDIA:<absolute path>` — absolute paths only;
  relative `MEDIA:` paths are dropped silently by some channels.
- Writable content roots (bind mounts): `/workspace/curricula`,
  `/workspace/lesson-logs`, `/workspace/tablet-slides`, `/workspace/generated-images`,
  `/workspace/field-trips`, `/workspace/dashboards`, `/workspace/.backups`,
  `/workspace/.logs`, `/workspace/.state`, `/workspace/.scratch`. Other paths
  under `/workspace` are baked into the image and writes there do not survive
  the container.
- Host records referenced from `students.yaml` as `~/...` resolve under
  `/home/node/...` via `CHARLOTTE_HOME_MOUNTS`.
- The `image` tool only reads paths inside the workspace. When a file lives
  outside it (e.g. a Signal attachment under `/home/node/.local/share/...`),
  copy it to `/workspace/.scratch/` (create the directory if needed), analyze
  it there, and delete the copy afterward. Never park working copies in
  `generated-images/`, `tablet-slides/`, or other content roots — those hold
  finished artifacts only. `.scratch/` persists across container replacement
  so interrupted workflows can resume, but its contents remain temporary and
  must be cleaned by the owning workflow after success.
- Voice replies: when the inbound message contains the marker
  `[Audio transcript (machine-generated, untrusted)]`, the user spoke a
  voice note — end your reply with a line containing exactly
  `[[tts:speed=1]]` so the reply is also delivered as speech (the directive
  is stripped from the visible text). The body is required: a bare `[[tts:]]`
  is ignored by the parser and shows up as literal text. Never add a tts
  directive when the user typed.
- Google Maps and Grok vision/search capabilities go through MCP via the
  `mcporter` CLI (configured in `~/.mcporter/mcporter.json`). Examples:
  - `mcporter call 'google_maps.maps_search_places(query: "children museums near Chicago")'`
  - `mcporter call 'google_maps.maps_geocode(address: "...")'`
  - `mcporter call 'grok.chat_with_vision(image_path: "/home/node/...", prompt: "...")'`
  - `mcporter call 'grok.live_search(query: "...")'`
  Use `mcporter list` to see every server and tool. If a call fails because a
  server or key is missing, say so instead of guessing.
