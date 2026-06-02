---
name: unit-builder
description: Build a Mason-shaped unit — a thematic slice of N lessons on one subject — grounded in the project's pedagogy wiki. Produces a unit manifest with a hero illustration, a chosen spine book, and N lesson files (via lesson-plan-builder), with an optional set of field trips (via field-trip-planner). Curriculum-builder chains units into a paced curriculum; unit-builder owns the arc within one unit.
argument-hint: <unit description in prose, optionally referencing a student, class, or spine book> [--auto] [--lessons N] [--field-trip] [--no-lessons] [--save PATH]
---

# Unit Builder

Produce one unit — a thematic slice of several lessons on one subject — from a free-form prose prompt. Every unit is grounded in the Charlotte Mason pedagogy wiki at `pedagogy/wiki/` for **how** it is made, regardless of subject. A unit built by this skill is a coherent arc of lessons (typically 3–12, depending on grade), not a single session and not a full curriculum.

This skill owns the *arc* — which relations the whole unit opens, the spine book that anchors it, the order of lessons, and how the unit connects up to a parent curriculum if one exists. It does not own individual lesson design (lesson-plan-builder does), does not own rendering (materials-builder does), does not plan field trips (field-trip-planner does), and does not own calendar/pace — that's curriculum-builder's job.

## Usage

- `/unit-builder A 6-lesson unit on organism relationships for Alice in 4th-grade science`
- `/unit-builder A 4-lesson unit on Maya civilization for a 3rd grader, anchored by Peter Lourie's "Jungle Journey"`
- `/unit-builder Water cycle — 3 short observation-shaped lessons for a preschooler --auto`
- `/unit-builder Picture study unit on John Singer Sargent — four watercolors, one per lesson, for Alice --field-trip`
- `/unit-builder Extend the organism-relationships unit with two lessons on decomposers for Alice`

### Flags

- `--auto` — skip any clarifying questions; take defaults and write the unit. Intended for curriculum-builder integration.
- `--lessons N` — override the grade default for the number of lessons in the unit. Without the flag: preschool/K → 3; 1st–4th → 6; 5th+ → 8. A prompt that names a number ("4-lesson unit") takes precedence over the default.
- `--field-trip` — generate at least one field trip for this unit via field-trip-planner. Requires a location resolvable from the prompt. Default: no trip. Prose like "with a field trip in X" is equivalent.
- `--no-lessons` — write `unit.md` only; defer lesson generation for a second pass. Useful when the teacher wants to review the arc before lessons are written.
- `--save PATH` — override the default output directory.

## Inputs (parsed from the prompt)

The prompt is free-form prose. Extract:

1. **Class / subject** (required, usually inferable). Same rules as lesson-plan-builder — inferred from prompt + grade. "3rd-grade science" → `3rd-grade-science`. "Spanish for a 3rd grader" → `3rd-grade-spanish`. Lowercase kebab-case.
2. **Unit theme** (required) — what this unit is about (e.g. `organism-relationships`, `maya-civilization`, `water-cycle`). Kebab-case.
3. **Student** (optional) — matched against `students.yaml` exactly the way lesson-plan-builder matches. Used for length defaults and register, not for subject authoring.
4. **Lesson count** (optional) — from `--lessons`, from prose ("a 6-lesson unit"), or from the grade default above.
5. **Spine book** (optional, from prose) — if the user names a book, use it. Otherwise unit-builder picks one (see "Spine book" below).
6. **Field trip wish** (optional) — from `--field-trip` or prose.
7. **Curriculum context** (optional, passed by curriculum-builder) — if the invocation includes a parent curriculum slug, a pace budget (minutes per lesson, lessons in this unit), an ordinal within the curriculum, or an overarching spine book, respect those.

If the unit theme is genuinely ambiguous and not under `--auto`, ask once and stop. Under `--auto`, pick the most plausible interpretation, state it in one line at the top of the delivery, and proceed.

## Student configuration

