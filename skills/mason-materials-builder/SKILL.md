---
name: mason-materials-builder
description: Build printable or standalone homeschool materials — maps, timelines, flashcards, copywork sheets, nature-notebook pages, narration templates, picture-study and composer cards, vocabulary and memory-verse cards, math/phonics/handwriting practice, PDFs, SVGs, PNG illustrations, and similar resources — grounded in the project's pedagogy wiki. Invokes mason-aesthetics for visual direction and mason-print-design for rendering. Generates images through the configured Charlotte image router. Do not use for Android lock-screen slides, MindFeast slides, unlock questions, or app slide packages; use mindfeast-slide-builder for those.
argument-hint: <material description in prose, optionally referencing a student or lesson> [--out PATH] [--image quality|fast] [--format pdf|html|svg|png|md] [--size 1K|2K|4K]
---

# Materials Builder

Produce homeschool materials from a free-form prose prompt. Every material is grounded in the Charlotte Mason pedagogy wiki at `pedagogies/charlotte-mason/wiki/` for **how** it's made, regardless of *what* is being made. The skill never refuses a reasonable request — if a parent asks for a comprehension worksheet, it builds one, and offers a Mason-native alternative as a single closing note.

This skill owns the *what* — material type, content, pedagogical framing, curriculum linkage. It does not own the *how* of aesthetics or rendering — those live in two peer skills that must be invoked:

- `mason-aesthetics` — typography, color, illustration style, layout, decoration, language on the page, and the tests a material must pass.
- `mason-print-design` — rendering rules (HTML → PDF via WeasyPrint, SVG → PNG/PDF via Inkscape, vector text defaults, full-bleed CSS, dimensions, pre-conversion checklist).

Do not restate or reimplement those skills' guidance — invoke them.

For MindFeast challenge slides synced from `tablet-slides/`, use `mindfeast-slide-builder` instead. This includes bare requests such as "make a slide about toads" when the active project context is MindFeast/tablet slides. Those slides have an app-specific folder, YAML, media, and validation contract rather than a print-rendering contract.

## Usage

- `/mason-materials-builder A set of picture-study cards for four John Singer Sargent watercolors. Landscape orientation, PDF.`
- `/mason-materials-builder Copywork sheet from the Level-3-Language-Arts Lesson 40 passage — use the passage from that lesson. Half-ruled lines, cream background.`
- `/mason-materials-builder A map of Guatemala showing Antigua, Tikal, and Lake Atitlán — pen-and-ink style for a history lesson on Maya sites. SVG so I can overlay labels.`
- `/mason-materials-builder Ten math flash cards practicing two-digit by one-digit multiplication (Math-3 Lessons 42–43).`
- `/mason-materials-builder A blank narration page with a drawing frame and six lines for a pre-K reader after we read Blueberries for Sal.`
- `/mason-materials-builder An illustration of a monarch butterfly on milkweed, botanical plate style, no text.`

### Flags

- `--out PATH` — directory (or file path for single outputs) to write to. Default: current working directory. The future mason-lesson-plan-builder will set this explicitly; for now the user is in control.
- `--image quality|fast` — image route. Default: `quality`. See "Image generation" below for route behavior.
- `--format pdf|html|svg|png|md` — output format. If omitted, pick the sensible default for the material type (see below).
- `--size 1K|2K|4K` — when generating images through the image router. Default: `1K` unless the material is a wall card / large-format poster, in which case `2K`.

## Inputs (parsed from the prompt)

The prompt is free-form prose. Extract:

1. **Material type** (required) — map, timeline, flashcard set, copywork sheet, nature-notebook page, narration template, picture-study card, composer card, vocabulary card, memory-verse card, math practice, phonics practice, handwriting sheet, illustration, etc. If ambiguous, pick the most plausible type and say so in a single line at the start of the work — do not block.
2. **Theme / subject matter** (required) — what the material is *about*.
3. **Student** (optional) — a name, alias, or age/grade. Used for reading level, typography sizing, writing-line spacing, prompt register, and to resolve curriculum file locations. Matched against `students.yaml` (see below). If not supplied and not inferable, design for mid-elementary and note in the work that age-specific differentiation is available on request — do not block on it.
4. **Curriculum lesson reference** (optional) — if the prompt names a curriculum file or lesson, read that lesson from the student's curriculum directory and build from what the lesson actually covers.
5. **Output wishes** (optional) — format, orientation, single sheet vs. set, tablet vs. print, etc.
6. **Flags** — as listed above.

## Student configuration

Student metadata lives in `students.yaml` at the repo root. It is the single source of truth for every skill in this project that needs per-student info; this skill does not hard-code any student names. When a prompt references a student by name or alias, resolve them through the registry.

