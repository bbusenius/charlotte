---
name: lesson-plan-builder
description: Build a single Mason-shaped lesson plan, grounded in the project's pedagogy wiki, for a named theme and (optionally) a named student. Produces a markdown lesson file with a hero illustration and — when the lesson's activities actually need them — any embedded materials rendered via materials-builder. Unit-builder chains these into a unit; curriculum-builder chains units into a paced curriculum.
argument-hint: <theme in prose, optionally referencing a student or grade> [--auto] [--save PATH] [--length short|standard|long]
---

# Lesson Plan Builder

Produce one lesson plan from a free-form prose prompt. Every plan is grounded in the Charlotte Mason pedagogy wiki at `pedagogy/wiki/` for **how** it is made, regardless of *what* subject is being taught. A lesson built by this skill is a single session (roughly 15–60 min depending on the child), not a unit or a week.

This skill owns the *what* — theme, relations, spine of the session, narration, any materials the session literally uses. It does not own rendering (materials-builder does) and does not plan field trips (field-trip-planner does).

## Usage

- `/lesson-plan-builder Spanish for Alice — greetings and introductions`
- `/lesson-plan-builder A history lesson on how the Maya used jade for a 3rd grader`
- `/lesson-plan-builder Picture study of a Sargent watercolor for Alice`
- `/lesson-plan-builder Nature study — observing a single tree across the seasons (first session) for Alice`
- `/lesson-plan-builder Handicraft for Charlie: simple running stitch on burlap --length short`

### Flags

- `--auto` — skip any clarifying questions; take defaults and write the plan. Intended for curriculum-builder integration.
- `--save PATH` — write the final plan to PATH (a directory or a full `.md` path) instead of the default location.
- `--length short|standard|long` — override the age default. `short` ≈ 15–20 min, `standard` ≈ 30–45 min, `long` ≈ 45–60 min.

## Inputs (parsed from the prompt)

The prompt is free-form prose. Extract:

1. **Subject** (required, usually inferable). Subject is *not* read from `students.yaml` — the `subjects` list there exists for time-tracking against paid curricula we already own, not for lesson authoring. Infer subject from the prompt *and* the student's grade. "Spanish for Alice" (grade 4) resolves to subject slug `4th-grade-spanish`. "Science for a preschooler" → `preschool-science`. Prefer `<grade>-grade-<subject>` when grade is known; drop the grade prefix if only a subject is given. Slugs are lowercase kebab-case.
2. **Theme** (required) — what this specific lesson is about (e.g. `greetings-and-introductions`, `maya-use-of-jade`, `observing-a-single-tree`). Also kebab-case for the slug.
3. **Student** (optional) — matched against `students.yaml` (see below). Used for length default, language register, and to record the intended reader in frontmatter. If no student is named and no grade is given, design for mid-elementary and note that differentiation is available on request — do not block.
4. **Length wish** (optional) — from the `--length` flag or language in the prompt ("short lesson", "full 45 minutes"). If absent, pick from the student's grade: preschool/K → short; 1st–4th → standard; 5th+ → long.
5. **Flags** — as above.

If subject or theme cannot be inferred and the prompt is genuinely ambiguous, ask once and stop. Under `--auto`, pick the most plausible interpretation, state it in one line at the top of the plan, and proceed.

## Student configuration

Student metadata lives in `students.yaml` at the repo root. This skill uses: `display_name` (for address), `grade` (for length and register defaults), `aliases` (for matching prompt references). It does **not** use the `subjects` list (see above) and does **not** use `curricula_dir` or `curricula` (those point at paid third-party curricula this skill is not authoring against).

Resolution procedure:

1. Read `students.yaml`.
2. Lowercase the prompt's name reference and match against each student's slug and every entry in their `aliases` list.
3. On a hit, record the student's `display_name` and `grade`.
4. On no hit but with a grade/age in the prompt, proceed on that.
5. On no hit and no grade, design for mid-elementary.

Never hard-code student names, aliases, or grades.

## Pedagogical framing (applied to every lesson)

Re-read any of these wiki pages whose language you are about to use — the vocabulary is load-bearing and shouldn't be paraphrased loosely:

