# Charlotte Homeschool Agent

Charlotte is a homeschool agent system — named for Charlotte Mason — for automating [Homeschool Dashboard](https://github.com/bbusenius/Homeschool-Dashboard) compatible lesson time logging, Homeschool Dashboard compatible reading-list logging, pedagogically grounded field trip planning, curriculum and lesson authoring, material creation, and MindFeast slide generation. It coordinates Signal message capture, AI-assisted identification, spreadsheet logging, on-demand trip planning, weekly review Android tablet lock slide creation, and on-demand material generation — all against a local pedagogy knowledge base. Pedagogical grounding is configurable (see [Pedagogy packs](#pedagogy-packs)); Charlotte ships with a public-domain Charlotte Mason pack as the default, plus a complete set of Charlotte Mason authoring skills.

## How it works

Charlotte allows users to log time and books through [Signal](https://signal.org/) chats. It uses [signal-sieve](https://github.com/bbusenius/signal-sieve) to strip metadata and protect privacy. AI agents only receive the minimal amount of data they need to do their job, not the kitchen sink. Charlotte also comes with on-demand planning/creation skills (field trips, materials, MindFeast slides), all reading a local pedagogy wiki for framing. Per-student metadata lives in `students.yaml` at the repo root (see [Student registry](#student-registry)).

Charlotte is **runtime-neutral by design**: the repo itself is the agent — skills, operating instructions, pedagogy packs, and family records — and the harness that runs it is swappable. Use it in one of two ways:

1. **As a standalone tool** inside a coding agent such as Claude Code, Codex, or OpenCode.
   - Just clone the repo and run skills in your coding agent of choice.
2. **As an always-on chat agent** on the harness of your choice — [Hermes](https://github.com/nousresearch/hermes-agent) ([runtime/hermes/](runtime/hermes/)) or [OpenClaw](https://openclaw.ai) ([runtime/openclaw/](runtime/openclaw/)) — with a chat gateway (Telegram recommended).
   - Tell the agent to run workflows in chat, or schedule skills with the harness's `cron`.
   - Both adapters run the identical skill set against the identical family data: switching harnesses is a matter of launching a different `runtime/<name>/run.sh`, and records logged under one runtime are fully visible to the other. The [runtime contract](docs/runtime-contract.md) defines what any new adapter must provide, so further harnesses can be added without touching the skills.

### Homeschool Dashboard lesson time logging (`/hsd-time-log`)

1. A parent sends Signal messages (text + screenshots) to a per-child lesson group documenting what was covered
2. **signal-sieve** captures those messages into SQLite (runs as a systemd service)
3. The `hsd-time-log` skill:
   - Reads text and screenshot images with a vision-capable runtime tool to identify lessons
   - Looks up lesson details in the curriculum markdown files
   - Logs entries to the child's time-tracking spreadsheet
   - Marks messages as processed

### Homeschool Dashboard book logging (`/hsd-book-log`)

1. Messages (book titles or cover photos) are sent to a per-child book group (configured via `reading.signal_group_alias` in `students.yaml`)
2. **signal-sieve** captures them the same way
3. The `hsd-book-log` skill:
   - Reads text / extracts title + author from cover images with a vision-capable runtime tool
   - Looks up metadata in order: **Lexile → Open Library → live search** (last-resort confirmation/search)
   - Writes a row to the child's reading-list spreadsheet (sheet chosen by position: "read by" vs "read to")
   - Marks messages as processed

### Homeschool Dashboard record queries (`/hsd-records-read`)

Reads existing time and reading-list workbooks without exposing whole spreadsheets to the model. Given a natural question such as "what was the last thing Eliana did in Math?" or "what books has Isamaya read lately?", the skill:

1. Resolves the student through `students.yaml`
2. Runs `scripts/hsd_read.py` against the configured workbook
3. Answers from compact JSON rows

The helper supports time-log filters by subject, date range, text query, and latest/limit. It supports reading-list filters by text query, configured list type (`read_by_self` / `read_to`), and latest/limit.

### Homeschool Dashboard viewing (`/hsd-dashboard-show`)

Generates the visual [Homeschool Dashboard](https://github.com/bbusenius/Homeschool-Dashboard) HTML for a configured student. Given a request such as "show me Eliana's homeschool dashboard", the skill:

1. Resolves the student through `students.yaml`
2. Runs `scripts/hsd_dashboard.py` against the student's `time_tracking_spreadsheet`
3. Writes `dashboards/<student>.html`
4. Opens, links, or reports the generated HTML path depending on the active runtime

This path is for visual dashboards. Conversational questions about logged records should use `/hsd-records-read`.

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

### MindFeast weekly slides (`/mindfeast-weekly-slides`)

Generates a small weekly review set for the MindFeast Android lock-screen app from a student's time-tracking spreadsheet. Given a student and optional week, the skill:

1. Reads the student's logged lesson rows via `skills/mindfeast-weekly-slides/scripts/collect_week.py`
2. Reads configured curriculum files or other known lesson materials when available to understand what was actually covered
3. Chooses a small set of useful slide opportunities, usually fewer than 8 and sometimes 0
4. Uses `tablet-slide-builder` to create MindFeast-compatible slide folders under the student's `tablet_slides_dir`
5. Validates each slide package
6. Optionally POSTs to the student's MindFeast remote sync endpoint and waits for the sync result before reporting

Slide types are content-driven: informational cards, multiple-choice questions, free-text questions, and essay/narration prompts are all valid. If a slide is based on a known public-domain artwork, the skill prefers the actual image from Wikimedia Commons rather than generated art.

### MindFeast slide sync (`/mindfeast-slide-sync`)

Syncs already-created tablet slide packages to the student's configured MindFeast remote endpoint. Given a student, it reads `mindfeast.remote_url` and `mindfeast.remote_token` from `students.yaml`, POSTs once to `<remote_url>/api/sync`, and reports the endpoint host/path and response summary without printing the token. If no student is named, it syncs every student with complete MindFeast sync config.

### MindFeast slide trigger (`/mindfeast-slide-trigger`)

Triggers a configured tablet to show a MindFeast slide now. Given a student, it reads `mindfeast.remote_url` and `mindfeast.remote_token` from `students.yaml`, POSTs once to `<remote_url>/api/trigger`, and reports the endpoint host/path, response summary, and returned `slideId` without printing the token. If no student is named, it triggers every student with complete MindFeast remote config.

## Student registry

Per-student metadata lives in `students.yaml` at the repo root. This is the single source of truth for display name, grade, aliases, curriculum files (with lesson-header regex), subjects, time-tracking spreadsheet path, tablet slide directory, MindFeast remote sync config, Signal group alias, and reading list config (spreadsheet path, sheet indices, Signal group alias). Skills read from it rather than hard-coding student data, so the repo stays portable — another family can ship their own `students.yaml`.

Adding a student:

1. Add an entry under `students:` in `students.yaml`
2. Put any third-party curriculum markdown under `curricula/third-party/<slug>/<filename>.md` and list that relative path in the student's `curricula` map
3. Skills that need the metadata will pick it up automatically

MindFeast sync is configured per student:

```yaml
mindfeast:
  remote_url: http://192.168.1.23:8787
  remote_token: ""
```

`remote_url` is the base URL for the tablet's MindFeast remote server. `remote_token` is the bearer token copied from MindFeast remote settings. Keep real tokens in local `students.yaml`, not in committed examples.

## Pedagogy packs

Pedagogical grounding is configurable. A **pedagogy pack** is a directory under `pedagogies/` containing `raw/` (immutable source documents) and `wiki/` (an LLM-maintained knowledge base built from them), following the schema in [pedagogies/AGENTS.md](pedagogies/AGENTS.md). The pack wiki implements Andrej Karpathy's [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) pattern — instead of retrieving from raw documents at query time (RAG), the LLM ingests sources once into a persistent, cross-referenced "living wiki" and keeps it current as sources and questions accumulate. Charlotte ships with `pedagogies/charlotte-mason/` — built from Charlotte Mason's public-domain works — as the default.

To use your own pedagogy or curriculum philosophy:

1. Create `pedagogies/<your-pack>/raw/` and drop your source materials there. Every pack except `charlotte-mason` is gitignored, so purchased or copyrighted texts stay on your machine and cannot be committed by accident.
2. Point `pedagogy.path` at the pack in local `runtime.yaml`.
3. Ask Charlotte to ingest the sources — the wiki is built and maintained for you.

General pedagogical questions and pedagogy-aware skills read the active pack's wiki. The visual register for generated images and materials is configured separately by `pedagogy.aesthetics` (default `skills/mason-aesthetics`) — swap in your own aesthetics file to change how every generated illustration looks without changing anything else.

The `mason-*` skills (`mason-lesson-plan-builder`, `mason-unit-builder`, `mason-curriculum-builder`, `mason-field-trip-planner`, `mason-materials-builder`, `mason-aesthetics`, `mason-print-design`) are the exception: they are Charlotte Mason tools by design, with Mason's method built into their workflows, and always read the `charlotte-mason` pack. They ship as an optional authoring toolkit for families who want lessons, units, curricula, trips, and materials in Mason's method — most families working entirely from purchased curricula only need the logging, dashboard, and tablet skills, which are pedagogy-neutral. Authoring toolkits for other pedagogies are welcome as contributions.

## Local content roots

This repository tracks the homeschool agent system, reusable skills, scripts, examples, and pedagogy scaffolding. It does not track family content, paid curriculum text, generated lesson content, generated slide packages, standalone generated images, trip plans, spreadsheets, or backups.

The following paths are writable local content roots and are intentionally gitignored:

- `curricula/` — paid/imported curriculum markdown plus generated curricula, units, lessons, and lesson assets
- `tablet-slides/` — generated Android lock-screen slide packages
- `generated-images/` — standalone generated images that are not tablet slide packages or printable materials
- `field-trips/` — generated field trip plans
- `dashboards/` — generated Homeschool Dashboard HTML
- `.backups/` — local spreadsheet backups created during logging workflows
- `.logs/` — local sync and long-running operation logs

Docker/OpenClaw/Hermes runtimes should treat these paths as local data volumes, not source code.

## Setup

Python scripts live in a project-local venv.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

This installs the Python dependencies from `pyproject.toml`, including `signal-sieve`, `xlsx-append`, `faster-whisper`, and `weasyprint` into `.venv/bin/`. The Lexile lookup uses Playwright with a system Chrome/Chromium executable, and audiobook transcription uses `ffmpeg`/`ffprobe`.

Install non-Python rendering/browser tools with your system package manager:

```bash
sudo apt install chromium ffmpeg inkscape
```

### Signal capture setup

The Charlotte install provides the `signal-sieve` CLI in `.venv/bin/`, which is enough for skills to read captured messages and mark them processed when `signal-sieve` config and data already exist.

Signal-driven logging also needs a running Signal capture service. In the currently supported setup, that service is host-owned: `signal-cli` and `signal-sieve listen` run on the host, while Hermes-in-Docker mounts the host `signal-sieve` config, database, and attachments. This is only required for the `hsd-time-log` and `hsd-book-log` workflows; Telegram chat, curriculum/material generation, tablet slides, and MindFeast sync do not require Signal capture.

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

tools:
  chrome_path: /usr/bin/google-chrome-stable
```

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

The current `hsd-time-log` and `hsd-book-log` skills write to spreadsheet records compatible with [Homeschool-Dashboard](https://github.com/bbusenius/Homeschool-Dashboard). Workbook paths live in `students.yaml`, so local Codex/Claude usage can keep host-native `~/...` paths. Docker runtimes must mount any host directories containing those workbooks, and host-owned Signal capture also requires mounting `signal-sieve` config/data paths; the Hermes adapter does both with `CHARLOTTE_HOME_MOUNTS`.

### Material creation prerequisites

`mason-materials-builder` additionally relies on:

- **Image routes** in ignored `image-generation.yaml` when a material needs generated images. `scripts/charlotte_image.py` uses the configured route; direct Google via `scripts/gemini_image.py` is one available backend, not a required default.
- **WeasyPrint** — HTML → PDF rendering, invoked from `mason-print-design`. Installed by `.venv/bin/python -m pip install -e .`; system libraries such as `libpango` and `libcairo` may still be required depending on the platform.
- **Inkscape** — SVG → PDF/PNG rendering. Install from your package manager (`apt install inkscape`).

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

## Homeschool record read commands

```bash
.venv/bin/python scripts/hsd_read.py --student eliana time --subject Math --latest 1
.venv/bin/python scripts/hsd_read.py --student eliana books --latest 10
```

## Homeschool dashboard command

```bash
.venv/bin/python scripts/hsd_dashboard.py --student eliana
```

## Curricula

Curriculum PDFs are converted to markdown with `pdftotext` or [OpenDataLoader PDF](https://github.com/opendataloader-project/opendataloader-pdf), then post-processed as needed to normalize lesson headers. PDF-to-markdown cleanup is curriculum-specific; one-off local fixup scripts belong under ignored `scripts/local/`.

### Converting a new curriculum

```bash
pdftotext "Course Book.pdf" "output.md"
scripts/local/<your-fixup-script> "output.md"
```
or

```bash
opendataloader-pdf curricula.pdf -f markdown
```

After processing, lesson headers appear as `## Lesson <number>` which the AI can search by lesson number.

### Curriculum files

Third-party curricula are stored under `curricula/third-party/<slug>/`, one subdirectory per curriculum, shared across students:

```
curricula/
└── third-party/
    ├── math-3/                   # e.g. Math-3.md
    ├── level-3-language-arts/    # e.g. Level-3-Language-Arts.md
    └── level-3-spanish-unit-3/   # e.g. Level-3-Spanish-Unit-3.md
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
/hsd-time-log                # process all children's lesson messages
/hsd-time-log <student>      # only one student's lesson messages

/hsd-book-log                # process both children's book messages
/hsd-book-log <student>      # only one student's book messages

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

/mindfeast-slide-sync <student>                           # sync existing slides for one student
/mindfeast-slide-sync --all                               # sync every configured tablet
/mindfeast-slide-sync <student> --dry-run                 # validate sync config without POSTing

/mindfeast-slide-trigger <student>                        # trigger a slide on one tablet
/mindfeast-slide-trigger --all                            # trigger every configured tablet
/mindfeast-slide-trigger <student> --dry-run              # validate trigger config without POSTing
```

Examples:

- `/mason-field-trip-planner We've just finished Math-3 Lessons 40–45 (rounding and estimation). Plan a trip in Hyde Park, Chicago, within 5 miles.`
- `/mason-materials-builder A copywork page for a mid-elementary student on a Robert Louis Stevenson couplet, with a small pen-and-ink vignette at the top.`
- `/mason-materials-builder A set of six picture-study cards for monarch butterfly life stages, tablet-first, watercolor register.`
- `/mindfeast-weekly-slides <student> for this week, but don't sync yet.`
- `/mindfeast-slide-sync <student>`
- `/mindfeast-slide-trigger <student>`

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/lexile/lookup.py` | Looks up a book on hub.lexile.com (Playwright); returns title, author, language, ISBN, Lexile |
| `scripts/openlibrary/lookup.py` | Looks up a book on Open Library; returns metadata with a high/medium/low confidence tier |
| `scripts/openlibrary/subject_search.py` | Discovers books on a topic via Open Library subject search; classifies results as `picture_book`, `chapter_book`, `middle_grade`, `young_adult`, or `adult` for enrichment bucketing in field trip plans |
| `scripts/get-sheet-name.py` | Resolves a sheet name by its positional index in an xlsx file |
| `scripts/hsd_read.py` | Reads configured Homeschool-Dashboard-compatible time and reading-list spreadsheets as compact JSON |
| `scripts/hsd_dashboard.py` | Generates visual Homeschool Dashboard HTML for a configured student |
| `scripts/charlotte_image.py` | Routes image generation through configured sources in `image-generation.yaml`; supports `--dry-run` prompt inspection; exits 2 when no script-callable provider is available |
| `scripts/gemini_image.py` | Direct Google/Gemini image backend used by `scripts/charlotte_image.py` when configured |
| `skills/mindfeast-slide-sync/scripts/sync.py` | Syncs existing MindFeast tablet slides through the per-student remote endpoint in `students.yaml` |
| `skills/mindfeast-slide-trigger/scripts/trigger.py` | Triggers a configured MindFeast tablet to show a slide through the per-student remote endpoint in `students.yaml` |
| `skills/tablet-slide-builder/scripts/make_slide.py` | Creates a Homeschool Screen Lock slide folder with `slide.md` and optional copied media |
| `skills/tablet-slide-builder/scripts/validate_slide.py` | Validates Homeschool Screen Lock slide folders before delivery |

Local one-off conversion scripts for paid curriculum imports live in ignored `scripts/local/` and are not part of the reusable project surface.

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
├── skills/                  # canonical tracked skills
│   ├── hsd-time-log/        # Homeschool-Dashboard-compatible lesson time logging skill
│   ├── hsd-book-log/        # Homeschool-Dashboard-compatible book logging skill
│   ├── hsd-records-read/    # Read-only workbook query skill
│   ├── hsd-dashboard-show/  # Visual dashboard generation skill
│   ├── mason-lesson-plan-builder/ # Charlotte Mason lesson authoring skill
│   ├── mason-unit-builder/  # Charlotte Mason unit authoring skill
│   ├── mason-curriculum-builder/  # Charlotte Mason curriculum authoring skill
│   ├── mason-field-trip-planner/  # Charlotte Mason field trip planning skill
│   ├── mason-materials-builder/   # Charlotte Mason material creation skill
│   ├── mindfeast-weekly-slides/ # weekly MindFeast slide generation from time logs
│   ├── mindfeast-slide-sync/ # sync existing MindFeast slides to tablets
│   ├── mindfeast-slide-trigger/ # trigger a MindFeast tablet slide remotely
│   ├── tablet-slide-builder/ # Android lock-screen slide generation skill
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
│   ├── charlotte_image.py   # configured image capability router
│   ├── gemini_image.py      # direct Google/Gemini image backend
│   ├── lexile/lookup.py
│   ├── openlibrary/lookup.py
│   └── openlibrary/subject_search.py
├── scripts/local/           # ignored local one-off curriculum conversion scripts
├── field-trips/             # local-only saved field trip plans
├── .logs/                   # local-only sync/operation logs
└── .backups/                # local-only spreadsheet backups
```