Student metadata lives in `students.yaml` at the repo root. Unit-builder uses: `display_name`, `grade`, and `aliases`. It does **not** use `subjects`, `curricula_dir`, or `curricula` — those point at third-party curricula this skill is not authoring against.

Resolution procedure is the same as lesson-plan-builder: read `students.yaml`, lowercase-match prompt name references against each student's slug and `aliases` list, record `display_name` and `grade` on a hit. On no hit with a grade in the prompt, proceed on grade alone. On no hit and no grade, design for mid-elementary. Never hard-code student names, aliases, or grades.

## Pedagogical framing

Re-read any of these wiki pages whose language you are about to use — the vocabulary is load-bearing:

- `concepts/science-of-relations.md` — the unit's backbone. A unit opens a coherent family of relations across its lessons. What varies by subject is *which* relations, not whether they're named.
- `concepts/act-of-knowing.md` and `concepts/narration.md` — every lesson closes in narration; the unit inherits this at every session.
- `concepts/living-books.md` — the spine book is a living book. First-hand, narrative, author's voice. Not a textbook summary. This is especially load-bearing at the unit level, where Mason's "form book" / single-spine pattern applies.
- `concepts/single-reading.md` — if the unit reads, each reading is attended to once.
- `concepts/education-is-atmosphere-discipline-life.md` — the unit *is* the atmosphere for several sessions running; its spine and its hero image contribute.
- `concepts/children-are-born-persons.md` — prompts are invitations, all the way down.
- `concepts/knowledge-as-food.md` — the unit nourishes; no twaddle in the manifest's own prose.
- `concepts/knowledge-of-god-man-universe.md` — canonical observation practices for observation-shaped units (nature study, picture study, music appreciation, handicraft).

The unit manifest should be open and go for the teacher: what to pick up each day, what to read or observe, what materials are needed, what the narration close is, and how the lessons fit together, with no advance decoding required.

## Spine book

Every unit has a spine — a single living book (or, rarely, a named artwork set / composer set / field site) that the unit rests on. This is Mason's "form book" pattern applied at the unit scale: one attentive read across several sessions beats a different book every day.

### Choosing the spine

1. **If the prompt names a book**, use it. Look it up via the Open Library helper to verify it exists and to get an ISBN URL; if the helper can't confirm the exact title, say so in the delivery and ask the user — never invent.
2. **If curriculum-builder passed an overarching spine in the prose**, use that spine for this unit. Don't pick a different one.
3. **Otherwise pick one** via the Open Library helper:

```bash
.venv/bin/python scripts/openlibrary/subject_search.py "<unit theme>" --limit 15
```

Run from the project root. The venv and the script are both relative to the repo.

Pick a `chapter_book` or `middle_grade` result with living-book quality (narrative, single-author, not a committee-written reference). Match the `type` field to the student's grade: `picture_book` for preschool/K, `chapter_book` for 1st–4th, `middle_grade` for upper grades. Prefer the ISBN URL (`https://openlibrary.org/isbn/<isbn>`) over the work URL — the work-page cover edition is sometimes a non-English translation.

For observation-shaped units (nature study, picture study, music appreciation) the "spine" is not a book but a subject — one tree across the seasons, one painter's four watercolors, one composer's short set. Record that in the spine frontmatter instead of a book.

4. **If nothing suitable comes back**, say so in the delivery and fall back to a per-lesson-reading unit — each lesson picks its own short reading. Note this choice in `unit.md`. Do not fabricate a spine.

### Passing the spine to lessons

When unit-builder invokes lesson-plan-builder for each lesson, the spine (title, author, OL URL, chapter/section for this session) is included in the prose prompt. The spine is the **main reading material** of the lesson — the meat of the session when the session reads. It is not a default to be casually swapped for something the lesson-plan thinks fits better, and it is not to be disregarded.

A lesson is still free to add a **supplementary reading** alongside the spine — a poem, a one-page article, a short picture book, even a chapter from a different book — when the session genuinely calls for one, and is free to query Open Library to find that supplement. What the lesson may not do is replace the spine with something else. Core reading = spine; supplements = whatever fits.