- `concepts/act-of-knowing.md` — knowing is a definite act completed by narration. This is why every lesson ends in narration.
- `concepts/narration.md` — the child tells back, without prompts, leading questions, or interruption. Universal close-out for every lesson in this skill, reading-based or not.
- `concepts/single-reading.md` — **applies only when the lesson involves reading.** Any reading is attended to once, not drilled.
- `concepts/living-books.md` — **applies only when the lesson involves reading.** A book used in the lesson is first-hand, narrative, author's voice — never a textbook summary. Twaddle cannot be narrated.
- `concepts/science-of-relations.md` — every lesson opens specific relations (to persons, nature, art, country, past, present, mathematics, language, God). The plan names which ones, concretely.
- `concepts/children-are-born-persons.md` — prompts are invitations to a person, not drills.
- `concepts/education-is-atmosphere-discipline-life.md` — the lesson *is* the day's life, not a rehearsal for it.
- `concepts/knowledge-as-food.md` — the lesson nourishes; no twaddle in the language of the plan itself.
- `concepts/knowledge-of-god-man-universe.md` — Mason's canonical observation practices (nature study / field study, picture study, music appreciation, handicraft observation). Use whichever fit the subject.
- `concepts/too-wide-a-mesh.md` — narration replaces quizzing. Do not write comprehension questions with right answers.

The framework is *applied every time*. What varies is which relations open and which canonical activity pattern fits the subject.

### Activity spine by subject shape

- **Reading-shaped** (history, literature, geography, Bible, sometimes science): single reading of a living book → child narrates → optional short follow-up activity. Single-reading and living-books rules are non-negotiable here.
- **Observation-shaped** (nature study, picture study, music appreciation, handicraft): silent sustained attention to one object/piece/artist/craft → child narrates what was seen/heard/done. No reading required.
- **Practice-shaped** (math, phonics, handwriting, a foreign language drill): short, focused engagement with the skill → child narrates the *method* (what they did and how), which is Mason-consistent: knowing the method is itself a form of knowledge.
- **Hybrid** (a science lesson with a short reading *and* an outdoor observation; a Spanish lesson with a short dialogue *and* pronunciation practice): compose the phases; apply each rule only where it applies.

Reading is not required. Creativity and the subject dictate the shape. Narration always closes.

## What the plan produces

Every run produces:

1. A markdown lesson file at `curricula/<class-slug>/<unit-slug>/<lesson-file>.md` (path scheme below).
2. A **hero illustration** — always, every run — embedded at the top of the markdown so it renders inline on GitHub and in Obsidian.
3. Any other materials the lesson's activities **literally use during the session**. Not speculative follow-ups. Not "wouldn't it be nice if." If the lesson sequence says "look at this map," the map is generated; if it says "copy this short verse into the notebook," a copywork sheet is generated; if it says nothing of the kind, nothing else is generated. Materials can be images, maps, cards, or printables.
4. Every generated material is **linked (and, for images, embedded) from the lesson plan**. This is a hard requirement.

The skill must never generate a worksheet for the sake of generating a worksheet. Printing is a cost (paper, time, attention); if the child can copy from a book they already have, no copywork sheet is needed.

## Paths and naming

The layout is three-deep: **class → unit → lesson**. A class groups all work at a given level and subject (e.g. `3rd-grade-science`). A unit is a theme within the class (e.g. `organism-relationships`, `the-water-cycle`) and may contain one or many lessons. A lesson is a single session. `images/` and `materials/` live at the unit level and are shared across every lesson in that unit.

```
curricula/
  <class-slug>/
    <unit-slug>/
      [lesson-NN-]<lesson-slug>.md
      images/
        <lesson-slug>-hero.png
      materials/
        <lesson-slug>-<kind>.<ext>
```

Concrete example (unit with two lessons):

```
curricula/3rd-grade-science/organism-relationships/
  symbiosis.md
  competition.md
  images/
    symbiosis-hero.png
    competition-hero.png
  materials/
    symbiosis-notebook-page.pdf
```

Slug rules:

- All slugs are lowercase kebab-case. No dates. No student names. No ordinals unless the ordinals rule below applies.
- `<class-slug>`: `<grade>-grade-<subject>` when grade is known (e.g. `3rd-grade-science`, `preschool-handwriting`); drop the grade prefix if only a subject was given.
- `<unit-slug>`: the thematic grouping (see "Unit and lesson inference" below).
- `<lesson-slug>`: the specific thing this session teaches, taken from the prompt.
- Image file: `<lesson-slug>-hero.png` in the unit's `images/` dir.
- Other materials: `<lesson-slug>-<kind>.<ext>` in the unit's `materials/` dir (`-map.svg`, `-copywork.pdf`, `-notebook-page.pdf`, `-picture-study.pdf`, etc.).

