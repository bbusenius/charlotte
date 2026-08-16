---
name: mason-curriculum-builder
description: Build a Mason-shaped curriculum — a paced sequence of thematic units on one subject — grounded in the project's pedagogy wiki. Produces a curriculum manifest with a hero illustration, zero or more overarching spine books (each covering a span of weeks), N unit directories (each built via mason-unit-builder), and — only when asked — a set of field trips. Owns pacing in weeks / sessions-per-week / minutes-per-session. Never dates.
argument-hint: "<curriculum description in prose: subject, student or grade, pace, optional weekly themes> [--auto] [--weeks N] [--sessions-per-week M] [--minutes L] [--field-trip weekly|culminating|none] [--no-units] [--save PATH]"
---

# Curriculum Builder

Produce one curriculum — a paced sequence of thematic units on one subject — from a free-form prose prompt. Every curriculum is grounded in the Charlotte Mason pedagogy wiki at `pedagogies/charlotte-mason/wiki/` for **how** it is made, regardless of subject. A curriculum built by this skill spans many sessions across many weeks (typically a term, a semester, or a school year) and comprises several units, each of which comprises several lessons.

This skill owns the *pace and the arc across units* — how many weeks, how many sessions per week, how long each session runs, what each week is about, and how weekly themes group into units. It does not own unit design (mason-unit-builder does), does not own individual lesson design (mason-lesson-plan-builder does), does not own rendering (mason-materials-builder does), and does not plan field trips (mason-field-trip-planner does).

It also owns the **overarching spine(s)** (if any) — zero or more living books, each running underneath a defined span of weeks above the per-unit spines. Mason's "form book" pattern, scaled up.

## Usage

- `/mason-curriculum-builder A 12-week Spanish curriculum for Alice — 3 sessions/week, 45 min each, weekly themes: greetings, family, food, the home, the city, the market, the kitchen, the calendar, weather, animals, the body, review --auto`
- `/mason-curriculum-builder A one-semester (16 weeks) 3rd-grade science curriculum on living systems — 2 sessions/week, 30 min each --auto`
- `/mason-curriculum-builder A year-long Guatemalan history curriculum for a 3rd grader, 3 sessions/week, 40 min, anchored by Peter Lourie's "Jungle Journey" as the overarching spine`
- `/mason-curriculum-builder A 6-week handicraft curriculum for Charlie — one session/week, 20 min, weekly themes: running stitch, cross stitch, buttons, hems, patches, mending --field-trip culminating`
- `/mason-curriculum-builder Extend the existing 3rd-grade-science curriculum with a 4-week unit on weather --no-units`

### Flags

- `--auto` — skip any clarifying questions; take defaults and write the curriculum. Every mason-unit-builder invocation inherits this flag.
- `--weeks N` — override any prose. Number of weeks the curriculum runs.
- `--sessions-per-week M` — override any prose. Typical sessions per week.
- `--minutes L` — override any prose. Minutes per session.
- `--field-trip weekly|culminating|none` — trip pattern. `weekly` = one trip per unit, cross-linked to the unit that owns it. `culminating` = one trip at the end of the curriculum, linked from `curriculum.md` itself. `none` = generate no trips (default). Prose like "with a culminating field trip to X" is equivalent to `--field-trip culminating`.
- `--no-units` — write `curriculum.md` only; defer unit generation for a second pass. Useful when the teacher wants to review the overall arc before unit/lesson work begins.
- `--save PATH` — override the default output directory.

## Inputs (parsed from the prompt)

The prompt is free-form prose. Extract:

1. **Class / subject** (required, usually inferable). Same rules as mason-lesson-plan-builder and mason-unit-builder. "3rd-grade science" → `3rd-grade-science`. "Spanish for a 3rd grader" → `3rd-grade-spanish`. "Handicraft for Alice" → lookup Alice's grade in `students.yaml`, then `<grade>-grade-handicraft`. Lowercase kebab-case.
2. **Curriculum theme or name** (optional) — if the user names the curriculum in its own terms (e.g. "Guatemalan History", "Living Systems"), use that as the curriculum slug. If they don't, the curriculum slug equals the class slug — i.e., the curriculum *is* the class at this grade level.
3. **Student** (optional) — matched against `students.yaml` by slug + aliases, the same way mason-unit-builder matches. Used for length defaults, register, and to resolve an unspecified grade. Not used for subject authoring.
4. **Pace** (required) — weeks, sessions per week, minutes per session. From flags if given, otherwise from prose ("12-week", "3 sessions/week", "45 min each"), otherwise from grade defaults: preschool/K → 2×/week, 15–20 min; 1st–4th → 3×/week, 30–45 min; 5th+ → 4–5×/week, 45–60 min. Weeks cannot be inferred from a grade default — if neither flag nor prose names a week count and the prompt isn't under `--auto`, ask once.
5. **Weekly themes** (optional, but common) — an ordered list naming what each week is about. If present, they drive unit grouping in Step 4. If absent, mason-unit-builder will be handed the broader theme and asked to decompose it internally across a suggested number of units.
6. **Overarching spine wish** (optional) — if the user names a book as the spine of the whole curriculum, use it. Otherwise, decide in Step 3 whether to pick one (see "Overarching spine" below).
7. **Field-trip wish** (optional) — from `--field-trip` or prose ("with a weekly field trip", "culminating trip to the market"). Default is `none`.