If the spine genuinely cannot carry a particular session (e.g., the unit's spine is a chapter book but this session is a picture-study of an artwork the spine doesn't touch), the lesson may source its own primary material — and record why in one sentence under "Materials in hand." This should be rare; if it's happening often, the unit's spine was the wrong choice and unit-builder should hear the feedback back from the user.

## What the unit produces

Every run produces:

1. A unit manifest at `curricula/<class-slug>/<unit-slug>/unit.md`.
2. A **unique hero illustration** for the unit, embedded at the top of `unit.md`.
3. N lesson files, one per lesson (unless `--no-lessons`), each generated by invoking `lesson-plan-builder --auto` with unit metadata and the spine book passed in prose.
4. Zero or more field-trip files under `field-trips/` (only when the user asked for them), cross-linked in `unit.md` and in the owning lesson(s) when relevant.

Every generated markdown file is a node in a connected navigation graph (see "Navigation contract" below). Every material, image, book, and venue named anywhere in the unit has a link; nothing is referenced as a bare name.

## Paths and naming

The layout adds `unit.md` to the existing three-deep class → unit → lesson scheme. Unit-level `images/` and `materials/` are shared across every lesson in the unit.

```
curricula/
  <class-slug>/
    curriculum.md                                # only if a parent curriculum exists
    images/<class-slug>-hero.png                 # only if curriculum.md exists
    <unit-slug>/
      unit.md                                    # new — the unit manifest
      images/
        <unit-slug>-hero.png                     # unit's unique hero (always)
        <lesson-slug>-hero.png                   # each lesson's unique hero
      materials/
        <lesson-slug>-<kind>.<ext>
      lesson-01-<lesson-slug>.md                 # ordinals required under unit-builder
      lesson-02-<lesson-slug>.md
```

Slug rules match lesson-plan-builder: lowercase kebab-case, no dates, no student names.

### Ordinals

Unit-builder **always** prefixes new lesson files with `lesson-NN-` (zero-padded). A unit is a planned sequence; ordering is the whole point.

### Retrofit (existing units)

If the target unit directory already exists and contains loose lessons (no ordinals), **do not rename or renumber them.** New lessons get ordinals picked up after the highest existing ordinal (or starting at 01 if there are none). The `unit.md` lesson-sequence table lists the loose lessons first without ordinals, then the new ordinaled lessons — note the mixed state in one line at the top of the manifest.

If the user wants full renumbering, they ask for it explicitly in prose. That's a separate, destructive operation.

### Save path

Default: `curricula/<class-slug>/<unit-slug>/`. Override with `--save PATH` (directory). If the directory doesn't exist, create it. If `unit.md` already exists at the target and the user didn't say "extend" or "retrofit," ask once before overwriting.

## Workflow

### Step 1 — Parse and resolve

Extract class, unit theme, student, lesson count, spine wish, field-trip wish, flags. Resolve student against `students.yaml`. Infer class/unit slugs. Compute lesson count from the grade default if neither a flag nor prose gave one.

If curriculum-builder invoked this skill, also extract: parent curriculum slug, ordinal within the curriculum, pace budget (minutes per lesson), and any overarching spine book.

### Step 2 — Read the pedagogy pages that apply

Read them this run, with the Read tool, before designing. Pages listed in "Pedagogical framing" above. This is not satisfied by "I've read these before."

If a sibling unit in the same class directory already exists (e.g., other `unit.md` files under `curricula/<class-slug>/`), read one for tone reference *after* the pedagogy pages, not instead of them.

### Step 3 — Pick the spine book

Follow "Spine book" above. Record the spine's title, author, and ISBN/work URL — you will cite it in `unit.md` frontmatter and pass it to every lesson.

### Step 4 — Design the arc