The registry provides, per student: display name, aliases, grade, curricula directory, a map from curriculum filenames to subject and lesson-header pattern, subject list, and the time-tracking spreadsheet path. mason-materials-builder uses: display name and grade (for age-appropriate sizing and address), curricula directory + curricula map (for lesson lookups), and aliases (for matching prompt references).

**Resolution procedure** when the prompt mentions a name:

1. Read `students.yaml`.
2. Lowercase the prompt's name reference and match it against each student's slug (top-level key) and every entry in their `aliases` list.
3. On a hit, use that student's `curricula_dir` and `curricula` map as the authoritative sources for lesson lookups; use `grade` for pedagogical defaults.
4. On no hit, proceed with whatever grade/age the prompt supplies directly; if it supplies none, design for mid-elementary and note that in the work.

If the prompt names a student who isn't in the registry but gives enough direct context to proceed (e.g. "for my 5-year-old"), proceed on that context and mention the missing registry entry once — never block.

## Pedagogical framing (applied to every material)

Before writing any material, invoke the `mason-aesthetics` skill to load the project's aesthetic point of view. When rendering, invoke `mason-print-design`.

Read (or re-read) whichever of these pedagogy concept pages are load-bearing for the specific material:

- `pedagogies/charlotte-mason/wiki/concepts/education-is-atmosphere-discipline-life.md` — applies to every material. The material is atmosphere.
- `pedagogies/charlotte-mason/wiki/concepts/children-are-born-persons.md` — applies to every material. The copy addresses a person.
- `pedagogies/charlotte-mason/wiki/concepts/living-books.md` — any textual content draws on living-book register.
- `pedagogies/charlotte-mason/wiki/concepts/knowledge-as-food.md` — the material is nourishment, not busywork.
- `pedagogies/charlotte-mason/wiki/concepts/science-of-relations.md` — where the material admits it, prompts open relations rather than close them.
- `pedagogies/charlotte-mason/wiki/concepts/narration.md` — for anything that follows a reading, narration is the default response-format; comprehension quizzes are a fallback, not a default.
- `pedagogies/charlotte-mason/wiki/concepts/single-reading.md` — associated reading is read attentively once, not drilled.
- `pedagogies/charlotte-mason/wiki/concepts/knowledge-of-god-man-universe.md` — nature study, picture study, music appreciation, handicraft observation as load-bearing Mason practices.

The wiki's vocabulary is load-bearing — don't paraphrase it loosely when you reference these concepts in explanatory copy or in offered alternatives.

## Material-type defaults

Each material type has a sensible default format and layout. These are starting points — override when the prompt says so. Rendering specifics for each format are in `mason-print-design`.

| Material type | Default format | Default orientation | Notes |
|---|---|---|---|
| Copywork sheet | PDF | Portrait letter | Passage set above ruled writing space; quote comes from a living book (check curriculum file if one is referenced). |
| Narration page | PDF | Portrait letter | Illustration frame + lined space. No comprehension questions. Prompt is an invitation. |
| Picture-study card | PDF or PNG | Landscape, card-sized or letter | Full-bleed image on front, artist / title / date as subtle caption. One artist, one piece — Mason's rule. |
| Composer card | PDF or PNG | Landscape, card-sized | Portrait or scene, dates, one piece to listen for, one line of context. |
| Nature-notebook page | PDF | Portrait or landscape | Dated framed sketch area, lined space for observations, optional species-list column. No pre-answered fields. |
| Flashcard set | PDF (multi-card sheet) | Landscape letter, cards per sheet | Plan cuts so cards align. Vocabulary cards have term on front, definition + sentence-from-literature on back. |
| Memory-verse card | PDF or PNG | Landscape, wall-card size | Lettering carve-out from `mason-print-design` often applies here — hand-lettering can legitimately be the art. |
| Map | SVG (primary) or PDF | As subject demands | Prefer SVG so the parent can overlay labels. If the material is a labeled atlas page, ship PDF. |
| Timeline | SVG or PDF | Landscape, often tabloid | Dated entries, room for the child to add to it. Do not pre-fill every event — timelines are built over time. |
| Vocabulary / memory card (stack) | PDF | Landscape letter, 6–10 per page | Back-of-card sentence taken from a living book when possible. |
| Math practice | PDF | Portrait letter | Problem size scales with grade. Read the referenced curriculum lesson — build from the lesson's method, not a generic template. |
| Phonics practice | PDF | Portrait letter | Words drawn from the curriculum's phonics sequence if one is referenced. Real words preferred over pseudo-words. |
| Handwriting sheet | PDF | Portrait letter | Appropriate manuscript or italic model font. Rule-spacing matches grade. |
| Illustration (standalone) | PNG | As subject demands | No text baked in. Save to `--out` for use in another material later. |

