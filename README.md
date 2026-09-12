# Charlotte

A local-first homeschool agent for records, planning, materials, and review.

An open-source project from [MindFeast](https://mindfeast.life/), built and used in a real homeschooling family.

Charlotte connects the files and tools a family already controls. It can turn short family messages into lesson and reading records, answer questions from those records without sending whole spreadsheets to a model, build lessons and printable materials, plan field trips, and create optional MindFeast review slides. Family records, purchased curricula, generated work, and credentials remain local and are excluded from the repository.

## What Charlotte can do

- Keep a durable record of what was actually taught: captured photos, screenshots, and voice notes, their extracted text, and a written account of each session.
- Log lesson time and books to Homeschool-Dashboard-compatible spreadsheets.
- Query those records, send a weekly household digest of how learning went, and generate local visual dashboards.
- Build lessons, units, curricula, field trips, and print-ready materials.
- Use a configurable local pedagogy knowledge base; a public-domain Charlotte Mason pack is included.
- Create, validate, sync, and trigger optional MindFeast tablet slides, and push a student's MindFeast Agent Alarm.
- Run directly in a coding agent or through the included always-on Hermes and OpenClaw adapters.

Charlotte does not require MindFeast, Signal, a messaging gateway, or cloud-hosted family records. Enable only the workflows and external tools you want.

## Quick start

Requirements: Git, Python 3.12 or newer, and a skill-aware coding agent such as Codex, Claude Code, or OpenCode.

```bash
git clone https://github.com/bbusenius/charlotte.git
cd charlotte
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
cp students.yaml.example students.yaml
```

Edit the ignored `students.yaml` with your own local paths and fictional-or-real household configuration. Then open the repository in your coding agent and try a workflow that needs no external account, for example:

> Build a short Charlotte Mason nature-study lesson about the Moon.

Signal capture, image generation, spreadsheet records, Docker runtimes, and MindFeast tablet control have additional optional configuration described below. Run the test suite with `.venv/bin/python -m pytest`.

## How it works

Charlotte allows users to log time and books through [Signal](https://signal.org/) chats. It uses [signal-sieve](https://github.com/bbusenius/signal-sieve) to strip metadata and protect privacy. AI agents only receive the minimal amount of data they need to do their job, not the kitchen sink. Charlotte also comes with on-demand planning/creation skills (field trips, materials, MindFeast slides), all reading a local pedagogy wiki for framing. Per-student metadata lives in `students.yaml` at the repo root (see [Student registry](#student-registry)).

Charlotte is **runtime-neutral by design**: the repo itself is the agent — skills, operating instructions, pedagogy packs, and family records — and the harness that runs it is swappable. Use it in one of two ways:

1. **As a standalone tool** inside a coding agent such as Claude Code, Codex, or OpenCode.
   - Just clone the repo and run skills in your coding agent of choice.
2. **As an always-on chat agent** on the harness of your choice — [Hermes](https://github.com/nousresearch/hermes-agent) ([runtime/hermes/](runtime/hermes/)) or [OpenClaw](https://openclaw.ai) ([runtime/openclaw/](runtime/openclaw/)) — with a chat gateway (Telegram recommended).
   - Tell the agent to run workflows in chat, or schedule skills with the harness's `cron`.
   - Both adapters run the identical skill set against the identical family data: switching harnesses is a matter of launching a different `runtime/<name>/run.sh`, and records logged under one runtime are fully visible to the other. The [runtime contract](docs/runtime-contract.md) defines what any new adapter must provide, so further harnesses can be added without touching the skills.

### Lesson logging (`/lesson-log`)

The primary record. One directory per teaching session under `lesson-logs/`:

```
lesson-logs/eliana/grade-3/2026/07/24/
    language-arts-literature-lesson-112-guide-words/
    math-lesson-45-comparing-rounded-amounts/
    science-forest-plot-survey/
        log.md          what was taught, how it went, what comes next
        messages.md     what the parent said: text verbatim, voice transcribed
        images.md       what Charlotte saw: description plus visible text
        videos.md       videos watched: URL, what it was about, transcript
        sources/        image-01.jpg, image-02.jpg, voice-01.ogg
```

Year, month, and day directories make all of one school day's sessions visible together. Each session name begins with its configured subject. Files in `sources/` are named only by kind and arrival order. What an image shows — which workbook page, whether it is filled in, what the scene is — lives in `images.md`, and the real page numbers also go in the log's frontmatter, so "what page are we on in Language Arts?" is answerable from a summary. A watched video is logged the same way: the URL, the transcript, and what the video taught live in `videos.md`.

1. A parent describes a lesson — in a [typed queue](docs/ingest-contract.md) or just in conversation — with any photos, screenshots, voice notes, or video links
2. The `lesson-log` skill:
   - Reads every image with a vision-capable runtime tool and transcribes voice notes
   - Fetches the transcript of any video URL and records what the video is about
   - Looks up the lesson through its configured curriculum index and native sources when available
   - Copies the captured media into the session and writes the extracted text alongside it
   - Writes the account of what was covered and how it went

Keeping the extracted text, not just the photos, is what makes the record useful later: a year of captured pages and watched videos is searchable, and it is enough to plan from for a subject with no digital curriculum.

### Homeschool Dashboard time projection (`/hsd-time-log`)

A spreadsheet row is a one-line receipt of a lesson log, and the dashboard renders it when you hover a date.

1. Run it whenever you want the workbooks current — end of day, weekly, or after a month away
2. The `hsd-time-log` skill finds logged sessions with no row yet and appends them

It only ever adds missing rows. It never updates or overwrites an existing one, so hand edits survive, and running it twice writes nothing the second time. Sessions missing either start or end time are reported rather than written, since Homeschool-Dashboard needs both.

### Homeschool Dashboard book logging (`/hsd-book-log`)

1. Messages (book titles or cover photos) are sent to a per-child book queue (configured via `reading.inbox` in `students.yaml`)
2. **signal-sieve** captures them the same way
3. The `hsd-book-log` skill:
   - Reads text / extracts title + author from cover images with a vision-capable runtime tool
   - Looks up metadata in order: **Lexile → Open Library → live search** (last-resort confirmation/search)
   - Writes a row to the child's reading-list spreadsheet (sheet chosen by position: "read by" vs "read to")
   - Marks messages as processed

### Homeschool Dashboard record queries (`/hsd-records-read`)

Answers questions about what a student has done, without pulling whole spreadsheets or whole lesson logs into the model. Content questions ("what was the last thing Alice did in Math?", "have we covered guide words?") are answered from the lesson logs, which hold the full account, the captured page text, and video transcripts. Hours and totals are answered from the time workbook, where the computation lives and where history from before lesson logging still is. Books come from the reading-list workbook. Given a question, the skill:

1. Resolves the student through `students.yaml`
2. Runs `scripts/hsd_read.py` against the configured workbook
3. Answers from compact JSON rows

The helper supports time-log filters by subject, date range, text query, and latest/limit. It supports reading-list filters by text query, configured list type (`read_by_self` / `read_to`), and latest/limit.

### Homeschool Dashboard viewing (`/hsd-dashboard-show`)

Generates the visual [Homeschool Dashboard](https://github.com/bbusenius/Homeschool-Dashboard) HTML for a configured student. Given a request such as "show me Alice's homeschool dashboard", the skill:

1. Resolves the student through `students.yaml`
2. Runs `scripts/hsd_dashboard.py` against the student's `time_tracking_spreadsheet`
3. Writes `dashboards/<student>.html`
4. Opens, links, or reports the generated HTML path depending on the active runtime

This path is for visual dashboards. Conversational questions about logged records should use `/hsd-records-read`. A weekly household digest of highlights and things that need attention is `/weekly-review`.

### Weekly review (`/weekly-review`)

A short household digest of the week's lesson logs for the adults who are responsible for the children. Given a request such as "how did the week go" or `/weekly-review`, the skill:

1. Resolves students through `students.yaml` (every student, or one named student)
2. Reads the week's lesson logs through `scripts/lesson_log_read.py`
3. Replies with one chat message: highlights, things that need attention, and what to do next

It does not recap classes one by one, write a file, create slides, or touch a spreadsheet. The lesson logs remain the durable record. Default range is the seven calendar days ending today. The skill is unattended-safe and meant to be scheduled weekly on the harness cron; the digest is the conversation reply.

### Field trip planning (`/mason-field-trip-planner`)

Distinct from the logging pipelines — a planning skill, not Signal-driven. Given a theme (often lessons already studied) and a location in the prompt, the `mason-field-trip-planner` skill:

1. Reads the theme and, if curriculum files are referenced, the specific lessons from wherever `students.yaml` points (third-party curricula live under `curricula/third-party/`)
2. Queries the Google Maps MCP for candidate venues near the location, supplemented by WebSearch for natural / outdoor places that Google Maps undercounts (trout streams, prairie remnants, trailheads, birding hotspots, etc.)
3. Ranks 3–5 options with Google Maps + website/social links
4. On selection (or with `--auto`), produces a full markdown field trip plan

Plans are grounded in the local pedagogy wiki at `pedagogies/charlotte-mason/wiki/` (Charlotte Mason) — every trip is framed around [[concepts/science-of-relations]], uses [[concepts/narration]] as post-trip assessment, and names Mason's canonical on-site activities (nature study, picture study, music appreciation, handicraft observation) where the venue admits them.

### Material creation (`/mason-materials-builder`)

Also a planning/creation skill rather than a Signal-driven pipeline. Given a prose description (optionally referencing a student or specific lessons), the `mason-materials-builder` skill:

1. Resolves the student (if any) via `students.yaml` and, if curriculum files are referenced, reads the relevant lessons from the paths `students.yaml` resolves them to
2. Invokes `mason-aesthetics` (peer skill) for aesthetic direction — typography tradition, palette direction, illustration register, font-availability check
3. Invokes `mason-print-design` (peer skill) for the rendering toolchain (WeasyPrint for HTML→PDF, Inkscape for SVG→PDF/PNG) and print-fidelity rules, including a lettering carve-out so hand-lettered or decorative text can be baked into the image when lettering *is* the art
4. Generates illustrations through `scripts/charlotte_image.py`, using the image routes configured in local `image-generation.yaml`
5. Writes the finished material to the current working directory (or `--out PATH`), naming the image route, source, and model in the final message

Material types include printable worksheets, copywork pages, flashcards, narration templates, picture-study cards, period maps, posters, and tablet-first illustrations. Grounded in the same Charlotte Mason wiki at `pedagogies/charlotte-mason/wiki/`, `mason-aesthetics` roots its guidance in [[concepts/children-are-born-persons]], [[concepts/education-is-atmosphere-discipline-life]], [[concepts/knowledge-as-food]], [[concepts/living-books]], [[concepts/science-of-relations]], and [[concepts/narration]].

`mason-aesthetics` and `mason-print-design` are internal peer skills — invoked *by* creation skills such as `mason-materials-builder`, not directly by the user.

### AO picture study (`/ao-picture-study`)

Prepares the next AmblesideOnline artist-rotation picture study for a configured student. The skill parses AO's current year/term schedule, advances from a minimal per-student last-created cursor, finds the actual artwork with Wikimedia Commons as the first source, and requires the environment's default image-understanding capability to inspect the artwork itself. It also requires at least one museum, archive, scholarly, or equivalent tier-1/2 anchor source for the narration; discovery sources such as Wikipedia cannot satisfy that gate. It persists the artwork and finished narration as a reusable individual study linked from the student's configured AO curriculum entrypoint. It creates a short grade-appropriate single-narrator audio study with the environment's available TTS capability, packages the artwork, audio, and a two-line title/artist/date label as an informational MindFeast slide, validates and syncs it, selects that exact slide as next, and only then advances the cursor. Lesson logs remain independent until the study is actually taught.

### AO composer study (`/ao-composer-study`)

Prepares the next AmblesideOnline composer-rotation selection for a configured student. The primary informational MindFeast slide pairs the real AO-selected recording with a generated image and displays only the work title and composer; a secondary informational slide contains a short narrated composer/work study and its own generated image. Both are archived as an exact reusable curriculum study, validated, and synced, but only the primary listening slide is selected next. AO selections assigned four weeks are delivered twice without duplicating the podcast. A per-student cursor preserves the flexibility to give different tablets independent schedules or copy one student's position to another. The shared `yt-dlp` and `ffmpeg` dependencies acquire audio from AO's links when a suitable public-domain recording is not readily available.

### MindFeast weekly slides (`/mindfeast-weekly-slides`)

Generates a small weekly review set for the MindFeast Android lock-screen app from a student's time-tracking spreadsheet. Given a student and optional week, the skill:

1. Reads the student's logged lesson rows via `skills/mindfeast-weekly-slides/scripts/collect_week.py`
2. Reads configured curriculum files or other known lesson materials when available to understand what was actually covered
3. Chooses a small set of useful slide opportunities, usually fewer than 8 and sometimes 0
4. Uses `mindfeast-slide-builder` to create MindFeast-compatible slide folders under the student's `tablet_slides_dir`
5. Validates each slide package
6. Optionally POSTs to the student's MindFeast remote sync endpoint and waits for the sync result before reporting

Slide types are content-driven: informational cards, multiple-choice questions, free-text questions, and essay/narration prompts are all valid. If a slide is based on a known public-domain artwork, the skill prefers the actual image from Wikimedia Commons rather than generated art.

The existing package contract is documented in [MindFeast Slide Package Format, Version 1](docs/mindfeast-slide-format-v1.md). Version 1 labels the specification; slide packages do not contain a format-version field.

### MindFeast slide sync (`/mindfeast-slide-sync`)

Syncs already-created tablet slide packages to the student's configured MindFeast remote endpoint. Given a student, it reads `mindfeast.remote_url` and `mindfeast.remote_token` from `students.yaml`, POSTs once to `<remote_url>/api/sync`, and reports the endpoint host/path and response summary without printing the token. If no student is named, it syncs every student with complete MindFeast sync config.

### MindFeast slide trigger (`/mindfeast-slide-trigger`)

Triggers a configured tablet to show a MindFeast slide now. Given a student, it reads `mindfeast.remote_url` and `mindfeast.remote_token` from `students.yaml`, POSTs once to `<remote_url>/api/trigger`, and reports the endpoint host/path, response summary, and returned `slideId` without printing the token. If no student is named, it triggers every student with complete MindFeast remote config.

### MindFeast Agent Alarm (`/mindfeast-agent-alarm`)

Pushes a morning atmosphere to a student's MindFeast Agent Alarm app over LAN. Given a student, it reads `agent_alarm.remote_url` and `agent_alarm.remote_token` from `students.yaml` (not `mindfeast.remote_*` lock-screen settings) and can set status, wake audio, a picture, notes, theme, clock format, wake time, repeat days, and enable/disable. Reports the student, endpoint host/path, and each operation without printing the token. If no student is named, it pushes every student with complete Agent Alarm config. Two students may share one URL when they share a tablet.

## Student registry

Household and per-student metadata lives in `students.yaml` at the repo root. This is the single source of truth for display name, grade, aliases, concrete curriculum index files (with optional identity, aliases, and subject overrides), subjects, time-tracking spreadsheet path, tablet slide directory, MindFeast remote sync config, MindFeast Agent Alarm config, the optional capture `inbox`, and reading list config (spreadsheet path, sheet indices, its own optional `inbox`). Its top-level `schedules:` map registers shared forward-looking family schedules. Skills read this registry rather than hard-coding household paths, so the repo stays portable — another family can ship their own `students.yaml`.

Adding a student:

1. Add an entry under `students:` in `students.yaml`
2. Put curriculum content under `curricula/` (`curricula/third-party/` for purchased/imported material) and list its concrete lookup entrypoint in the student's `curricula` map
3. Skills that need the metadata will pick it up automatically

MindFeast lock-screen sync is configured per student:

```yaml
mindfeast:
  remote_url: http://192.0.2.10:8787
  remote_token: ""
```

`remote_url` is the base URL for the tablet's MindFeast remote server. `remote_token` is the bearer token copied from MindFeast remote settings. Keep real tokens in local `students.yaml`, not in committed examples.

MindFeast Agent Alarm is per student and a separate Android app from lock-screen MindFeast:

```yaml
agent_alarm:
  remote_url: http://192.0.2.20:8787
  remote_token: ""
```

`agent_alarm.remote_url` is scheme, host, and port only. `agent_alarm.remote_token` is the bearer token from Agent Alarm settings. Do not reuse `mindfeast.remote_*` values here. Two students may share one URL when they share a tablet.

Shared schedules are a planning layer, not records of completed lessons. Use the human title as the map key; `path` is repository-relative and must be under `schedules/`. The Charlotte LAN page lists configured schedules and serves only those configured paths.

```yaml
schedules:
  Family Weekly Rhythm:
    description: The shared weekly teaching rhythm for the household.
    school_year: 2026-2027
    students: [alice, charlie]
    path: schedules/2026-2027/family-weekly-rhythm.html
```

## Pedagogy packs

Pedagogical grounding is configurable. A **pedagogy pack** is a directory under `pedagogies/` containing `raw/` (immutable source documents) and `wiki/` (an LLM-maintained knowledge base built from them), following the schema in [pedagogies/AGENTS.md](pedagogies/AGENTS.md). The pack wiki implements Andrej Karpathy's [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) pattern — instead of retrieving from raw documents at query time (RAG), the LLM ingests sources once into a persistent, cross-referenced "living wiki" and keeps it current as sources and questions accumulate. Charlotte ships with `pedagogies/charlotte-mason/` — built from Charlotte Mason works that are not restricted by U.S. copyright law — as the default. See [Third-party notices](THIRD_PARTY_NOTICES.md) for provenance and terms.

To use your own pedagogy or curriculum philosophy:

1. Create `pedagogies/<your-pack>/raw/` and drop your source materials there. Every pack except `charlotte-mason` is gitignored, so purchased or copyrighted texts stay on your machine and cannot be committed by accident.
2. Point `pedagogy.path` at the pack in local `runtime.yaml`.
3. Ask Charlotte to ingest the sources — the wiki is built and maintained for you.

General pedagogical questions and pedagogy-aware skills read the active pack's wiki. The visual register for generated images and materials is configured separately by `pedagogy.aesthetics` (default `skills/mason-aesthetics`) — swap in your own aesthetics file to change how every generated illustration looks without changing anything else.

The `mason-*` skills (`mason-lesson-plan-builder`, `mason-unit-builder`, `mason-curriculum-builder`, `mason-field-trip-planner`, `mason-materials-builder`, `mason-aesthetics`, `mason-print-design`) are the exception: they are Charlotte Mason tools by design, with Mason's method built into their workflows, and always read the `charlotte-mason` pack. They ship as an optional authoring toolkit for families who want lessons, units, curricula, trips, and materials in Mason's method — most families working entirely from purchased curricula only need the logging, dashboard, and tablet skills, which are pedagogy-neutral. Authoring toolkits for other pedagogies are welcome as contributions.

## Local content roots

This repository tracks the homeschool agent system, reusable skills, scripts, examples, and pedagogy scaffolding. It does not track family content, paid curriculum text, generated lesson content, generated slide packages, standalone generated images, trip plans, spreadsheets, or backups.

The following paths are writable local content roots and are intentionally gitignored:

- `curricula/` — paid/imported native curriculum sources and indexes plus generated curricula, units, lessons, and lesson assets
- `lesson-logs/` — the record of what was actually taught: one directory per session holding the captured photos and voice notes, their extracted text, video transcripts, and the written log
- `tablet-slides/` — generated Android lock-screen slide packages
- `generated-images/` — standalone generated images that are not tablet slide packages or printable materials
- `field-trips/` — generated field trip plans
- `dashboards/` — generated Homeschool Dashboard HTML
- `schedules/` — forward-looking household schedule artifacts, which may be school-year or calendar anchored
- `.backups/` — local spreadsheet backups created during logging workflows
- `.logs/` — local sync and long-running operation logs

Docker/OpenClaw/Hermes runtimes should treat these paths as local data volumes, not source code.

## Setup

Python scripts live in a project-local venv.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

This installs the Python dependencies from `pyproject.toml`, including `signal-sieve`, `xlsx-append`, `faster-whisper`, `weasyprint`, and `yt-dlp` into `.venv/bin/`. The Lexile lookup uses Playwright with a system Chrome/Chromium executable; audiobook transcription and AO composer-study recording extraction use `ffmpeg`/`ffprobe`. Full YouTube support also needs a JavaScript runtime; both shipped Docker runtimes provide Node.js.

Install non-Python rendering/browser tools with your system package manager:

```bash
sudo apt install chromium ffmpeg inkscape
```

### Capture setup

Material reaches Charlotte two ways, and both are first-class. See [the ingest contract](docs/ingest-contract.md) for the full picture.

**Conversation** needs no setup at all. Tell Charlotte what you covered and attach the photos. This is the default, and a student with no `inbox` block in `students.yaml` works this way.

**A typed queue** is optional and worth it if you want terse messages or scheduled unattended runs: the queue's name says which workflow and which student, so nothing has to be inferred. Signal via `signal-sieve` is the implemented adapter; the contract itself is transport-neutral.

The Charlotte install provides the `signal-sieve` CLI in `.venv/bin/`, which is enough to read captured messages and mark them processed when `signal-sieve` config and data already exist.

Signal capture also needs a running service. In the currently supported setup, that service is host-owned: `signal-cli` and `signal-sieve listen` run on the host, while Hermes-in-Docker mounts the host `signal-sieve` config, database, and attachments. Nothing else requires it — conversational logging, Telegram chat, curriculum/material generation, tablet slides, and MindFeast sync all work without Signal.

Host-owned Signal capture setup belongs to local operator provisioning. See [runtime/hermes/](runtime/hermes/) for the Docker mount configuration Charlotte expects when Hermes consumes host-captured Signal messages.

### Runtime configuration

Non-secret machine/tool settings live in local `runtime.yaml`, which is ignored. To override defaults, copy the example and edit it:

```bash
cp runtime.yaml.example runtime.yaml
```

Currently supported:

```yaml
pedagogy:
  path: pedagogies/charlotte-mason    # active pedagogy pack
  aesthetics: skills/mason-aesthetics # visual register for generated images/materials

logging:
  lesson_log: true    # the primary record of what was taught (system of record)
  time: true          # capture clock times on lessons
  hsd: true           # also project rows into Homeschool-Dashboard spreadsheets

tools:
  chrome_path: /usr/bin/google-chrome-stable
```

`logging` is global, not per student. `hsd: true` requires both `lesson_log: true`, because spreadsheet rows are projected from lesson logs, and `time: true`, because Homeschool-Dashboard needs start and end times.

The `pedagogy` block selects the active pedagogy pack and aesthetics skill (see [Pedagogy packs](#pedagogy-packs)); when absent, the Charlotte Mason defaults apply. `scripts/lexile/lookup.py` uses `tools.chrome_path` for its Playwright browser executable. Leave `runtime.yaml` absent if the defaults work.
If `tools.chrome_path` is absent or points at a path that does not exist in the current runtime, the script searches common Chrome/Chromium executable names such as `google-chrome-stable` and `chromium`.

Image-generation route settings live in local `image-generation.yaml`, which is ignored. Copy the example and edit the route models/keys for your machine:

```bash
cp image-generation.yaml.example image-generation.yaml
```

The default route is `quality`. Route `fast` is reserved for fast/cheap/simple generation and receives the configured aesthetics skill's compact image summary when the file provides one (the full text otherwise); all other routes receive the full aesthetics skill text as image prompt context unless the caller overrides `--prompt-mode`.

In the Hermes Docker runtime, `runtime/hermes/run.sh` also serves a small local Charlotte info page over plain HTTP (default port `8788`) and prints a scannable QR so a tablet on the same LAN can open it. The `charlotte-url` skill re-shares that URL and QR on demand.

Secret local settings live in ignored `.env`. Copy the example and fill only the keys your local runtime needs:

```bash
cp .env.example .env
chmod 600 .env
```

Currently used keys can include direct provider keys such as `GEMINI_API_KEY` and `XAI_API_KEY`, plus runtime adapter keys such as `NANOGPT_API_KEY` when the active runtime uses NanoGPT. Image-generation routes are configured in ignored `image-generation.yaml`, not hard-coded in the skills. `scripts/charlotte_image.py` reads repo-local `.env` for these route variables during local Claude/Codex use. Runtime adapters document their own setup in their runtime directories, including configurable Docker mounts for host files referenced from `students.yaml`.

### Image routing

Standalone image requests and skill-generated illustrations go through `scripts/charlotte_image.py`. The router reads ignored `image-generation.yaml`, selects the named route, builds the Charlotte prompt, and calls that route's configured source/model. The example configuration uses `quality` for the default high-quality route and `fast` for lower-cost/simple generation.

Agents should pass the user's requested subject and constraints plainly to `--prompt`; they should not invent style adjectives, lighting, camera language, scenery, props, or emotional tone unless the user asked for them. All non-fast routes receive the full text of the configured aesthetics skill (`pedagogy.aesthetics` in `runtime.yaml`, default `skills/mason-aesthetics/SKILL.md`) as prompt context — any markdown file works as-is. Route `fast` uses the aesthetics file's `#### Image-router summary` section when one exists (a short profile originally added for weaker image models that follow long prompts poorly); when the file has no such section, the fast route receives the full text like every other route. If fast-route results degrade with a ported aesthetics file, adding that section is the fix. The script reports the actual saved path because providers may return a different image format than the requested file extension, and JSON includes the resolved `route`, `source`, `model`, and `prompt_mode`.

Use `--dry-run` to inspect the resolved route and final provider prompt without calling an image provider or writing files:

```bash
.venv/bin/python scripts/charlotte_image.py \
  --prompt "a monarch butterfly on milkweed, no text" \
  --out generated-images/monarch.png \
  --kind illustration \
  --route quality \
  --dry-run --json
```

### Agent runtimes

Charlotte's core scaffolding is runtime-neutral. `AGENTS.md`, `skills/`, `students.yaml`, the local content roots, and the helper scripts are canonical. The [runtime contract](docs/runtime-contract.md) defines the shared expectations for any runtime adapter added to this repo, and the [runtime tool surface](docs/runtime-tool-surface.md) lists the concrete local, MCP, and runtime-native capabilities skills expect.

Signal remains the structured workflow queue through `signal-sieve`.

Hermes Docker runtime support lives in [runtime/hermes/](runtime/hermes/). Experimental OpenClaw Docker runtime support lives in [runtime/openclaw/](runtime/openclaw/).

### Homeschool-Dashboard-compatible records

The `hsd-time-log` and `hsd-book-log` skills write to spreadsheet records compatible with [Homeschool-Dashboard](https://github.com/bbusenius/Homeschool-Dashboard). Workbook paths live in `students.yaml`, so local Codex/Claude usage can keep host-native `~/...` paths. Docker runtimes must mount any host directories containing those workbooks, and host-owned Signal capture also requires mounting `signal-sieve` config/data paths; the Hermes adapter does both with `CHARLOTTE_HOME_MOUNTS`.

Time records are a projection of the lesson logs, not a parallel record. `hsd-time-log` only adds rows for sessions that have a log and never modifies an existing row, so pre-existing history and hand edits are both safe.

### Material creation prerequisites

`mason-materials-builder` additionally relies on:

- **Image routes** in ignored `image-generation.yaml` when a material needs generated images. `scripts/charlotte_image.py` uses the configured route; direct Google via `scripts/gemini_image.py` is one available backend, not a required default.
- **WeasyPrint** — HTML → PDF rendering, invoked from `mason-print-design`. Installed by `.venv/bin/python -m pip install -e .`; system libraries such as `libpango` and `libcairo` may still be required depending on the platform.
- **Inkscape** — SVG → PDF/PNG rendering. Install from your package manager (`apt install inkscape`).
- **Poppler utilities** — native PDF text extraction and selected-page rendering for `curriculum_read.py` (`pdftotext` and `pdftoppm`; install `poppler-utils` on Debian/Ubuntu).

### Tests

Install the development extra to run the pytest suite:

```bash
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest
```

## Dependencies

These are separate, reusable tools that this project relies on:

| Tool | Location | Purpose |
|------|----------|---------|
| [signal-sieve](https://github.com/bbusenius/signal-sieve) | Installed from Git URL in `pyproject.toml` | Captures Signal messages into SQLite |
| [xlsx-append](https://github.com/bbusenius/xlsx-append) | Installed from Git URL in `pyproject.toml` | Appends rows to Excel spreadsheets |
| [Homeschool-Dashboard](https://github.com/bbusenius/Homeschool-Dashboard) | Installed from Git URL in `pyproject.toml` | Generates visual dashboard HTML from time-tracking spreadsheets |
| Vision/search-capable runtime tools | Configured in the active harness | Analyze screenshot and cover images; last-resort book lookups. Grok MCP is one supported implementation. |
| Google Maps MCP | Configured in the active harness | Geocoding, places search, place details, and directions for field trip planning |
| Image capability router | `scripts/charlotte_image.py` + ignored `image-generation.yaml` | Routes image generation through configured sources such as direct Google/Gemini, direct xAI/Grok, or NanoGPT |
| Gemini (`google-genai` SDK) | `scripts/gemini_image.py` | Direct Google/Gemini image backend used when configured as a route |
| WeasyPrint | Installed from `pyproject.toml` | HTML → PDF rendering; invoked from `mason-print-design` |
| Inkscape | system package | SVG → PDF/PNG rendering; invoked from `mason-print-design` |
| Poppler utilities | system package | Native curriculum PDF search, bounded extraction, and selected-page rendering through `scripts/curriculum_read.py` |
| hub.lexile.com (free tier) | — | Primary source for book metadata + Lexile level |
| openlibrary.org | — | Secondary source for title/author/ISBN when Lexile misses |
| `pedagogies/` | This repo | Pedagogy packs (see [Pedagogy packs](#pedagogy-packs)); the shipped `charlotte-mason` pack is read by the mason-* skills for framing, and the active pack (`pedagogy.path` in `runtime.yaml`) grounds general pedagogical help |

See [Runtime Tool Surface](docs/runtime-tool-surface.md) for the support checklist runtime adapters should satisfy.

## signal-sieve commands (used by the skill)

```bash
.venv/bin/signal-sieve list --group <alias>      # get unprocessed messages as JSON
.venv/bin/signal-sieve mark-processed 1 2 3      # mark IDs as done after processing
```

## xlsx-append usage

```bash
.venv/bin/xlsx-append <file.xlsx> <sheet> <col1> <col2> ... [--json]
```

Lesson spreadsheet columns: Date, Start Time, End Time, Description, Teacher

Reading list spreadsheet columns (same across both "read by" and "read to" sheets): Title, Author, Language, ISBN, SKU, Level, Audiobook, Part of coursework?

## Lesson log commands

```bash
# session directories: locate, create, add captured media
.venv/bin/python scripts/lesson_log_new.py find --student alice --date 2026-07-24 --subject Science
.venv/bin/python scripts/lesson_log_new.py create --student alice --date 2026-07-24 \
  --subject Science --slug forest-plot-survey
.venv/bin/python scripts/lesson_log_new.py add --session <dir> --role image --file photo.jpg

# reading logs back
.venv/bin/python scripts/lesson_log_read.py list --student alice --subject Science --latest 1
.venv/bin/python scripts/lesson_log_read.py search --student alice --query "guide words"
.venv/bin/python scripts/lesson_log_read.py show --session <dir> --section "how it went"

# spreadsheet projection
.venv/bin/python scripts/hsd_project.py gaps --student alice
.venv/bin/python scripts/hsd_project.py append --student alice --log <dir> \
  --description "Lesson 12: Mapping a Plot" --notes "Grasped decomposers immediately."
```

## Homeschool record read commands

```bash
.venv/bin/python scripts/hsd_read.py --student alice time --subject Math --latest 1
.venv/bin/python scripts/hsd_read.py --student alice books --latest 10
```

## Homeschool dashboard command

```bash
.venv/bin/python scripts/hsd_dashboard.py --student alice
```

## Curricula

Each curriculum assigned in `students.yaml` names one concrete Markdown
entrypoint file beneath the student's `curricula_dir`. Charlotte conventionally
uses `curriculum.md`, and `mason-curriculum-builder` produces that name, but the
resolver does not assume it: any configured filename is valid.

An imported curriculum index links to its real source files without requiring
conversion. Sources currently supported by the shared reader are Markdown,
plain text, and PDF. A composite index can describe the purpose of each file:

```markdown
---
id: example-language-arts-4
title: Example Language Arts Level 4
publisher: Example Publisher
subject: Language Arts & Literature
aliases: [language arts 4]
components:
  - path: Course Book.pdf
    role: primary-lessons
  - path: Reader.pdf
    role: reader
---

# Example Language Arts Level 4

- [Course Book](Course%20Book.pdf)
- [Reader](Reader.pdf)
```

Component paths are relative to the index. They must stay within the authorized
`curricula_dir`; directory names and publisher layouts are organizational
choices, not runtime signals.

### Reading native curriculum sources

The shared reader resolves the configured index, searches its linked sources,
and reads only a bounded section:

```bash
.venv/bin/python scripts/curriculum_read.py --student alice inspect \
  --curriculum example-language-arts-4
.venv/bin/python scripts/curriculum_read.py --student alice search \
  --curriculum example-language-arts-4 --lesson 5 --role primary-lessons
.venv/bin/python scripts/curriculum_read.py --student alice read \
  --source curricula/third-party/example/course.pdf --pages 19-20
```

PDF search text is extracted and normalized in memory for that invocation, then
discarded. The PDF remains the authoritative curriculum. When page layout or
imagery matters, `read --render-dir <temporary-directory>` renders only the
selected pages; callers inspect those images and remove the scratch directory.
There is no persistent extraction cache.

### Curriculum files

Third-party curricula may be stored under `curricula/third-party/`, shared across students. This is an example layout rather than a required hierarchy:

```
curricula/
└── third-party/
    ├── publisher-a/math-3/curriculum.md
    ├── publisher-a/language-arts-3/course-index.md
    └── publisher-b/spanish-3/curriculum.md
```

The child ↔ curriculum association lives in `students.yaml`, not in the directory layout.

Curricula authored inside this repo (via `mason-unit-builder` / `mason-curriculum-builder`) live elsewhere under `curricula/` — see each skill's documentation.

## Spreadsheets

Configured per student in `students.yaml`. The example registry stores Homeschool-Dashboard-compatible records under `~/Documents/Homeschool/<child>/`, but local paths can differ:

- **Time tracking** (`Time-<level>.xlsx`) — one sheet per subject/class.
- **Reading list** (`Reading List-<level>.xlsx`) — two sheets per workbook. By position: sheet `0` is books the child reads, sheet `1` is books read to the child. The skill resolves these by index so sheet names can change freely.

## Skill usage

From a skill-aware harness, while in the project directory:

```
/lesson-log                  # write lesson logs for every student with material waiting
/lesson-log <student>        # only one student

/hsd-time-log                # fill in missing Homeschool-Dashboard rows for every student
/hsd-time-log <student>      # only one student

/hsd-book-log                # process both children's book messages
/hsd-book-log <student>      # only one student's book messages

/weekly-review               # household digest of the last seven days (cron form)
/weekly-review <student>     # only one student
/weekly-review --from YYYY-MM-DD --to YYYY-MM-DD

/mason-field-trip-planner <theme + location in prose>           # ranked list + interactive pick
/mason-field-trip-planner <...> --auto                          # skip the ranked list; take rank 1
/mason-field-trip-planner <...> --save path/to/plan.md          # override default save location

/mason-materials-builder <material description in prose>        # generate a homeschool material
/mason-materials-builder <...> --out path/to/file               # override save location (default: CWD)
/mason-materials-builder <...> --image gemini|grok              # force model-family preference
/mason-materials-builder <...> --format pdf|html|svg|png|md     # override default format
/mason-materials-builder <...> --size 1K|2K|4K                  # override illustration resolution

/mindfeast-weekly-slides <student>                        # generate this week's MindFeast slides
/mindfeast-weekly-slides <student> --week-start 2026-05-18 # generate from a specific week
/mindfeast-weekly-slides <student> --no-sync              # create/validate slides without tablet sync

/ao-picture-study <student>                               # prepare, sync, and select the next AO study
/ao-composer-study <student>                              # create two slides; select the listening slide

/mindfeast-slide-sync <student>                           # sync existing slides for one student
/mindfeast-slide-sync --all                               # sync every configured tablet
/mindfeast-slide-sync <student> --dry-run                 # validate sync config without POSTing

/mindfeast-slide-trigger <student>                        # trigger a slide on one tablet
/mindfeast-slide-trigger --all                            # trigger every configured tablet
/mindfeast-slide-trigger <student> --dry-run              # validate trigger config without POSTing

/mindfeast-agent-alarm <student> --status                 # Agent Alarm status for one student
/mindfeast-agent-alarm --all --status                     # status for every configured alarm
/mindfeast-agent-alarm <student> --audio path --time 07:30 --enable
/mindfeast-agent-alarm <student> --days mon,tue,wed,thu,fri
/mindfeast-agent-alarm <student> --dry-run --status       # validate config without POSTing
```

Examples:

- `/mason-field-trip-planner We've just finished Math-3 Lessons 40–45 (rounding and estimation). Plan a trip in Hyde Park, Chicago, within 5 miles.`
- `/mason-materials-builder A copywork page for a mid-elementary student on a Robert Louis Stevenson couplet, with a small pen-and-ink vignette at the top.`
- `/mason-materials-builder A set of six picture-study cards for monarch butterfly life stages, tablet-first, watercolor register.`
- `/weekly-review`
- `/weekly-review last week`
- `/mindfeast-weekly-slides <student> for this week, but don't sync yet.`
- `/ao-picture-study Make <student>'s next AO picture study.`
- `/ao-composer-study Make <student>'s next AO composer study.`
- `/mindfeast-slide-sync <student>`
- `/mindfeast-slide-trigger <student>`
- `/mindfeast-agent-alarm <student> --status`

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/lexile/lookup.py` | Looks up a book on hub.lexile.com (Playwright); returns title, author, language, ISBN, Lexile |
| `scripts/openlibrary/lookup.py` | Looks up a book on Open Library; returns metadata with a high/medium/low confidence tier |
| `scripts/openlibrary/subject_search.py` | Discovers books on a topic via Open Library subject search; classifies results as `picture_book`, `chapter_book`, `middle_grade`, `young_adult`, or `adult` for enrichment bucketing in field trip plans |
| `scripts/get-sheet-name.py` | Resolves a sheet name by its positional index in an xlsx file |
| `scripts/lesson_log_new.py` | Locates or creates lesson-log session directories and copies captured media in with stable append-only names |
| `scripts/lesson_log_read.py` | Queries lesson logs as bounded JSON — session summaries, full-text search across logs/pages/messages/video transcripts, and named sections |
| `scripts/fetch_video_transcript.py` | Fetches a video URL's captions or auto-captions as JSON without downloading the video |
| `scripts/hsd_project.py` | Finds logged sessions with no Homeschool-Dashboard row and appends the missing ones; never updates an existing row |
| `scripts/hsd_read.py` | Reads configured Homeschool-Dashboard-compatible time and reading-list spreadsheets as compact JSON |
| `scripts/hsd_dashboard.py` | Generates visual Homeschool Dashboard HTML for a configured student |
| `scripts/charlotte_image.py` | Routes image generation through configured sources in `image-generation.yaml`; supports `--dry-run` prompt inspection; exits 2 when no script-callable provider is available |
| `scripts/gemini_image.py` | Direct Google/Gemini image backend used by `scripts/charlotte_image.py` when configured |
| `skills/mindfeast-slide-sync/scripts/sync.py` | Syncs existing MindFeast tablet slides through the per-student remote endpoint in `students.yaml` |
| `skills/mindfeast-slide-trigger/scripts/trigger.py` | Triggers a configured MindFeast tablet to show a slide through the per-student remote endpoint in `students.yaml` |
| `skills/mindfeast-agent-alarm/scripts/push.py` | Pushes MindFeast Agent Alarm settings through the per-student `agent_alarm` endpoint in `students.yaml` |
| `skills/mindfeast-slide-builder/scripts/make_slide.py` | Creates a MindFeast slide folder with `slide.md` and optional copied media |
| `skills/mindfeast-slide-builder/scripts/validate_slide.py` | Validates MindFeast slide folders before delivery |
| `skills/ao-picture-study/scripts/rotation.py` | Parses AO's artist rotation and maintains the last-created cursor |
| `skills/ao-picture-study/scripts/write_study.py` | Persists an exact AO study and artwork and updates its curriculum index idempotently |
| `skills/ao-picture-study/scripts/select_slide.py` | Selects an exact synced MindFeast slide as next without triggering it |
| `skills/ao-composer-study/scripts/rotation.py` | Parses AO's composer rotation and maintains per-student presentation cursors |
| `skills/ao-composer-study/scripts/download_audio.py` | Acquires a selected web recording as MP3 with yt-dlp and ffmpeg |
| `skills/ao-composer-study/scripts/write_study.py` | Idempotently archives a work, narration, images, sources, and recording metadata |
| `skills/ao-composer-study/scripts/select_slide.py` | Selects the exact primary listening slide without triggering it |
| `scripts/curriculum_resolve.py` | Resolves a configured curriculum by id, alias, path, or unique subject without guessing among overlaps |
| `scripts/curriculum_read.py` | Inspects curriculum indexes and searches or reads bounded Markdown, text, and native PDF sources; PDF extraction is temporary |

Purchased curriculum files remain in their native formats; conversion is not a
registration requirement.

## Project structure

```
charlotte/
├── README.md
├── AGENTS.md               # canonical agent instructions
├── CLAUDE.md               # Claude adapter; points to AGENTS.md
├── pyproject.toml           # Python dependencies
├── students.yaml.example    # portable example registry; real students.yaml is local-only
├── image-generation.yaml.example # portable example image route config; real image-generation.yaml is local-only
├── .venv/                   # project virtualenv, local-only
├── curricula/               # local-only content root
│   └── third-party/         # third-party curricula, one subdirectory per curriculum
├── lesson-logs/             # local-only content root: the record of what was taught
│   └── <student>/<grade>/<year>/<month>/<day>/<subject>-<slug>/
├── schedules/               # local-only forward-looking household schedules
├── skills/                  # canonical tracked skills
│   ├── lesson-log/          # lesson content logging skill (the system of record)
│   ├── weekly-review/       # household digest of the week's lesson logs
│   ├── hsd-time-log/        # Homeschool-Dashboard time-row projection skill
│   ├── hsd-book-log/        # Homeschool-Dashboard-compatible book logging skill
│   ├── hsd-records-read/    # Read-only workbook query skill
│   ├── hsd-dashboard-show/  # Visual dashboard generation skill
│   ├── mason-lesson-plan-builder/ # Charlotte Mason lesson authoring skill
│   ├── mason-unit-builder/  # Charlotte Mason unit authoring skill
│   ├── mason-curriculum-builder/  # Charlotte Mason curriculum authoring skill
│   ├── mason-field-trip-planner/  # Charlotte Mason field trip planning skill
│   ├── mason-materials-builder/   # Charlotte Mason material creation skill
│   ├── ao-picture-study/    # next AO artwork + narrated MindFeast picture study
│   ├── ao-composer-study/   # AO recording + primary listening and secondary podcast slides
│   ├── mindfeast-weekly-slides/ # weekly MindFeast slides from lesson logs (workbook fallback)
│   ├── mindfeast-slide-sync/ # sync existing MindFeast slides to tablets
│   ├── mindfeast-slide-trigger/ # trigger a MindFeast tablet slide remotely
│   ├── mindfeast-agent-alarm/ # per-student MindFeast Agent Alarm LAN client
│   ├── mindfeast-slide-builder/ # MindFeast slide generation skill
│   │   └── scripts/
│   │       ├── make_slide.py
│   │       └── validate_slide.py
│   ├── mason-aesthetics/    # peer skill: aesthetic direction (typography, palette, illustration register)
│   └── mason-print-design/  # peer skill: print-fidelity rules + rendering toolchain
├── .claude/skills/          # Claude adapter symlinks to skills/
├── .agents/skills/          # generic agent adapter symlinks to skills/
├── pedagogies/              # pedagogy packs; user packs dropped here are gitignored
│   ├── AGENTS.md            # pack schema + wiki maintenance instructions (all packs)
│   ├── CLAUDE.md            # Claude adapter; points to AGENTS.md
│   ├── templates/           # wiki page templates shared by all packs
│   └── charlotte-mason/     # shipped public-domain Charlotte Mason pack (raw/ + wiki/)
├── scripts/
│   ├── get-sheet-name.py
│   ├── lesson_log_new.py    # session directories + captured media
│   ├── lesson_log_read.py   # bounded queries over lesson logs
│   ├── fetch_video_transcript.py # video URL captions/auto-captions as JSON
│   ├── hsd_project.py       # lesson logs -> Homeschool-Dashboard rows
│   ├── curriculum_resolve.py # configured curriculum identity + entrypoint resolution
│   ├── curriculum_read.py   # bounded Markdown/text/native-PDF curriculum reader
│   ├── charlotte_image.py   # configured image capability router
│   ├── gemini_image.py      # direct Google/Gemini image backend
│   ├── lexile/lookup.py
│   ├── openlibrary/lookup.py
│   └── openlibrary/subject_search.py
├── scripts/local/           # ignored local one-off import/fixup scripts
├── field-trips/             # local-only saved field trip plans
├── .logs/                   # local-only sync/operation logs
└── .backups/                # local-only spreadsheet backups
```

## License

Charlotte's original code, skills, and documentation are licensed under the
[Apache License 2.0](LICENSE).

That license does not apply to third-party material identified in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), private family data,
purchased curricula, generated family content, or separately licensed
MindFeast products and trademarks. Charlotte's MindFeast integration tools are
open source; the MindFeast Android application, official content, services,
and visual brand assets are separately licensed.

See [Contributing](CONTRIBUTING.md), [Support](SUPPORT.md), [Security and privacy](SECURITY.md), and [Third-party notices](THIRD_PARTY_NOTICES.md).