### Unit and lesson inference

**The prompt is authoritative about the lesson.** Whatever topic the user named — "a lesson about symbiosis," "today's lesson is the water cycle," "introducing the letter B" — *is* the lesson. Do not rename it to a sub-angle you picked during design. (Design influences image content, phase choices, and materials — not the lesson's identity.)

Resolve in this order:

1. **Both unit and lesson named explicitly** — e.g. "in our organism-relationships unit, today's lesson is symbiosis" → unit=`organism-relationships`, lesson=`symbiosis`.
2. **Only the lesson is named** (the common case — e.g. "a 3rd-grade science lesson about symbiosis"):
   - Under `--auto`: **infer a reasonable parent unit** — one level of abstraction above the lesson topic, named as the user would plausibly name it. For `symbiosis` → `organism-relationships`. For `water-cycle` → `earth-systems` (not `science`, which is already the class). For `the-letter-b` → `beginning-phonics`. Keep the inferred unit narrow enough that sibling lessons actually belong in it — not so broad it becomes a catch-all. State the inferred unit name in one line at the top of the delivery so the user can rename it if they disagree.
   - Without `--auto`: **ask the user for the unit name**, proposing a sensible inference as a default. Stop and wait.
3. **Curriculum-builder invocation** — curriculum-builder passes class, unit, and lesson slugs (and optionally an ordinal) in its prompt. Use them as given.

The inferred or provided unit name never overrides the user's stated lesson topic. If the user says the lesson is about symbiosis, the lesson slug is `symbiosis`, period.

### Ordinals

- **Default: no ordinal** in the filename.
- **Prompt explicitly names one** ("lesson 2 on symbiosis", "session 3", "the second lesson of this unit") → prefix the filename with `lesson-NN-`, zero-padded to two digits (e.g. `lesson-02-symbiosis.md`). The ordinal lives only in the markdown filename — never in the image or material filenames — so renumbering a lesson doesn't touch its assets.
- **Unit-builder and curriculum-builder** may pass an ordinal in their prompt; respect it.
- The skill never assigns an ordinal on its own.

### Cross-lesson asset reuse

Because `images/` and `materials/` are shared at the unit level, a later lesson in the same unit may embed or link a non-hero asset generated by an earlier lesson — just reference it by path. A shared map, flashcard set, or timeline keeps the unit coherent without regenerating the same artifact twice.

**Hero images are never reused.** Every lesson has its own unique hero, every unit has its own unique hero, every curriculum has its own unique hero. Hero images are identifiers as much as illustrations — they are the visual landmark a teacher uses to distinguish this lesson from the one before and the one after. Reuse defeats that purpose.

Create directories as needed. `--save PATH` overrides the lesson file path; if `--save` names a directory, the file lands there using the same base filename.

### Spine book passed from unit-builder

When unit-builder (or curriculum-builder through it) invokes this skill, the prose prompt includes the unit's **spine book** — title, author, Open Library URL, and the chapter/section for this specific lesson. The spine is the **main reading material** of the session when the session reads. Treat it as the meat of the lesson, not a suggestion to be casually replaced with something else the lesson-plan thinks fits better.

A lesson may add a **supplementary reading** alongside the spine — a poem, a one-page article, a short picture book, even a chapter from a different book — when the session genuinely calls for one. Query Open Library for the supplement the same way you would in a standalone run. The rule is: core reading = spine; supplements = whatever fits.

If the spine genuinely cannot carry this specific session (e.g. a picture-study session inside a chapter-book unit), source the primary material elsewhere and note why in one sentence under "Materials in hand." This should be rare — it signals a mismatch between unit and session that the teacher will want to see.

## Google Open Library (books)

When the lesson involves reading or suggests enrichment books, use the project's Open Library helper to find real titles — never invent a book or author:

```bash
.venv/bin/python scripts/openlibrary/subject_search.py "<narrow topic>" --limit 15
```

Run from the project root.

Start narrow; broaden once if needed. The script returns a `type` field (`picture_book`, `chapter_book`, `middle_grade`, `young_adult`, `adult`) — use it to pick an age-appropriate title for the student. Do not add Lexile numbers. If nothing useful comes back, say so in the plan — do not fabricate.

**URLs come from the script, never from memory.** The script's output includes an `isbn`, a `work_key` (e.g. `/works/OL446444W`), and a pre-built `url`. When linking a book in the plan, prefer `https://openlibrary.org/isbn/<isbn>` over the `url` field: Open Library's work-page cover edition is sometimes a non-English translation (Spanish, French, etc.), and an ISBN URL routes to the specific English edition. If the result has no ISBN, fall back to the script's `url` (the work page). **Never** construct an Open Library URL from a work ID you remember, infer, or generate — this is how bad links get shipped. If the script didn't return the book, the book isn't linked.

For a living-book passage used *inside the lesson itself*, the book's real text has to land on the page. If you have the passage, quote it with page/chapter citation. If you don't, identify the book and section precisely and tell the user to open to it — do not invent the passage.

## Workflow

### Step 1 — Parse and resolve

Extract subject, theme, student, length, flags. Resolve the student against `students.yaml`. Infer subject/theme slugs. Compute a length default from the grade if `--length` is absent.

### Step 2 — Read the pedagogy pages that apply

**This step is not optional and is not satisfied by "I've read these before" or by a sibling lesson that already applied them.** Read the files with the Read tool, this run, before designing the lesson. The wiki's vocabulary is load-bearing (see "Pedagogical framing" above) and the pages are short — skipping them is how paraphrase drift and quizzing-disguised-as-narration creep into plans.

Always: `act-of-knowing`, `narration`, `science-of-relations`, `children-are-born-persons`, `education-is-atmosphere-discipline-life`, `knowledge-as-food`.

If reading is involved: add `single-reading`, `living-books`.
If observation-shaped: add `knowledge-of-god-man-universe`.

If a sibling lesson in the same unit already exists (e.g. previous lessons in `<unit-slug>/`), read one as a reference for register and shape — *after* reading the pedagogy pages, not instead of them.

### Step 3 — Design the lesson

Decide the activity spine (reading-shaped / observation-shaped / practice-shaped / hybrid). Sketch the phases in order with rough timings that sum to the chosen length, including a narration close. Name the relations this lesson opens concretely (which of persons, nature, art, country, past, present, mathematics, language, God, and how).

Identify what the session literally uses in hand:

- A hero image (always).
- A map? A picture to study? A printable? A short passage that must be supplied by this plan?

Only materials that answer "yes, the child interacts with this *during* the session" are generated.

### Step 4 — Generate the hero image (always)

Invoke the **materials-builder** skill to produce the hero image. Pass it a prompt of the form:

> Illustration for a homeschool lesson plan on `<lesson>`. Landscape 4:3. `<one sentence on subject matter>`. No text, no labels. Save to `curricula/<class-slug>/<unit-slug>/images/<lesson-slug>-hero.png`.

Let materials-builder decide the image register (via `mason-aesthetics`) and the provider. Do not second-guess those choices here. Record the returned provider name — it goes in the delivery message.

**Aspect ratio note.** Gemini/Imagen only supports `1:1`, `9:16`, `16:9`, `4:3`, `3:4`. Use `4:3` as the default landscape for hero images. Use `3:4` only when the subject clearly needs portrait. Do not request `3:2` — the API will reject it.

### Step 5 — Generate other materials (only if the lesson uses them)

For each material the lesson's phases literally use, invoke materials-builder with a concrete prompt describing what the child will use in hand. Save paths follow the scheme above. Collect the resulting file paths.

If the lesson uses no additional materials, skip this step entirely.

### Step 6 — Source books and enrichment (only when relevant)

If the lesson reads from a living book, identify it via Open Library (above) or a source the user named. Record title, author, and the exact passage/chapter used in the session.

If there is room for a short "Go further" list, run the Open Library helper once or twice and an optional WebSearch or two for a poem, an artwork, or a short video — same rules as field-trip-planner's enrichment pass (verified URLs only, omit categories that turn up nothing, never fabricate). This section is optional; a lesson plan is not required to carry an enrichment appendix.

### Step 7 — Write the lesson file

Write `curricula/<class-slug>/<unit-slug>/[lesson-NN-]<lesson-slug>.md` in the shape below. Embed the hero image at the top with a markdown image so it renders on GitHub and in Obsidian. Embed any other generated images inline where they are used; link (not embed) any PDFs or SVGs with the file path.

```markdown
---
class: "<Class as a human-readable phrase, e.g. '3rd-Grade Science'>"
class_slug: <class-slug>
unit: "<Unit, human-readable, e.g. 'Organism Relationships'>"
unit_slug: <unit-slug>
lesson: "<Lesson, human-readable, e.g. 'Symbiosis'>"
lesson_slug: <lesson-slug>
ordinal: <integer or null>        # only set when the prompt names one
parent_unit: unit.md               # null if this lesson is standalone (no unit.md exists)
parent_curriculum: ../curriculum.md       # null if no curriculum.md exists at the class level
prev_lesson: lesson-NN-<slug>.md   # null for the first lesson or when there is no ordering
next_lesson: lesson-NN-<slug>.md   # null for the last lesson or when there is no ordering
student: "<display_name or 'unassigned'>"
grade: <grade or 'unassigned'>
length: "<short|standard|long> (~<range> min)"
concepts: [<wiki concept slugs touched, e.g. narration, science-of-relations, living-books>]
relations_opened: [<from: persons, nature, art, country, past, present, mathematics, language, God>]
activity_shape: <reading|observation|practice|hybrid>
spine_book:                        # only when the lesson uses a unit-level spine book (passed in by unit-builder, or found in unit.md)
  title: "..."
  author: "..."
  url: "https://openlibrary.org/isbn/<isbn>"
  section: "<chapter / page range used this session>"
---

![<alt text describing the hero image>](images/<lesson-slug>-hero.png)

# <Class>: <Lesson>

**Part of:** [<Unit Name>](unit.md)<!-- append "· [<Curriculum Name>](../curriculum.md)" when parent_curriculum is not null; omit the entire line when there is no parent unit -->

**For:** <display_name, grade> · **Length:** ~<range> min

## Relations this lesson opens

<2–3 sentences naming concretely which of the relations in [science-of-relations](../../../pedagogy/wiki/concepts/science-of-relations.md) this lesson opens and how. The pedagogical rationale of the plan. Not decoration.>

## Materials in hand

<Bulleted list of every physical/visual thing the child or teacher uses during the session. Every generated material appears here with a link; every non-generated item (e.g. the book itself, a pencil, a nature notebook the child already owns) is listed as "bring: X". If there are no additional materials beyond the hero image, write "None beyond the lesson page.">

- Main illustration (above).
- <e.g. `[Map of Mesoamerica](materials/maya-use-of-jade-map.svg)` — generated>
- <e.g. bring: *Heidi*, Johanna Spyri, Ch. 3, pp. 41–43 — not generated>

## Lesson sequence

| Phase | What happens | ~Time |
|---|---|---|
| Welcome & orientation | <concrete opener — a question, a poem, a moment of attention> | <min> |
| <phase 2 name> | <what happens> | <min> |
| <phase 3 — core activity> | <what happens; if reading, "read aloud once from <book>, <pages>"; if observation, "<x> minutes silent attention to <subject>"; if practice, "<specific practice>"> | <min> |
| Narration | <invitation to the child to tell back, in their own words, without interruption. Phrase as an invitation, not a question with a right answer.> | <min> |

## The passage (if any)

<If the lesson reads a passage, quote it here with author + chapter/page citation and a link to the book's Open Library entry. The passage must be the real text. If you do not have the passage text at hand, omit this block and, in "Materials in hand", tell the teacher which book and page to open — do not paraphrase or invent.>

> "<real passage text>"
> — <Author>, *<Title>*, <ch./pp.> · [Source](<url>)

## Narration prompt

<One or two sentences offered as an invitation. Examples:
- "Tell me what you remember about Heidi's morning on the mountain."
- "Tell me what you noticed about the tree today — anything at all."
- "Tell me how you solved the last one."
Never "What are the three things that…?">

## Feeding forward

<1–2 threads this lesson opens. Seeds for future lessons or candidate field-trip hooks. Kept terse — unit-builder and curriculum-builder pick these up.>

- <thread 1>
- <thread 2>

## Go further (optional)

<Omit this whole section if nothing real surfaced. Otherwise, only items with verified sources:>

- **Read-aloud:** <title, author, one sentence on why it opens the relation, type label from Open Library>
- **Independent reading:** <title, author, type label>
- **Poem / short reading:** <title, source, URL>
- **Artwork (picture-study candidate):** <artist, work title, URL to reproduction>
- **Video (parent to preview):** <title, source, URL>

## Notes on method

<One short paragraph (2–4 sentences) reminding the teacher of the method-specific rules that apply: single reading (if reading), silent sustained attention (if observation), narration without interruption (always). Phrased as reminders to a capable adult, not as instructions to a novice. Reference the wiki pages inline as real markdown links, e.g. [narration](../../../pedagogy/wiki/concepts/narration.md), [single-reading](../../../pedagogy/wiki/concepts/single-reading.md).>

---

<!-- Navigation footer — include when ordinaled and when prev/next exist. Omit the whole footer for a truly standalone lesson. -->
[← <Previous lesson name>](lesson-NN-<slug>.md) · [↑ Unit: <Unit Name>](unit.md) · [<Next lesson name> →](lesson-NN-<slug>.md)
```

### Step 8 — Deliver

Print a short summary to the console:

- Path of the lesson file.
- Paths of all generated materials, with the provider that produced any images (as materials-builder reports it).
- A single one-line note if anything about the request sits in real tension with the pedagogy — offered as an alternative, never as a correction, never more than once.

## Rules (hard)

- **Unique hero image every time.** Generated by materials-builder, embedded at the top of the markdown. Never reused across lessons, units, or curricula — hero images are visual identifiers as much as illustrations.
- **Other materials only when the session literally uses them.** No speculative worksheets. Printing is a cost.
- **Everything generated is linked or embedded in the plan.** Images embed inline; PDFs/SVGs link by path.
- **Everything the plan references carries a real link.** Every book has an Open Library URL (ISBN form when available; work URL otherwise). Every artwork has a source URL. Every venue (on a feeding-forward trip hook) has a Google Maps URL. No bare names.
- **No Wikipedia.** Wikipedia is not a citation source in this project. Books go to Open Library; short reference articles go to sources the user names (e.g. Grokipedia) or are left out. If a fact needs a citation and no verifiable source surfaces, omit the fact.
- **"Hero image" is an internal term.** It never appears in the lesson prose. In the plan, refer to it as "the main illustration" or "the illustration above" — the filename (`<lesson-slug>-hero.png`) keeps the internal designation.
- **Pedagogy references are real markdown links, never Obsidian wiki-links.** Use `[narration](../../../pedagogy/wiki/concepts/narration.md)` from a lesson file, not `[[concepts/narration]]`. Wiki-link syntax does not resolve on GitHub. The three-deep `../../../` comes from the `curricula/<class>/<unit>/<lesson>.md` layout.
- **Navigation links up and across.** When `unit.md` exists, the lesson body starts with a "Part of: [<Unit>](unit.md)" line (append "· [<Curriculum>](../curriculum.md)" when that also exists). When the lesson has an ordinal and siblings, a prev/next navigation footer appears at the bottom. A lesson opened in Obsidian must offer a link back to its unit and to the lessons on either side.
- **No dates anywhere in the lesson content.** No dates in filenames, no dates in frontmatter, no dates in prose. Lessons are date-portable by design — the same lesson should be reusable next year without edits.
- **Pedagogy framework applies every time.** Relations are named. Narration closes the lesson, every lesson.
- **Single-reading and living-books apply only when reading is in the lesson.** Not every lesson reads.
- **Subject is inferred from prompt + grade, not from `students.yaml` `subjects`.** That list is for time-tracking third-party curricula.
- **Student data otherwise comes from `students.yaml`.** Never hard-code names, aliases, grades.
- **No fabricated sources.** Book titles, authors, passages, quotes, URLs are real or absent. Open Library for books; WebSearch for other enrichment (never Wikipedia).
- **Spine book from unit-builder is the core reading.** When unit-builder passes a spine book in the prose, it is the main reading material of the session, not a suggestion to be casually replaced. Supplementary readings are allowed alongside the spine when the session calls for them (including chapters from other books sourced via Open Library); replacing the spine with something else is allowed only when the spine genuinely cannot carry the session, and requires a one-sentence note in "Materials in hand".
- **No comprehension questions with right answers.** Narration replaces quizzing.
- **No twaddle in the plan's own prose.** The plan addresses a capable adult teaching a person.
- **Never auto-invoke field-trip-planner.** Trips are their own skill; note field-trip threads under "Feeding forward" at most. When invoked by unit-builder or curriculum-builder, trips are generated by those orchestrators, not from inside a lesson run.