When the prompt implies a material not in the table, pick the closest analogue and note it in the work.

## Image generation

Image generation for this skill is route-based. This skill asks for the normal `quality` route unless the user explicitly asks for a fast/cheap image; `image-generation.yaml` decides which provider/model supplies that route.

- Keep using `mason-aesthetics` and `mason-print-design` before image generation. The router applies the Charlotte image prompt profile for the selected route; it does not replace material design or print-design constraints.
- Use the repo-local router below, invoked from the project root through `.venv/bin/python`.
- If the router exits `2`, no configured script-callable image provider is available. At that point, use a runtime-native image tool if the active harness exposes one. If no runtime image tool exists, report that image generation is unavailable.
- If the router exits `3`, stop. That is a policy/safety rejection; do not try another provider.

### Default route: quality

Use the router with `--route quality`:

```bash
.venv/bin/python scripts/charlotte_image.py \
  --prompt "…" --out path/to/file.png \
  --size 1K --aspect-ratio 4:3 \
  --kind illustration \
  --route quality --json
```

Run from the project root. The `--out` path can be relative to the project root or absolute.

The router reads `image-generation.yaml`. Use the JSON `path` in the result as the actual media file path; some providers return `.jpg` even when the requested path ended in `.png`. Use the JSON `route`, `source`, `model`, and `prompt_mode` fields when naming what generated the image.

Use `--dry-run --json` on the same command to inspect the resolved route and final provider prompt without calling an image provider or writing files.

Exit codes:

- `0` success. Use the JSON output to name the source/model in delivery.
- `1` configured providers were called but failed. Report the failure; do not hide it.
- `2` no script-callable provider is configured or available. Use a runtime-native image tool if available.
- `3` policy/safety rejection. Stop.

### Fast route

If the user explicitly asks for a fast/cheap/simple image, use `--route fast`:

```bash
.venv/bin/python scripts/charlotte_image.py \
  --prompt "…" --out path/to/file.png \
  --size 1K --aspect-ratio 4:3 \
  --kind illustration \
  --route fast --json
```

The route named `fast` receives the compact Mason image summary. Other routes receive the full `mason-aesthetics` skill as image prompt context unless `--prompt-mode` is explicitly overridden.

### Naming the image route in the delivery

The delivery message always names which route/source/model generated any images included in the material. A short line is enough: *"Illustration generated via route `quality`, Google, `<model>`"* or *"Illustration generated via route `fast`, Google, Imagen 4, 1K"*.

### Illustration prompt rules

- State the visual register explicitly ("pen-and-ink botanical plate," "watercolor in the register of Beatrix Potter," "Victorian nature-study illustration"). See `mason-aesthetics` §4.
- Say "no text, no labels, no captions" — we add text in HTML or SVG, not in the image.
  - Exception: the `mason-print-design` lettering carve-out. If the lettering *is* the art (a hand-lettered memory-verse card, decorative initial, period map label), allow baked-in text — and state *that* register explicitly too ("hand-lettered in an italic chancery hand," etc.).
- Specify composition when text will overlay the image later ("subject on the right, negative space on the left for a title," etc.).
- For anything that may be printed in grayscale, prefer registers with strong tonal structure (pen-and-ink, wood engraving) over color-dependent styles.

## Curriculum linkage

When the prompt references a curriculum file or specific lesson:

1. Resolve the student (see `students.yaml` above). This gives you a `curricula_dir` and a `curricula` map (filename → `{subject, lesson_header_pattern, ...}`).
2. If the prompt names a curriculum file directly (e.g. "Level-3-Language-Arts Lesson 40"), locate it in the student's `curricula_dir`. If it names only a subject ("math lesson 42"), use the `curricula` map to find the file whose subject matches.
3. Find the lesson in the file using the registry's `lesson_header_pattern`. Read the lesson content.
4. Build the material from what the lesson actually covers — not from a generic template and not from your prior about the topic.
5. When a copywork passage, vocabulary word, or practice problem is going into the material and could come directly from the lesson's source text, prefer the actual source-text wording.
6. Treat the lesson as **already studied** when the prompt refers to it as context; the material extends, applies, or consolidates it. Don't re-teach.

## Workflow

### Step 1 — Parse the prompt

Extract material type, subject, student reference, curriculum reference, format wishes, flags. If *material type* or *subject* is missing and can't be inferred, ask once and stop. Otherwise pick the most plausible interpretation, state it in one line, and proceed.

### Step 2 — Resolve the student (if named)

Read `students.yaml` and resolve any student reference. If not resolvable, proceed on direct prompt context; note the missing entry once.

### Step 3 — Read the pedagogy pages that apply

Always: `children-are-born-persons`, `education-is-atmosphere-discipline-life`.

Then, by material type:

