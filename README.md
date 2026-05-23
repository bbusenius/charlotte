# Charlotte Mason Homeschool Agent

Charlotte is a Charlotte Mason homeschool agent system for automating lesson time logging, reading-list logging, pedagogically grounded field trip planning, curriculum and lesson authoring, and material creation. It coordinates Signal message capture, AI-assisted identification, spreadsheet logging, on-demand trip planning, and on-demand material generation — all against a local pedagogy wiki.

## How it works

Two Signal-driven logging pipelines (lessons, books) plus two on-demand planning/creation skills (field trips, materials), all reading the local pedagogy wiki for framing. Per-student metadata lives in `students.yaml` at the repo root (see [Student registry](#student-registry)).

### Lesson time logging (`/time-log`)

1. A parent sends Signal messages (text + screenshots) to a per-child lesson group documenting what was covered
2. **signal-sieve** captures those messages into SQLite (runs as a systemd service)
3. The `time-log` skill:
   - Reads text and screenshot images (via Grok Vision) to identify lessons
   - Looks up lesson details in the curriculum markdown files
   - Logs entries to the child's time-tracking spreadsheet
   - Marks messages as processed

### Book logging (`/book-log`)

1. Messages (book titles or cover photos) are sent to a per-child book group (configured via `reading.signal_group_alias` in `students.yaml`)
2. **signal-sieve** captures them the same way
3. The `book-log` skill:
   - Reads text / extracts title + author from cover images via Grok Vision
   - Looks up metadata in order: **Lexile → Open Library → Grok** (last-resort confirmation/search)
   - Writes a row to the child's reading-list spreadsheet (sheet chosen by position: "read by" vs "read to")
   - Marks messages as processed

### Field trip planning (`/field-trip-planner`)

Distinct from the logging pipelines — a planning skill, not Signal-driven. Given a theme (often lessons already studied) and a location in the prompt, the `field-trip-planner` skill:

1. Reads the theme and, if curriculum files are referenced, the specific lessons from wherever `students.yaml` points (third-party curricula live under `curricula/third-party/`)
2. Queries the Google Maps MCP for candidate venues near the location, supplemented by WebSearch for natural / outdoor places that Google Maps undercounts (trout streams, prairie remnants, trailheads, birding hotspots, etc.)
3. Ranks 3–5 options with Google Maps + website/social links
4. On selection (or with `--auto`), produces a full markdown field trip plan

Plans are grounded in the local pedagogy wiki at `pedagogy/wiki/` (Charlotte Mason) — every trip is framed around [[concepts/science-of-relations]], uses [[concepts/narration]] as post-trip assessment, and names Mason's canonical on-site activities (nature study, picture study, music appreciation, handicraft observation) where the venue admits them.

### Material creation (`/materials-builder`)

Also a planning/creation skill rather than a Signal-driven pipeline. Given a prose description (optionally referencing a student or specific lessons), the `materials-builder` skill:

1. Resolves the student (if any) via `students.yaml` and, if curriculum files are referenced, reads the relevant lessons from the paths `students.yaml` resolves them to
2. Invokes `mason-aesthetics` (peer skill) for aesthetic direction — typography tradition, palette direction, illustration register, font-availability check
3. Invokes `mason-print-design` (peer skill) for the rendering toolchain (WeasyPrint for HTML→PDF, Inkscape for SVG→PDF/PNG) and print-fidelity rules, including a lettering carve-out so hand-lettered or decorative text can be baked into the image when lettering *is* the art
4. Generates illustrations through `scripts/gemini_image.py` (Gemini Imagen 4 at 1K/2K, Gemini 3 Pro at 4K). If `GEMINI_API_KEY` is unset, falls back to the Grok MCP (`mcp__grok-mcp__generate_image`) and names the provenance in the delivery
5. Writes the finished material to the current working directory (or `--out PATH`), naming the image provider and model in the final message

Material types include printable worksheets, copywork pages, flashcards, narration templates, picture-study cards, period maps, posters, and tablet-first illustrations. Grounded in the same Charlotte Mason wiki at `pedagogy/wiki/`, `mason-aesthetics` roots its guidance in [[concepts/children-are-born-persons]], [[concepts/education-is-atmosphere-discipline-life]], [[concepts/knowledge-as-food]], [[concepts/living-books]], [[concepts/science-of-relations]], and [[concepts/narration]].

`mason-aesthetics` and `mason-print-design` are internal peer skills — invoked *by* `materials-builder` (and, in time, future creation skills), not directly by the user.

## Student registry

Per-student metadata lives in `students.yaml` at the repo root. This is the single source of truth for display name, grade, aliases, curriculum files (with lesson-header regex), subjects, time-tracking spreadsheet path, Signal group alias, and reading list config (spreadsheet path, sheet indices, Signal group alias). Skills read from it rather than hard-coding student data, so the repo stays portable — another family can ship their own `students.yaml`.

Adding a student:

1. Add an entry under `students:` in `students.yaml`
2. Put any third-party curriculum markdown under `curricula/third-party/<slug>/<filename>.md` and list that relative path in the student's `curricula` map
3. Skills that need the metadata will pick it up automatically

## Local content roots

This repository tracks the homeschool agent system, reusable skills, scripts, examples, and pedagogy scaffolding. It does not track family content, paid curriculum text, generated lesson content, generated slide packages, trip plans, spreadsheets, or backups.

The following paths are writable local content roots and are intentionally gitignored:

- `curricula/` — paid/imported curriculum markdown plus generated curricula, units, lessons, and lesson assets
- `tablet-slides/` — generated Android lock-screen slide packages
- `field-trips/` — generated field trip plans
- `.backups/` — local spreadsheet backups created during logging workflows

Docker/OpenClaw/Hermes runtimes should treat these paths as local data volumes, not source code.

## Setup

Python scripts live in a project-local venv.

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

This installs the Python dependencies from `pyproject.toml`, including `signal-sieve`, `xlsx-append`, and `weasyprint` into `.venv/bin/`. Playwright uses the system `google-chrome-stable` by default, so no separate browser download is needed on systems where that executable exists.

Install non-Python rendering/browser tools with your system package manager:

```bash
sudo apt install inkscape
```

### Runtime configuration

Non-secret machine/tool settings live in local `runtime.yaml`, which is ignored. To override defaults, copy the example and edit it:

```bash
cp runtime.yaml.example runtime.yaml
```

Currently supported:

```yaml
tools:
  chrome_path: /usr/bin/google-chrome-stable
```

`scripts/lexile/lookup.py` uses `tools.chrome_path` for its Playwright browser executable. Leave `runtime.yaml` absent if the default path works.

### Material creation prerequisites

`materials-builder` additionally relies on:

- **`GEMINI_API_KEY`** in the environment (e.g. exported from `~/.bashrc`) for `scripts/gemini_image.py`. If unset, the skill falls back to the Grok MCP and notes the provenance.
- **WeasyPrint** — HTML → PDF rendering, invoked from `mason-print-design`. Installed by `.venv/bin/pip install -e .`; system libraries such as `libpango` and `libcairo` may still be required depending on the platform.
- **Inkscape** — SVG → PDF/PNG rendering. Install from your package manager (`apt install inkscape`).

## Dependencies

These are separate, reusable tools that this project relies on:

| Tool | Location | Purpose |
|------|----------|---------|
| [signal-sieve](https://github.com/bbusenius/signal-sieve) | Installed from Git URL in `pyproject.toml` | Captures Signal messages into SQLite |
| [xlsx-append](https://github.com/bbusenius/xlsx-append) | Installed from Git URL in `pyproject.toml` | Appends rows to Excel spreadsheets |
| Grok MCP (Vision + live_search + image generation) | Configured in the active harness | Analyzes screenshot images; last-resort book lookups; fallback image generation for `materials-builder` |
| Google Maps MCP | Configured in the active harness | Geocoding, places search, place details, and directions for field trip planning |
| Gemini (`google-genai` SDK) | `scripts/gemini_image.py` | Primary image generation for `materials-builder` (Imagen 4 at 1K/2K, Gemini 3 Pro at 4K). Requires `GEMINI_API_KEY`. |
| WeasyPrint | Installed from `pyproject.toml` | HTML → PDF rendering; invoked from `mason-print-design` |
| Inkscape | system package | SVG → PDF/PNG rendering; invoked from `mason-print-design` |
| hub.lexile.com (free tier) | — | Primary source for book metadata + Lexile level |
| openlibrary.org | — | Secondary source for title/author/ISBN when Lexile misses |
| `pedagogy/wiki/` | This repo | Local pedagogy knowledge base (Charlotte Mason); read by the field trip planner and material-creation skills for framing |

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

Curricula authored inside this repo (via `unit-builder` / `curriculum-builder`, when available) live elsewhere under `curricula/` — see each skill's documentation.

## Spreadsheets

Stored in `~/Documents/Homeschool/<child>/`:

- **Time tracking** (`Time-<level>.xlsx`) — one sheet per subject/class.
- **Reading list** (`Reading List-<level>.xlsx`) — two sheets per workbook. By position: sheet `0` is books the child reads, sheet `1` is books read to the child. The skill resolves these by index so sheet names can change freely.

## Skill usage

From a skill-aware harness, while in the project directory:

```
/time-log                    # process all children's lesson messages
/time-log alice              # only Alice's lesson messages
/time-log charlie            # only Charlie's lesson messages

/book-log                    # process both children's book messages
/book-log alice              # only Alice's book messages
/book-log charlie            # only Charlie's book messages

/field-trip-planner <theme + location in prose>           # ranked list + interactive pick
/field-trip-planner <...> --auto                          # skip the ranked list; take rank 1
/field-trip-planner <...> --save path/to/plan.md          # override default save location

/materials-builder <material description in prose>        # generate a homeschool material
/materials-builder <...> --out path/to/file               # override save location (default: CWD)
/materials-builder <...> --image gemini|grok              # force image provider
/materials-builder <...> --format pdf|html|svg|png|md     # override default format
/materials-builder <...> --size 1K|2K|4K                  # override illustration resolution
```

Examples:

- `/field-trip-planner We've just finished Math-3 Lessons 40–45 (rounding and estimation). Plan a trip in Hyde Park, Chicago, within 5 miles.`
- `/materials-builder A copywork page for Alice on a Robert Louis Stevenson couplet, with a small pen-and-ink vignette at the top.`
- `/materials-builder A set of six picture-study cards for monarch butterfly life stages, tablet-first, watercolor register.`

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/lexile/lookup.py` | Looks up a book on hub.lexile.com (Playwright); returns title, author, language, ISBN, Lexile |
| `scripts/openlibrary/lookup.py` | Looks up a book on Open Library; returns metadata with a high/medium/low confidence tier |
| `scripts/openlibrary/subject_search.py` | Discovers books on a topic via Open Library subject search; classifies results as `picture_book`, `chapter_book`, `middle_grade`, `young_adult`, or `adult` for enrichment bucketing in field trip plans |
| `scripts/get-sheet-name.py` | Resolves a sheet name by its positional index in an xlsx file |
| `scripts/gemini_image.py` | Generates images via the `google-genai` SDK; routes 1K/2K to Imagen 4 and 4K to Gemini 3 Pro; exit 2 on missing key/SDK, exit 1 on API failure |
| `scripts/tablet-slides/make_slide.py` | Creates a Homeschool Screen Lock slide folder with `slide.md` and optional copied media |
| `scripts/tablet-slides/validate_slide.py` | Validates Homeschool Screen Lock slide folders before delivery |

Local one-off conversion scripts for paid curriculum imports live in ignored `scripts/local/` and are not part of the reusable project surface.

## Project structure

```
charlotte/
├── README.md
├── AGENTS.md               # canonical agent instructions
├── CLAUDE.md               # Claude adapter; points to AGENTS.md
├── pyproject.toml           # Python dependencies
├── students.yaml.example    # portable example registry; real students.yaml is local-only
├── .venv/                   # project virtualenv, local-only
├── curricula/               # local-only content root
│   └── third-party/         # third-party curricula, one subdirectory per curriculum
├── skills/                  # canonical tracked skills
│   ├── time-log/            # lesson time-logging skill
│   ├── book-log/            # book-logging skill
│   ├── field-trip-planner/  # pedagogy-grounded field trip planning skill
│   ├── materials-builder/   # Charlotte Mason material creation skill
│   ├── mason-aesthetics/    # peer skill: aesthetic direction (typography, palette, illustration register)
│   └── mason-print-design/  # peer skill: print-fidelity rules + rendering toolchain
├── .claude/skills/          # Claude adapter symlinks to skills/
├── .agents/skills/          # generic agent adapter symlinks to skills/
├── pedagogy/                # pedagogy wiki (Charlotte Mason) read by field-trip-planner and material-creation skills
│   ├── AGENTS.md            # canonical pedagogy wiki maintenance instructions
│   └── CLAUDE.md            # Claude adapter; points to AGENTS.md
├── scripts/
│   ├── get-sheet-name.py
│   ├── gemini_image.py      # image generation via google-genai (Imagen 4 / Gemini 3 Pro)
│   ├── lexile/lookup.py
│   ├── openlibrary/lookup.py
│   ├── openlibrary/subject_search.py
│   └── tablet-slides/
│       ├── make_slide.py
│       └── validate_slide.py
├── scripts/local/           # ignored local one-off curriculum conversion scripts
├── field-trips/             # local-only saved field trip plans
└── .backups/                # local-only spreadsheet backups
```