Decide the activity shape(s) across the unit: reading-shaped, observation-shaped, practice-shaped, or hybrid. Sketch the lesson sequence — each lesson is a concrete session title (`symbiosis`, `predation-and-competition`, `decomposers`), not an outline. Name the relations the unit opens, concretely, in 2–3 sentences.

Decide whether each lesson uses the unit spine (single reading of a chapter) or diverges (a short supplementary text because that session calls for it). Record per-lesson spine usage in the unit manifest's sequence table.

### Step 5 — Generate the unit hero image (always)

**Invoke `materials-builder` inline.** A single hero image is cheap; loading materials-builder's instructions into the current context and running them here is the right tradeoff. (See [`CLAUDE.md` § Sub-agent spawn convention](../../../CLAUDE.md#sub-agent-spawn-convention).)

Pass it this prompt:

> Illustration for a homeschool unit on `<unit theme>`. Landscape 4:3. `<one sentence on visual subject>`. No text, no labels. Save to `curricula/<class-slug>/<unit-slug>/images/<unit-slug>-hero.png`.

Let materials-builder decide the register and configured image route. Record the returned route/source/model for the delivery message.

The unit hero is **unique** — it is not reused for any lesson. Each lesson generates its own hero under lesson-plan-builder.

### Step 6 — Generate field trips (only if requested)

If `--field-trip` was passed or the prose named a trip, **spawn `field-trip-planner` once per requested trip** as a sub-agent. Trip planning is heavy own work (Maps queries, candidate ranking, prose write-up) and benefits from its own context. Run spawns serially.

- **Skill:** `field-trip-planner`
- **Capability:** use a model/tool context that can handle local pedagogy synthesis, Maps/place research, candidate ranking, and structured markdown generation.
- **Prompt:** a self-contained prose block carrying: requested trip subject + location, unit slug, parent curriculum slug (if present), `--auto`, the path the trip file should land at, and any one-sentence pedagogical hook. Include everything — the spawn has no view of this skill's working memory.

Collect the saved paths each spawn returns. If a spawn cannot resolve a venue, surface that in the delivery rather than retrying with a different prompt.

If no trip was requested, skip this step entirely. Do not pre-emptively plan a trip the user didn't ask for.

### Step 7 — Write `unit.md`

Write `curricula/<class-slug>/<unit-slug>/unit.md` in the shape below. Embed the unit hero at the top with a markdown image. Embed the lesson-sequence table inline; link each lesson row to its file. Embed a "Part of:" line linking UP to `../curriculum.md` only if one exists.

```markdown
---
class: "<Class, human-readable, e.g. '3rd-Grade Science'>"
class_slug: <class-slug>
unit: "<Unit, human-readable, e.g. 'Organism Relationships'>"
unit_slug: <unit-slug>
parent_curriculum: ../curriculum.md   # or null if this unit stands alone
student: "<display_name or 'unassigned'>"
grade: <grade or 'unassigned'>
lesson_count: <N>
activity_shapes: [<reading|observation|practice|hybrid>, ...]
spine:
  type: <book|observation_subject>
  title: "<book title OR 'One painter: John Singer Sargent' for observation>"
  author: "<author or null>"
  url: "<OL ISBN url or work url; null if type is observation_subject and there is no book>"
concepts: [<wiki concept slugs this unit leans on>]
relations_opened: [<from: persons, nature, art, country, past, present, mathematics, language, God>]
field_trips: [<../../../field-trips/<filename>.md>, ...]   # absent if no trips
---

![<alt text>](images/<unit-slug>-hero.png)

# <Class>: <Unit>

**Part of:** [<Curriculum Name>](../curriculum.md)     <!-- omit the whole line if parent_curriculum is null -->

**For:** <display_name, grade> · **Lessons:** N

## Why this unit

<2–3 sentences naming the arc concretely: which relations from [science-of-relations](../../../pedagogy/wiki/concepts/science-of-relations.md) this unit opens across its whole sweep, and how the lessons hang together. Not decoration — this is the unit's pedagogical rationale.>

## Spine

<One short paragraph on the spine book (or observation subject). If a book: title, author, one sentence on why it carries the unit, and an Open Library link. If an observation subject: what it is, why one subject across the whole unit beats rotating subjects.>

- **[<Book title>](<OL url>)** by <Author> — <one sentence on why it opens the unit's relations>

## Lesson sequence

| # | Lesson | Shape | Spine chapter / section | Link |
|---|---|---|---|---|
| 1 | <Lesson Name> | reading / observation / practice / hybrid | <ch. 1, pp. 3–12>  |  [lesson-01-<slug>.md](lesson-01-<slug>.md) |
| 2 | <Lesson Name> | ... | ... | [lesson-02-<slug>.md](lesson-02-<slug>.md) |
| ... |

<If retrofitting over existing loose lessons, list them at the top without an ordinal column and note the mixed state in a single sentence above the table.>

## Field trips

<Omit this whole section if none were generated.>

- [<Trip title>](../../../field-trips/<filename>.md) — <one sentence on which lesson it hooks to and what relation it opens>

## Feeding forward

<1–2 threads this unit opens for future units. Kept terse — curriculum-builder picks these up.>

- <thread 1>
- <thread 2>

## Notes on method

<One short paragraph reminding the teacher of the method-specific rules applicable across the unit: single reading when reading; silent sustained attention when observing; narration close on every session. Reference wiki pages inline as real markdown links, e.g. [narration](../../../pedagogy/wiki/concepts/narration.md) (three-deep from `curricula/<class>/<unit>/unit.md`).>
```