- Anything involving reading: `living-books`, `single-reading`, `narration`.
- Anything observational (nature, picture, music): `science-of-relations`, `knowledge-of-god-man-universe`.
- Anything evaluative or practice-oriented: `knowledge-as-food` (to confirm the material is nourishment, not twaddle).

### Step 4 — Read the referenced curriculum lesson (if any)

If a lesson was referenced, read it in full from the student's `curricula_dir`, using the registry's `lesson_header_pattern` to locate it. Note the passage, terms, problems, or content that should flow into the material.

### Step 5 — Invoke `mason-aesthetics`

Load the aesthetic direction before designing. Its font-availability rule in particular needs to be respected before writing HTML/CSS or SVG that depends on a font.

### Step 6 — Design and render the material

Follow `mason-aesthetics` for typography / color / illustration / layout / decoration / language. Invoke `mason-print-design` for the rendering — it owns the format-specific rules, commands, and checklists. Do not reimplement what that skill already codifies.

Specific rules this skill adds on top of the two peer skills:

- **Living-book sources beat generic content.** If a passage, sentence, or problem can come from a living book or the referenced curriculum's own passages, use that source. A copywork sheet with a line from *Heidi* is a different object from a copywork sheet with a generic "The cat sat on the mat."
- **Narration is the default response-format** to a reading, not comprehension questions. If the parent asked for comprehension questions, build them — and offer a narration-page alternative as the one-line closing note.
- **Mason-native activity patterns are the default** for observation materials (nature notebook, picture-study card, composer card, handicraft card): single object / piece / artist, dated, silent sustained attention, then narration from memory.
- **Illustration register is explicit in every image prompt.** Never ship a vague prompt.
- **No twaddle language even in the most prosaic material.** A math worksheet can be direct and respectful without being jolly. A phonics sheet can have real words in its examples.

### Step 7 — Generate any illustrations

Use `scripts/charlotte_image.py` with the selected route. Place the image in the final composition via `<img>` (HTML) or `<image>` (SVG); text stays vector unless the lettering carve-out applies.

### Step 8 — Save

Save to `--out` if given, otherwise to the current working directory. Use a clear, descriptive filename:

- `copywork-<slug>-<YYYY-MM-DD>.pdf`
- `picture-study-sargent-<YYYY-MM-DD>.pdf`
- `map-guatemala-maya-sites.svg`
- `illustration-monarch-milkweed.png`

Use today's date (from the env) when a date is part of the filename. Never guess.

### Step 9 — Run the tests

Run `mason-aesthetics`'s tests before reporting completion: atmosphere, printability, font availability, person, nourishment, restraint. If anything fails, fix before delivering.

### Step 10 — Deliver

Output a short summary of what was produced and where it was saved. Include:

- Material type and what's in it (in one line)
- File path(s)
- **Image source/model named** when any image was generated (e.g. "illustration via NanoGPT using `<model>`" or "illustration via Google using Imagen 4, 1K")
- A single one-line note if anything about the request sits in real tension with the pedagogy — offered as an alternative, never as a correction, never more than once.

Example:

> Made `copywork-heidi-2026-04-19.pdf` — a half-page passage from *Heidi* Ch. 3 over ruled manuscript writing lines, classical serif body, cream ground. Illustration via NanoGPT using `<model>`. Saved in the current directory.
>
> *If useful, I can also produce a matching narration page for this passage — Mason's method is narration after a single reading.*

## Rules (hard)

- **Never refuse.** If the user asks for a material, build it. Tension with the pedagogy is handled in a single closing line, not by declining.
- **Pedagogy framework applies every time.** The framework is `how we make materials`, not `which materials we're willing to make`. Apply `mason-aesthetics` and read the relevant wiki pages on every run.
- **Invoke both peer skills.** `mason-aesthetics` for aesthetic direction; `mason-print-design` for rendering. Don't reimplement their guidance here.
- **Student data lives in `students.yaml`.** This skill never hard-codes student names, aliases, curriculum file paths, grade, or lesson-header patterns. All of that comes from the registry at runtime.
- **Living-book and curriculum sources beat generic content.** When a passage, word, or problem can come from a real source the student has been working in, it comes from there.
- **Image prompts state the register.** Never a vague prompt. Always "no text, no labels" unless the lettering carve-out applies.
- **Image source/model is named in delivery.** Always.
- **Image route is explicit.** Use the configured `quality` route by default. Use `fast` only when the user explicitly asks for fast/cheap/simple image generation.
- **No twaddle in language.** The material's copy addresses a person.
- **Date.** Use today's date from the env. Never guess.
- **No hallucinated sources.** If a passage, title, author, or historical fact goes on the page, it's real and correctly attributed. Don't invent a quote; open the book (or the curriculum file) and use a real passage, or ask the user to supply one.