If anything required is genuinely ambiguous and not under `--auto`, ask once and stop. Under `--auto`, pick the most plausible interpretation, state it in one line at the top of the delivery, and proceed.

## Student configuration

Student metadata lives in `students.yaml` at the repo root. mason-curriculum-builder uses: `display_name`, `grade`, and `aliases`. It does **not** use `subjects`, `curricula_dir`, or `curricula` — those assign existing curriculum entrypoints; this skill is authoring a new curriculum.

Resolution procedure is the same as mason-lesson-plan-builder and mason-unit-builder: read `students.yaml`, lowercase-match prompt name references against each student's slug and `aliases` list, record `display_name` and `grade` on a hit. On no hit with a grade in the prompt, proceed on grade alone. On no hit and no grade, design for mid-elementary. Never hard-code student names, aliases, or grades.

For a multi-student curriculum ("a Spanish curriculum for Alice and Charlie"), resolve both. Record them in frontmatter as a list and design it family-style: a common spine and common relations, with differentiated narration expectations by age, not parallel siblings running separate tracks.

## Pedagogical framing

Re-read any of these wiki pages whose language you are about to use. The vocabulary is load-bearing and should not drift.

All of mason-unit-builder's required set applies (`science-of-relations`, `act-of-knowing`, `narration`, `living-books`, `single-reading`, `education-is-atmosphere-discipline-life`, `children-are-born-persons`, `knowledge-as-food`, `knowledge-of-god-man-universe` where observation-shaped), plus:

- `concepts/liberal-education-for-all.md` — consult when the subject mix tempts narrowing (e.g. a "math-only" curriculum for a struggling student). Mason's conviction is that every child has a right to a wide feast, not a remedial trench. Flag the tension if it surfaces; never override the user.

mason-curriculum-builder writes a pilot-driven manifest: the teacher steers the curriculum, not a scope-and-sequence chart. The manifest must also be open and go: the teacher should be able to pick up any week's unit and know what to do without re-decoding. The frontmatter and the "Units" table are the teacher's dashboard.

## Pacing: the contract

Pacing is the thing this skill owns and no other skill does. It is expressed strictly in:

- **weeks** (integer, `N`),
- **sessions per week** (integer, `M`),
- **minutes per session** (integer, `L`),
- **total sessions** (computed, `N × M`).

**No calendar-anchor dates in any generated file.** Not in filenames, not in frontmatter, not in body prose. A calendar anchor is anything that ties the work to a specific school year, term, or month: `2026-09-14`, `September 2026`, `fall term`, `starting next Monday`, `Week of Oct 3`. Curricula (and the units, lessons, and trips that hang off them) are date-portable by design — reusable next year, or by another family on a different calendar, without edits.

"Week 1," "Week 2," "Weeks 3–4," "total sessions," and "minutes per session" are the pace vocabulary that *anchors* generated files. Phrases like "starting September," "fall term," "second semester" do not.

**Incidental time references are fine** when they carry pedagogical or logistical meaning rather than calendar anchoring:

- **Venue opening hours** pulled from Google Maps into a field-trip plan's Logistics section (e.g. "Tue–Sun 9am–5pm"). Those come from `mcp__google-maps__maps_place_details` and render exactly as returned.
- **Time-of-day qualifiers** when the activity is genuinely time-bound — "astronomy observation happens after dusk," "the nature walk works best in early morning when birds are active," "allow a full morning for the on-site session." Morning / afternoon / evening / dusk / dawn are free to appear wherever the lesson, unit, or trip actually depends on them.
- **Session lengths** ("~45 min," "15-minute narration window") — already implied by the pace contract.

The test is simple: if deleting the phrase would force the teacher to pick a different week or year to run the curriculum, it's a calendar anchor and it doesn't belong. If the phrase is still true next year on any calendar, it's fine.

### Deciding how weekly themes group into units

If the prompt supplied an ordered list of weekly themes, decide — in one pass before writing anything — how they group into units:

- **Each week is its own unit** when themes are topic-adjacent-but-independent (a "tour" curriculum: greetings, family, food, the home, ...). Each week gets its own unit directory, one unit per week.
- **Several consecutive weeks share a unit** when themes are facets of one arc (e.g. weeks 1–3 = "Maya origins," weeks 4–6 = "Classic period," weeks 7–8 = "Post-conquest"). Each multi-week block is one unit; the unit gets `weeks × sessions-per-week` lessons.
- **Mixed** is allowed and common (a unit that's 1 week and another that's 3 weeks). State the decision in one line at the top of the `curriculum.md` body so the teacher sees it immediately: `This curriculum is 8 units across 12 weeks (units 2 and 5 are 3 weeks each; the rest are 1 week).`