### Step 8 — Generate the lessons (unless `--no-lessons`)

**Spawn `lesson-plan-builder` once per lesson** as a sub-agent. Each lesson is heavy own work (pedagogy reads, hero generation, materials decisions, manifest write); 3–6 of these in a row will not fit in this skill's context. Run spawns serially — lessons share the unit's `images/` and `materials/` directories, and parallel spawns would race on directory creation and asset naming.

- **Skill:** `lesson-plan-builder`
- **Capability:** use a model strong enough for long-form lesson writing, pedagogy synthesis, file creation, and image/material decisions. Avoid lightweight summarization-only worker models for this spawn.
- **Prompt** (prose, self-contained — the spawn has no view of this skill's working memory; include every input it needs):

> Lesson <NN> of <N> in the <unit human name> unit (<unit-slug>) of <class human name> (<class-slug>). Today's lesson: <lesson human name> (<lesson-slug>). <Activity shape: reading|observation|practice|hybrid.> <Spine book or spine subject: "<Title>" by <Author>, [link](<url>), <chapter/section for this lesson>.> For <student display_name or "an unassigned <grade>-grader">. <One short sentence on the specific angle for this session.>
>
> Save the lesson file at `curricula/<class-slug>/<unit-slug>/lesson-<NN>-<lesson-slug>.md`. Generate the lesson hero image at `curricula/<class-slug>/<unit-slug>/images/<lesson-slug>-hero.png`. The unit's `unit.md` is at `unit.md` from the lesson — link UP via "Part of:" and use `../../../pedagogy/wiki/...` for pedagogy references.
>
> <If parent curriculum exists:> This unit is part of the <curriculum human name> curriculum at `../curriculum.md` (relative to the unit). From the lesson, the curriculum also sits at `../curriculum.md`. Add a "Part of curriculum:" continuation line. Pedagogy refs from a lesson are three-deep, `../../../pedagogy/...`.
>
> Use --auto. Return the saved lesson path and the hero image's route/source/model.

Each spawn returns a summary that includes the saved lesson path and the hero image's route/source/model. Record both for the Step 9 verification and the Step 10 delivery.

### Step 9 — Stitch navigation

Because lessons were spawned as sub-agents, this skill never watched them being written — verification is post-hoc by reading the saved files. Open each lesson file and check:

- Each lesson has a "Part of: [<Unit>](unit.md)" line in its body header.
- If `../curriculum.md` exists, each lesson has a "· Part of curriculum: [<Curriculum>](../curriculum.md)" continuation on the same line.
- Each lesson has prev/next links at the bottom: `[← Previous lesson](lesson-NN-<slug>.md) · [Next lesson →](lesson-NN-<slug>.md)`. The first lesson has no prev link; the last has no next link.

If any lesson file is missing a link it should have, add it directly with the Edit tool — do not respawn lesson-plan-builder for a missing nav line. Report the patch count in the delivery.

### Step 10 — Deliver

Print a short summary:

- Path of `unit.md`.
- Path of the unit hero image and its route/source/model.
- Paths of all generated lesson files.
- Paths of all field-trip files (if any).
- A single one-line note if anything about the request sits in real tension with the pedagogy — offered as an alternative, never as a correction, never more than once.

## Navigation contract (hard rule)

Every markdown file this skill produces is a node in a connected graph. At minimum:

- **`unit.md`** links DOWN to every lesson file in its sequence table; DOWN to any field-trip files in its field-trips section; UP to `../curriculum.md` via "Part of:" if one exists; OUT to the spine book (OL URL); OUT to pedagogy concept pages as real markdown links.
- **Each lesson file** links UP to `unit.md` via "Part of: [<Unit>](unit.md)"; UP to `../curriculum.md` if one exists; sideways to prev/next lessons when ordinaled; OUT to the spine book and to any pedagogy pages, materials, and books it references. lesson-plan-builder owns writing these; unit-builder verifies on Step 9.
- **Each field-trip file** links UP to the owning unit via its frontmatter (`owning_unit: ../curricula/<class>/<unit>/unit.md`) and a "Part of:" header line; OUT to venue Maps/website as already required by field-trip-planner.
- **Every book** named anywhere has an Open Library URL (ISBN URL when available; work URL otherwise). No bare book names.
- **Every venue** named in a trip file has a Google Maps URL + website (field-trip-planner already enforces this).
- **Every material** file generated for a lesson is linked from the lesson's "Materials in hand" section (lesson-plan-builder already enforces this).
- **Every pedagogy reference** is a real markdown link (`[narration](../../../pedagogy/wiki/concepts/narration.md)` from `unit.md` or a lesson file in `curricula/<class>/<unit>/`), never an Obsidian `[[wiki-link]]`.

A teacher opening any file in this unit in Obsidian should be able to navigate to every other related file without leaving the editor. Test this mentally on every run.

## Rules (hard)

- **Unique hero image on `unit.md`.** Generated by materials-builder, embedded at the top. Never reused as a lesson hero. Never reused across units.
- **Each lesson has its own unique hero** — lesson-plan-builder generates it. Hero images are identifiers; no sharing.
- **Ordinals always** for lessons written by this skill (`lesson-01-`, `lesson-02-`, ...).
- **Retrofit is non-destructive.** Never renumber or rename existing files. Record mixed state in `unit.md`.
- **One spine per unit.** Named in `unit.md` frontmatter and prose. Passed to every lesson. Lessons may still use short supplementary readings when the session calls for one, but the spine is the default.
- **No calendar dates anywhere in `unit.md`** — unit-builder has no calendar. Pace language (`~45 min per session`) is fine; dates (`starting 2026-05-01`) are not. Curricula are date-portable by design.
- **Real markdown links for everything**, including pedagogy references. No `[[wiki-links]]` in generated files.
- **Pedagogy framework applies every time.** Relations are named. Narration closes every lesson in the unit.
- **No fabricated sources.** Book titles, authors, URLs come from the Open Library helper or a user-supplied source. Never from memory.
- **Student data comes from `students.yaml`.** No hard-coded names, aliases, or grades.
- **Field trips only when asked.** Never auto-plan a trip the user didn't request.
- **Curriculum-builder integration:** when invoked from curriculum-builder with a parent slug, pace budget, ordinal, or overarching spine, respect all of them. Name the parent curriculum in `unit.md` frontmatter and in the "Part of:" header line. Pass the parent-curriculum context down to every lesson invocation.