If themes weren't supplied, hand mason-unit-builder the broader theme plus a suggested unit count (roughly `weeks / 2` for adjacency-heavy subjects like language; `weeks / 3` for arc-heavy subjects like history or science). mason-unit-builder will decompose internally.

### Pace budget passed to each unit

Each unit gets a slice of the pace budget in its invocation prose:

- **Lessons in this unit** = `weeks_in_unit × sessions_per_week`.
- **Minutes per lesson** = the curriculum's `minutes_per_session`.
- **Ordinal within curriculum** = 1..U.

mason-unit-builder respects both: it produces exactly that many lesson files at that session length.

## Overarching spine(s)

A curriculum *may* have one or more overarching spines — living books (or long-form subjects) that run underneath the whole thing or a defined span of it, above the per-unit spines. Mason's "form book" pattern applied at the curriculum scale.

The common shapes:

- **Zero overarching spines** — every unit picks its own per-unit spine. Right for practice-shaped curricula with no reading component (math, handwriting drills, phonics-blend drills) and observation-shaped curricula with no reading thread (a nature-study curriculum where each unit attends to a different organism with no narrative running underneath). The disqualifier is the absence of any place a living book could sit.
- **One overarching spine** — a single book carries the whole curriculum. Right for short-to-medium history, literature, or country-study curricula where one narrative genuinely touches every unit; for foreign-language curricula carried by a graded reader or chapter book at the student's target reading level; and for shorter curricula (down to 4 weeks) where the right book at the right reading level can be read in the time available.
- **Two or more overarching spines, each covering a span of weeks** — right for longer curricula where no one book can carry the full sweep, but each half (or third, or quarter) has a coherent arc that one book can. A year-long history curriculum might use one narrative through the medieval period and another through the Renaissance; a semester of literature might use one read-aloud for the first eight weeks and another for the last eight.

The choice is about coverage, not preference. If one book can honestly carry every unit, use one. If no single book can but two can split the curriculum cleanly along a real seam, use two. If it would take four or five overarching spines to keep coverage honest, you're really running a per-unit-spine curriculum and should say so.

### Choosing the overarching spine(s)

1. **If the prompt names a book (or books)**, use them. Look each up via the Open Library helper to verify it exists and get an ISBN URL; if the helper can't confirm the exact title, say so in the delivery and ask the user — never invent. When the prompt names a book and assigns it to a span ("Jungle Journey for the first half, Popol Vuh retellings for the second"), respect the span.
2. **Otherwise, decide whether the curriculum wants any overarching spine, and if so how many**:
   - **Zero good candidates**: practice-shaped curricula with no reading component (a math curriculum, a handwriting drill curriculum, a phonics-blend drill curriculum); observation-shaped curricula with no reading thread (e.g. a nature-study curriculum where each unit attends to a different organism with no narrative running underneath). The disqualifier is the absence of any place a living book could sit, not the subject label.
   - **One-spine candidates**: a one-semester (≤16 weeks) history curriculum carried by one narrative; a country-study term anchored by one traveler's narrative; a literature term anchored by one read-aloud; a foreign-language curriculum carried by a graded reader or a chapter book at the student's target reading level (language classes do this all the time — one living book gives the vocabulary somewhere to land); a short 4–6 week curriculum where the right book at the right reading level can be read in four weeks.
   - **Multi-spine candidates**: a year-long curriculum (32+ weeks) where the subject genuinely shifts midway — different period of history, different region, different genre, different language register. The seam between spines should align with a real shift in the curriculum's content, not be picked to make the math come out even.
   - **Rule of thumb**: if every unit would genuinely touch the overarching spine at least once, pick one. If most would, but a contiguous block of units wouldn't, that block wants its own spine — pick two and assign spans. If you can't draw clean spans, don't pick any.
3. **For each spine you do pick**, run the Open Library helper:

```bash
.venv/bin/python scripts/openlibrary/subject_search.py "<spine's span theme>" --limit 15
```

Run from the project root. Match the `type` to the student's grade (`chapter_book` for 1st–4th, `middle_grade` for upper). Prefer an ISBN URL over a work URL.

4. **If nothing suitable surfaces for one of your spans, skip the overarching spine for that span.** Per-unit spines fill the gap. Note the choice in `curriculum.md`.

### Spans

Each overarching spine has a `weeks_covered` span expressed in week ordinals — e.g. `weeks_covered: [1, 6]` for "weeks 1–6 inclusive," or `weeks_covered: [1, 32]` for a single spine across a full year. Spans must not overlap. Together they need not cover every week (gaps are fine — those weeks fall back to per-unit spines).

### Passing the overarching spine(s) down

When the curriculum has overarching spine(s), mason-curriculum-builder passes the *applicable* spine to each mason-unit-builder invocation in the prose prompt — based on which span the unit's weeks fall in. mason-unit-builder's rule is: if an overarching spine is passed, use that spine for the unit (don't pick a different one). The per-unit spine choice is overridden by the curriculum's choice. Lessons that don't genuinely touch the spine can still source a short supplementary reading — the spine is a default, not a cage.

When a unit's weeks fall in a gap between (or outside) any spine's span, no overarching spine is passed and the unit picks its own per-unit spine normally.

## What the curriculum produces

Every run produces:

1. A curriculum manifest at `curricula/<curriculum-slug>/curriculum.md`.
2. A **unique hero illustration** for the curriculum, embedded at the top of `curriculum.md`.
3. U unit directories under `curricula/<curriculum-slug>/`, one per unit (unless `--no-units`), each generated by invoking `mason-unit-builder --auto` with the curriculum's context passed in prose.
4. Zero or more field-trip files under `field-trips/` (only when the user asked for them via `--field-trip` or prose), cross-linked in the right unit and/or the curriculum manifest.

Every generated markdown file is a node in a connected navigation graph (see "Navigation contract" below). Every material, image, book, and venue named anywhere in the curriculum has a link; nothing is referenced as a bare name.

## Paths and naming

The curriculum lives one directory above its units — the layout is now four-deep: **curriculum → unit → lesson**, with optional field trips hanging off the top-level `field-trips/` directory.

```
curricula/
  <curriculum-slug>/
    curriculum.md                                 # new — the curriculum manifest
    images/
      <curriculum-slug>-hero.png                  # curriculum's unique hero (always)
    <unit-1-slug>/
      unit.md                                     # written by mason-unit-builder
      images/
        <unit-1-slug>-hero.png                    # unit's unique hero
        <lesson-slug>-hero.png                    # each lesson's unique hero
      materials/
        <lesson-slug>-<kind>.<ext>
      lesson-01-<slug>.md
      lesson-02-<slug>.md
      ...
    <unit-2-slug>/
      ...
field-trips/
  <venue-slug>.md                                 # only when --field-trip was set; <venue-slug>-<theme-slug>.md if a venue is reused on a different theme
```

### Curriculum slug

- If the prompt names the curriculum in its own terms ("Guatemalan history", "Living Systems"), slug it accordingly: `guatemalan-history`, `living-systems`. Append grade when it would otherwise collide (`guatemalan-history-3rd-grade`).
- If the prompt doesn't — the curriculum *is* the class at that grade — the curriculum slug defaults to the class slug (`3rd-grade-science`, `3rd-grade-spanish`). **But this default is contingent on the class-slug directory being free.** See "Collision check" below.
- Lowercase kebab-case. No dates. No student names.

### Collision check (runs before anything hits disk)

Before finalizing the curriculum slug, inspect `curricula/<candidate-slug>/`:

1. **`curriculum.md` already exists at that path.** This is a real collision. Ask the user whether to (a) extend/overwrite the existing curriculum, (b) pick a different slug, or (c) abort. Under `--auto`, abort and print the three options — never silently overwrite an existing curriculum manifest.
2. **The directory contains unit directories (each with a `unit.md`) but no `curriculum.md`.** This is the retrofit-a-class-into-a-curriculum case. Confirm with the user that the existing units should be treated as already-belonging-to this new curriculum (they'll be listed in the Units table and get their `parent_curriculum` frontmatter patched). Under `--auto`, proceed with that assumption and state the decision explicitly at the top of the delivery. If the user rejects it, they should pick a different slug.
3. **The directory contains unit directories that would plausibly *not* belong to this curriculum** (e.g. the user is building a second-semester 3rd-grade-science curriculum and the class-slug directory already holds the first semester's work). The signal for this is usually a mismatch between the existing unit themes and the new curriculum's theme, or an explicit cue in the prompt ("a second semester of..."). Do not claim those units. Pick a qualified slug: `<class-slug>-<theme>` (e.g. `3rd-grade-science-weather`) or `<class-slug>-<term>` expressed in pace terms not calendar terms (e.g. `3rd-grade-science-term-2`). Under `--auto`, pick the qualifier from the prompt and state the decision; without `--auto`, propose it and confirm.
4. **The directory doesn't exist.** Clean case. Use the default slug as computed.

The rule underneath all of this: **one `curriculum.md` per directory, never more.** And a curriculum never retroactively claims work it didn't mean to inherit. When in doubt, qualify the slug rather than collide.

### Unit slugs

Come from the weekly themes (when supplied) or are picked by mason-unit-builder. mason-curriculum-builder determines unit slugs *before* invoking mason-unit-builder — it needs them to populate the `curriculum.md` Units table. Pass each slug into the corresponding mason-unit-builder invocation so the slug matches.

### Retrofit (existing curricula)

The collision check above decides *whether* to retrofit; this section covers *how* to do it once the decision has been made.

When retrofitting a class directory into a curriculum (case 2 in the collision check): write `curriculum.md` alongside the existing unit directories; reference each existing `unit.md` in the Units table; patch each existing `unit.md`'s `parent_curriculum` frontmatter to `../curriculum.md` and add the "Part of:" header line if absent. Do not regenerate units unless the user asks. Record the mixed state in one line at the top of the manifest.

If `--no-units` is set, write only `curriculum.md` (with its hero) and stop — even on a fresh run with no pre-existing units.

**Never renumber or rename existing unit directories, existing lesson files, or existing assets.** If the user wants full renumbering, they ask for it explicitly in prose.

### Save path

Default: `curricula/<curriculum-slug>/`. Override with `--save PATH` (directory). If the directory doesn't exist, create it. If `curriculum.md` already exists at the target and the user didn't say "extend" or "retrofit," ask once before overwriting.

## Workflow

### Step 1 — Parse and resolve

Extract class, curriculum theme, student(s), pace (weeks, sessions/week, minutes), weekly themes (if any), overarching spine wish, field-trip wish, flags. Resolve student(s) against `students.yaml`. Infer class and curriculum slugs. Compute any missing pace numbers from grade defaults. Confirm weeks is known (ask once if not, unless `--auto`).

Then run the **collision check** ("Curriculum slug" → "Collision check" above) against the candidate slug. Resolve any collision now, before Step 2 — once the slug is final, nothing downstream needs to revisit it.

### Step 2 — Read the pedagogy pages that apply

Read them this run, with the Read tool, before designing. Use mason-unit-builder's required set. Add `liberal-education-for-all.md` if the subject mix feels narrow. This step is not satisfied by "I've read these before." Also apply the plain-language curriculum rules above: pilot-driven, open and go, and family-style when multiple students are named.

If a sibling curriculum in the same class directory or a related curriculum already exists (e.g., an older `curriculum.md` elsewhere under `curricula/`), read one for tone reference *after* the pedagogy pages.

### Step 3 — Pick the overarching spine(s) (or decide not to)

Follow "Overarching spine(s)" above. For each spine the curriculum gets, record title, author, ISBN/work URL, and `weeks_covered` span — you will cite each in `curriculum.md` frontmatter and pass the applicable one to each mason-unit-builder invocation in Step 7 based on the unit's weeks. If the curriculum gets zero overarching spines, write one sentence in `curriculum.md`'s Spine section explaining why the curriculum uses a per-unit spine model instead.

### Step 4 — Decide unit grouping and slugs

Using the rules in "Deciding how weekly themes group into units" above, compute:

- **Number of units** (`U`).
- **For each unit**: slug, human-readable name, the weeks it spans (e.g. "week 1" or "weeks 3–5"), and the resulting lesson count (`weeks_in_unit × sessions_per_week`).
- **One-line summary** of the grouping, to appear at the top of `curriculum.md`'s body.

Write this table mentally before anything hits disk — you'll need it for the manifest *and* for the mason-unit-builder invocations.

### Step 5 — Generate the curriculum hero image (always)

**Invoke `mason-materials-builder` inline.** A single hero image is cheap; loading mason-materials-builder's instructions into the current context and running them here is the right tradeoff. (See [`CLAUDE.md` § Sub-agent spawn convention](../../../CLAUDE.md#sub-agent-spawn-convention).)

Pass it this prompt:

> Illustration for a homeschool curriculum on `<curriculum theme>`. Landscape 4:3. `<one sentence on visual subject — an image that holds the whole arc, not one unit's worth>`. No text, no labels. Save to `curricula/<curriculum-slug>/images/<curriculum-slug>-hero.png`.

Let mason-materials-builder decide the register and configured image route. Record the returned route/source/model for the delivery message.

The curriculum hero is **unique** — not reused for any unit or lesson. Each unit will generate its own unit hero; each lesson its own lesson hero.

### Step 6 — Write `curriculum.md`

Write `curricula/<curriculum-slug>/curriculum.md` in the shape below. Embed the curriculum hero at the top with a markdown image. Embed the Units table inline; link each unit row to the `unit.md` file at its path (which will exist after Step 7, or be a dead link under `--no-units` — this is acceptable, noted in the manifest).

```markdown
---
curriculum: "<Curriculum, human-readable, e.g. 'Guatemalan History'>"
curriculum_slug: <curriculum-slug>
class: "<Underlying class/subject+grade, human-readable, e.g. '3rd-Grade History'>"
class_slug: <class-slug>
student: "<display_name>"                         # or a YAML list if multi-student
grade: <grade or 'unassigned'>
pace:
  weeks: <N>
  sessions_per_week: <M>
  minutes_per_session: <L>
  total_sessions: <N*M>
unit_count: <U>
overarching_spines:                               # omit this whole block (and the key) if the curriculum has no overarching spine. Use a list even when there's only one spine.
  - type: <book|observation_subject>
    title: "<book title>"
    author: "<author or null>"
    url: "<OL ISBN url or work url>"
    weeks_covered: [<start_week>, <end_week>]    # inclusive; e.g. [1, 16] for weeks 1–16, or [1, 32] for the full year
  # - additional spines, each with its own non-overlapping weeks_covered span
units: [<unit-1-slug>, <unit-2-slug>, ...]
field_trips: [<../../field-trips/<filename>.md>, ...]    # absent if no trips generated at the curriculum level
concepts: [<wiki concept slugs this curriculum leans on>]
relations_opened: [<from: persons, nature, art, country, past, present, mathematics, language, God>]
---

![<alt text>](images/<curriculum-slug>-hero.png)

# Curriculum: <Curriculum Name>

**For:** <display_name, grade>  <!-- or "<display1, grade1> & <display2, grade2>" when multi-student -->
**Pace:** <N> weeks · <M> sessions/week · <L> min/session (total: <N×M> sessions)

<One-line grouping summary from Step 4. Example: "This curriculum is 8 units across 12 weeks (units 2 and 5 are 3 weeks each; the rest are 1 week).">

## Arc

<3–5 sentences on the curriculum's through-line. Which relations from [science-of-relations](../../pedagogies/charlotte-mason/wiki/concepts/science-of-relations.md) open across the whole curriculum, and how the units hang together as one arc. Not decoration — this is the curriculum's pedagogical rationale, the thing the teacher will come back to when a week feels off and she's trying to recover the shape of the whole.>

## Spine

<If the curriculum has no overarching spine, omit the bullet list below and write one sentence explaining that the curriculum rests on per-unit spines instead and why (e.g. "Each week's theme is independent; a single book across all twelve weeks would stretch past breaking."). Otherwise list each overarching spine with its span and a one-sentence rationale. When two or more spines split the curriculum, name the seam between them in one short sentence above the list.>

- **Weeks N1–N2: [<Book title>](<OL url>)** by <Author> — <one sentence on why this book carries this span; what it lets the units in this span touch>
- **Weeks N3–N4: [<Book title>](<OL url>)** by <Author> — <one sentence on why this book picks up where the first leaves off>

## Units

| # | Weeks | Unit | Lessons | Link |
|---|---|---|---|---|
| 1 | 1 | <Unit Name> | <N_1> | [<unit-1-slug>/unit.md](<unit-1-slug>/unit.md) |
| 2 | 2–3 | <Unit Name> | <N_2> | [<unit-2-slug>/unit.md](<unit-2-slug>/unit.md) |
| ... |

<If running with --no-units, add one sentence above the table noting that unit directories have not yet been generated; the links will be created when mason-unit-builder runs.>

## Field trips

<Omit this whole section if no curriculum-level trips were generated. Per-unit trips live inside each `unit.md`, not here.>

- [<Trip title>](../../field-trips/<filename>.md) — <one sentence on which unit(s) it culminates or spans and what relation it opens>

## Feeding forward

<1–2 threads this curriculum opens for future curricula. What natural next step a follow-on year or term might take up. Kept terse.>

- <thread 1>
- <thread 2>

## Notes on method

<One short paragraph reminding the teacher of the method-specific rules that apply across the curriculum: single reading when reading; silent sustained attention when observing; narration closes every session. Pilot-driven: the manifest is a guide, not a cage. Reference wiki pages inline as real markdown links, two-deep from `curricula/<curriculum-slug>/curriculum.md`.>
```

### Step 7 — Generate the units (unless `--no-units`)

**Spawn `mason-unit-builder` once per unit** as a sub-agent. A unit is heavy own work that itself fans out into per-lesson spawns; a curriculum with U units cannot run end-to-end in this skill's context. Run spawns **serially, not in parallel** — units share the top-level `curricula/<curriculum-slug>/` directory and the `field-trips/` directory, and parallel spawns would race on directory creation, ordinal assignment across shared trips, and asset paths.

- **Skill:** `mason-unit-builder`
- **Capability:** use a strong planning/writing model that can design a full unit arc, coordinate lesson generation, maintain navigation/link invariants, and synthesize the pedagogy wiki. Avoid lightweight worker models for this spawn.
- **Prompt** (prose, self-contained — the spawn has no view of this skill's working memory; include every input it needs, plus `--auto` and `--lessons <count>` to lock the pace budget):

> Unit <ordinal> of <total units> in the <curriculum human name> curriculum (<curriculum-slug>). Unit name: <unit human name> (<unit-slug>). <Lesson count: weeks_in_unit × sessions_per_week> lessons at <minutes_per_session> minutes each. <One sentence on the unit's theme, from the weekly theme list or the grouping decision.>
>
> For <student display_name(s) and grade(s) from students.yaml>. Save the unit at `curricula/<curriculum-slug>/<unit-slug>/`.
>
> This unit is part of the <curriculum human name> curriculum at `../curriculum.md`. <If an overarching spine covers this unit's weeks:> The curriculum's overarching spine for weeks N1–N2 (which contains this unit) is "<book title>" by <book author>, [link](OL url here) — use it as this unit's spine as well, unless the specific unit theme genuinely cannot be carried by it (in which case pick a per-unit spine and note why). <If no overarching spine covers this unit's weeks:> The curriculum has no overarching spine for this unit's weeks — pick a per-unit spine normally.
>
> Use --auto and --lessons <count>. Return the saved unit.md path, the N saved lesson paths, and the unit hero image's route/source/model.

Each spawn returns a summary that includes the saved `unit.md` path, the N lesson paths, and the unit hero's route/source/model. Verify on the returned data and by reading the file:

- `unit.md` exists at `curricula/<curriculum-slug>/<unit-slug>/unit.md`.
- The unit's `unit.md` frontmatter has `parent_curriculum: ../curriculum.md`.
- The unit's `unit.md` body carries a "Part of: [<Curriculum Name>](../curriculum.md)" header line.
- Each lesson file under the unit has UP-links to both `unit.md` and `../curriculum.md`. (mason-lesson-plan-builder writes these per its rules; verify post-hoc — this skill never watched the spawn write them.)

Record route/source/model for each unit's hero image if different routes or providers were used.

### Step 8 — Generate field trips (only if requested)

**Spawn `mason-field-trip-planner` once per requested trip** as a sub-agent. Trip planning is heavy own work (Maps queries, candidate ranking, prose write-up). Run spawns serially.

- **Skill:** `mason-field-trip-planner`
- **Capability:** use a model/tool context that can handle local pedagogy synthesis, Maps/place research, candidate ranking, and structured markdown generation.
- **Prompt:** a self-contained prose block with `--auto`, the trip subject and location, the curriculum slug, and (for `weekly`) the unit slug it belongs to. Include the exact paths the trip file's frontmatter should back-reference and where the trip file should land.

If `--field-trip weekly`: after Step 7 completes, walk every unit and spawn one trip per unit, in unit order. The trip file's `owning_unit` becomes `../curricula/<curriculum-slug>/<unit-slug>/unit.md` and `owning_curriculum` becomes `../curricula/<curriculum-slug>/curriculum.md`. After each spawn returns, patch the owning `unit.md`'s `field_trips` frontmatter list and its "Field trips" section to include the new trip — the patch is post-hoc, done by this skill with the Edit tool.

If `--field-trip culminating`: after all units are generated, spawn `mason-field-trip-planner` once with a prompt that spans the whole curriculum arc. The trip file's `owning_curriculum` becomes `../curricula/<curriculum-slug>/curriculum.md`; `owning_unit` is null (the trip belongs to the curriculum as a whole, not one unit). Patch `curriculum.md`'s `field_trips` frontmatter list and its "Field trips" section to include the trip.

If the prose names specific trips (e.g. "a culminating trip to the jade market in Antigua"), pass the named location through in the spawn prompt. If it doesn't, mason-field-trip-planner will need a location — ask once before spawning.

If `--field-trip none` (the default), skip this step entirely. Do not pre-emptively plan trips the user didn't ask for.

### Step 9 — Stitch navigation

After all units (and any field trips) are generated, verify the connected-graph invariant:

- `curriculum.md` links DOWN to every `unit.md` (Units table).
- `curriculum.md` links DOWN to every curriculum-level trip (Field trips section).
- Every `unit.md` has `parent_curriculum: ../curriculum.md` in frontmatter and a "Part of: [<Curriculum>](../curriculum.md)" header line.
- Every `unit.md` links DOWN to every lesson (its lesson sequence table).
- Every `unit.md` links DOWN to every trip it owns (when `--field-trip weekly`).
- Every lesson links UP to `unit.md` and UP to `../curriculum.md`; sideways prev/next resolves.
- Every trip file has `owning_unit` and/or `owning_curriculum` set, and a "Part of:" header line that renders them.
- No `[[wiki-link]]` syntax anywhere in generated files. Every pedagogy reference is a real relative markdown link.
- No calendar-anchor dates anywhere in `curriculum.md`, any `unit.md`, any lesson file, or any trip file. Venue hours sourced from Google Maps and time-of-day qualifiers (morning, afternoon, evening, etc.) are fine when the activity genuinely depends on them — see the pacing contract for the test.

If any link is missing or any invariant is violated, patch it before delivery. Report the patch count.

### Step 10 — Deliver

Print a short summary:

- Path of `curriculum.md`.
- Path of the curriculum hero image and its route/source/model.
- Paths of all generated `unit.md` files.
- Total count of lessons generated, grouped by unit.
- Paths of all field-trip files (if any) and which unit / curriculum they back-reference.
- A single one-line note if anything about the request sits in real tension with the pedagogy (e.g. a 45-minute-per-session pace for a preschooler; a "math-only" scope when `liberal-education-for-all.md` would push back). Offered as an alternative, never as a correction, never more than once.

## Navigation contract (hard rule)

Every markdown file this skill produces — and every file it causes downstream skills to produce — is a node in a connected graph. At minimum:

- **`curriculum.md`** links DOWN to every `unit.md` via its Units table; DOWN to any curriculum-level field-trip files via its Field trips section; OUT to the overarching spine book (OL URL) if any; OUT to pedagogy concept pages as real markdown links.
- **Each `unit.md`** (generated by mason-unit-builder under this skill's orchestration) links UP to `../curriculum.md` via `parent_curriculum` frontmatter and a "Part of:" header line; DOWN to every lesson in its sequence; DOWN to any trips it owns; OUT to spine and pedagogy. mason-unit-builder owns writing these; mason-curriculum-builder verifies on Step 9.
- **Each lesson file** links UP to `unit.md` and `../curriculum.md`; sideways to prev/next when ordinaled; OUT to spine, pedagogy, materials, and books. mason-lesson-plan-builder owns writing these.
- **Each field-trip file** links UP to the owning unit and/or owning curriculum via its frontmatter (`owning_unit`, `owning_curriculum`) and a "Part of:" header line; OUT to venue Maps/website. mason-field-trip-planner owns writing these.
- **Every book** named anywhere has an Open Library URL (ISBN URL when available; work URL otherwise). No bare book names.
- **Every venue** named in a trip file has a Google Maps URL + website (mason-field-trip-planner already enforces this).
- **Every pedagogy reference** is a real markdown link. From `curriculum.md` (two-deep) that looks like `[narration](../../pedagogies/charlotte-mason/wiki/concepts/narration.md)`. Never an Obsidian `[[wiki-link]]`.

A teacher opening any file in this curriculum in Obsidian should be able to navigate to every other related file without leaving the editor. Test this mentally on every run.

## Rules (hard)

- **Unique hero image on `curriculum.md`.** Generated by mason-materials-builder, embedded at the top. Never reused as a unit hero or a lesson hero. Never reused across curricula.
- **Each unit has its own unique hero; each lesson has its own unique hero.** Enforced downstream by mason-unit-builder and mason-lesson-plan-builder respectively. Hero images are identifiers.
- **Pacing is weeks / sessions-per-week / minutes-per-session — always.** No calendar-anchor dates in any generated file (curriculum, unit, lesson, or trip): no specific years, months, terms, or "starting <date>" phrases. Frontmatter, body, and filenames all respect this. Date-portable by design. Venue opening hours from Maps and time-of-day qualifiers (morning / afternoon / evening / dusk / dawn) are fine when the activity genuinely depends on them — see the pacing contract above for the test.
- **Unit grouping is decided once, at the top of the run, and stated in one line in the manifest.** The teacher needs to see the grouping decision before she sees the Units table.
- **Zero, one, or more overarching spines per curriculum.** Each spine has a non-overlapping `weeks_covered` span. Named in frontmatter and prose; the spine applicable to a given unit's weeks is passed down in that mason-unit-builder invocation. When no overarching spine covers a unit's weeks, per-unit spines fill the gap and the manifest says so.
- **mason-unit-builder is invoked with `--auto` and with `--lessons <count>`.** The pace budget is the curriculum's to own; it is not negotiable by the unit.
- **Unit invocations run serially.** Parallel invocations race on shared directories.
- **Retrofit is non-destructive.** Never rename or renumber existing unit directories, existing lesson files, or existing assets. Record mixed state in `curriculum.md`.
- **Real markdown links for everything**, including pedagogy references. No `[[wiki-links]]` in generated files.
- **Pedagogy framework applies every time.** Relations are named across the arc. Narration closes every lesson in every unit. Pilot-driven — the manifest supports the teacher, not the reverse.
- **No fabricated sources.** Book titles, authors, URLs come from the Open Library helper or a user-supplied source. Never from memory.
- **Student data comes from `students.yaml`.** No hard-coded names, aliases, or grades.
- **Field trips only when asked.** Never auto-plan trips the user didn't request. `--field-trip none` is the default; `weekly` and `culminating` both require an explicit opt-in.
- **mason-aesthetics and mason-print-design are never invoked directly.** mason-curriculum-builder calls mason-materials-builder for the curriculum hero and nothing else; mason-aesthetics and mason-print-design are mason-materials-builder's collaborators.
- **No Wikipedia.** Open Library for books; Grokipedia or another verifiable source for short reference material if genuinely needed; no Wikipedia citations in generated files.
