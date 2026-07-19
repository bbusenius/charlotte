---
name: mindfeast-slide-builder
description: Use for any request to make a slide, tablet slide, lock-screen slide, unlock question, or MindFeast slide package. Generates MindFeast question, essay, or informational slides and supports MindFeast's special gratitude package type; resolves the output directory per student from students.yaml (`tablet_slides_dir`); creates `<dir>/<id>/` folders containing slide.md plus optional image/audio media; validates the MindFeast package contract; uses provided prompt images when available; and can generate images in the configured aesthetic register when none are provided. Do not route slide requests through mason-materials-builder or mason-print-design unless the user separately asks for a printable/PDF material.
argument-hint: <slide request in prose, optionally referencing a student, lesson, provided image, or media> [--out PATH] [--id SLUG] [--image quality|fast|provided] [--difficulty easy|medium|hard] [--type question|essay|gratitude|informational] [--subject SUBJECT]
---

# MindFeast Slide Builder

Create one or more MindFeast question, essay, or informational slides, with support for MindFeast's special gratitude package type. A slide is not a printable material; it is an app package synced from a configured slide directory. Output directory is resolved per student from `students.yaml`; see *Output resolution* below.

Use this skill when the user asks for a slide, tablet slide, lock-screen slide, screen-lock challenge, unlock question, essay prompt, informational unlock slide, or MindFeast slide. A bare request such as "make Alice a slide about toads" means this skill.

## Output resolution

Each student in `students.yaml` declares a `tablet_slides_dir` (e.g. `tablet-slides/eliana/active`). The skill writes one slide folder per slide into that directory.

Resolution order, highest priority first:

1. `--out PATH` — explicit override on the skill invocation. Used as-is.
2. **Student's `tablet_slides_dir`** — when the prompt names a student (by `display_name`, slug, or `aliases`) and that student has a `tablet_slides_dir` set. Match the same way `mason-lesson-plan-builder` does: read `students.yaml`, lowercase-match the prompt against each student's slug and `aliases`.
3. **Fallback** — repo-relative `tablet-slides/`. Used when no student is named and no `--out` is given. This is for ad-hoc one-offs not tied to a kid.

If a student is named but has no `tablet_slides_dir` set, fall back to `tablet-slides/` and note this in delivery so the user can decide whether to add the field.

Never hard-code student names, aliases, or paths — read them from `students.yaml` at runtime.

## Contract

Each slide lives in its own directory under the resolved output path:

```text
<resolved-out>/<slide-id>/
  slide.md
  image.png | image.jpg | audio.mp3
```

The folder name must exactly match the frontmatter `id`. The app imports only files directly inside each slide folder. Question, essay, and gratitude slides must declare at least one of `image` or `audio`; informational slides must include at least one of body text, `image`, or `audio`. Every declared media file must exist in that folder.

Question `slide.md` format:

```markdown
---
id: young-girl-reading
type: question
subject: painting
image: young-girl-reading.jpg
answer: Jean Honore Fragonard
accept:
  - Fragonard
choices:
  - Elisabeth Vigee Le Brun
  - Jean Honore Fragonard
  - Mary Cassatt
  - Johannes Vermeer
difficulty: medium
orientation: portrait
---

Who painted "A Young Girl Reading"?

This Rococo portrait is also known as "The Reader."
```

Audio-only example:

```markdown
---
id: moonlight-sonata
type: question
subject: composer
audio: moonlight-sonata.mp3
answer: Ludwig van Beethoven
accept:
  - Beethoven
  - Ludwig Beethoven
difficulty: easy
orientation: landscape
---

Who composed "Moonlight Sonata"?

Its full title is Piano Sonata No. 14 in C-sharp minor, Op. 27 No. 2.
```

Informational example:

```markdown
---
id: monet-giverny-context
type: informational
subject: painting
image: monet-giverny-context.png
difficulty: easy
orientation: landscape
---

Monet painted many water-lily scenes from the garden he designed at Giverny.
```

Essay example:

```markdown
---
id: painting-observation
type: essay
subject: painting
image: painting-observation.jpg
difficulty: easy
orientation: landscape
---

What do you notice first in this painting? Write two or three sentences.
```

Required fields: `id`, `type`. Use `type: question` for answerable challenge slides, `type: essay` for one-time free-response prompts that accept any non-blank student response, `type: gratitude` for recurring free-response prompts recorded in the gratitude journal, and `type: informational` for dismissible information slides. Use `subject` for category metadata such as `painting`, `composer`, `geography`, or `science`.

Optional fields:

- `subject` — content category metadata. The app currently ignores it, but keep it useful for humans and future tooling.
- `answer` — required for question slides; omit for essay, gratitude, and informational slides.
- `accept` — alternate free-text answers for question slides. Include spelling/plain-ASCII variants when names include accents.
- `choices` — multiple-choice options for question slides. If present, the app shows buttons instead of free text.
- `difficulty` — `easy`, `medium`, or `hard`; default to `easy`.
- `orientation` — `landscape` or `portrait`. Choose deliberately for both the image composition and the bottom-panel UI load; do not rely on the script default.

Markdown body:

- For question slides, the first paragraph is the question shown to the student.
- For question slides, the second paragraph, if present, is the hint shown after an incorrect attempt.
- For essay slides, the first paragraph is the question/prompt shown to the student. There is no answer, choices, accept list, or hint.
- For gratitude slides, the first paragraph is the recurring prompt shown to the student. There is no answer, choices, accept list, or hint.
- For informational slides, the first paragraph is optional display text. There is no answer, choices, or hint.
- Keep visible text short enough for the bottom panel of a tablet lock screen.

## Workflow

1. Parse the prompt for slide type, subject, student, lesson reference, requested slide count, image/audio input, answer style, and difficulty.
2. Read `students.yaml` and resolve the output directory per *Output resolution* above. Bind it to `<out>` for the rest of the workflow. If a student or lesson is referenced, also read the lesson content before writing the challenge.
3. If an image is provided in the prompt, use that image as the slide media. Copy it into the slide folder with a slugged filename and preserve the extension when practical.
4. If no image is provided and the slide is not audio-only, choose `orientation` from the image composition and expected UI load before generating the image, then generate one using the image generation rules below. Prompt for no text, no labels, no captions.
5. If the request is for music/listening, prefer audio when the user provides an audio file. Do not invent or download copyrighted audio.
6. Choose a stable `id` slug from the subject unless `--id` is given. Use lowercase ASCII letters, digits, and hyphens only.
7. Write `slide.md` and media into `<out>/<id>/`. Prefer the skill-local scaffold script for ordinary single-slide packages — pass the resolved `<out>` as `--out`:

```bash
.venv/bin/python skills/mindfeast-slide-builder/scripts/make_slide.py \
  --out <out> \
  --id <slide-id> \
  --type question \
  --subject <subject> \
  --image path/to/image.png \
  --answer "..." \
  --accept "..." \
  --choice "..." \
  --difficulty medium \
  --orientation landscape \
  --question "..." \
  --hint "..."
```

For informational slides:

```bash
.venv/bin/python skills/mindfeast-slide-builder/scripts/make_slide.py \
  --out <out> \
  --id <slide-id> \
  --type informational \
  --subject <subject> \
  --image path/to/image.png \
  --orientation landscape \
  --text "..."
```

For essay slides:

```bash
.venv/bin/python skills/mindfeast-slide-builder/scripts/make_slide.py \
  --out <out> \
  --id <slide-id> \
  --type essay \
  --subject <subject> \
  --image path/to/image.png \
  --difficulty medium \
  --orientation landscape \
  --question "What do you notice first? Write two or three sentences."
```

8. Run the bundled validator before delivery:

```bash
.venv/bin/python skills/mindfeast-slide-builder/scripts/validate_slide.py <out>/<slide-id>
```

For multiple slides, validate each folder.

## Question Slide Design

The lock-screen challenge should make the student retrieve or notice one meaningful thing, not fight the interface.

- Prefer concrete questions with one clear answer.
- Put accepted variants in `accept`.
- Use `choices` when spelling, accents, or young-reader typing would get in the way.
- For multiple-choice slides, put `choices` in their final display order and deliberately vary the correct answer's position across a set. Do not default to putting the correct answer first; when making several slides, spread correct answers among first, middle, and last positions.
- Prefer `orientation: portrait` for multiple-choice slides with four or more choices, or when the choices are long enough that button height matters.
- Use free text when recall matters and the answer is short.
- Avoid trick questions, vague wording, and overly long answers.
- Hints should reopen attention to the material, not give the answer away.
- For image slides, the image should be the main object of attention. Do not bake question text into the image.
- For generated images, follow the configured aesthetics skill (`pedagogy.aesthetics` in `runtime.yaml`, default `skills/mason-aesthetics`): calm, specific, no neon/novelty styling.

Good slide subjects include `painting`, `composer`, `geography`, `science`, `math`, `vocabulary`, `history`, `scripture`, `poetry`, and `phonics`.

## Informational Slide Design

Use `type: informational` when the slide should simply show context, a reminder, a quote, a label-free observation prompt, or a transition between challenge slides. Informational slides are dismissible and do not include `answer`, `accept`, `choices`, or hint text.

- Prefer one concise body paragraph.
- Prefer `orientation: portrait` for informational slides with a quote, several facts, or a paragraph long enough that the bottom panel becomes the main object of attention.
- Let the image or audio carry most of the slide when possible.
- Do not create fake questions with obvious answers just to fit the question format.
- A media-only informational slide is valid when the requested experience is just looking or listening.

## Essay Slide Design

Use `type: essay` when the student should respond in their own words. Essay slides are accepted when the student enters any non-blank response, show a larger multiline response box, display "Submitted" after completion, log the response for the parent, and deactivate after each submission until a parent reactivates them.

- Always include `image` or `audio`.
- Always include a clear prompt as the first body paragraph.
- Do not include `answer`, `accept`, `choices`, or hint text.
- Prefer observation, narration, reflection, and short written-response prompts.
- Keep the prompt specific enough that the student knows what to write, but open enough that many valid responses are possible.
- A good essay prompt usually asks for one to three sentences, one observation plus one inference, or a short narration from memory.

## Gratitude Packages

MindFeast ships with a standard recurring gratitude starter slide. The `gratitude` type documents that special application feature and permits compatible variations. It uses the same package requirements and free-form submission behavior as `essay`, but remains active after submission and records responses in the MindFeast gratitude journal.

## Image Generation

Use the same image route policy as `mason-materials-builder`, but with slide-specific aspect ratios and output paths.

Image generation for this skill is route-based. Use the normal `quality` route unless the user explicitly asks for a fast/cheap slide image; `image-generation.yaml` decides which provider/model supplies that route.

- Use the repo-local router below, invoked from the project root through `.venv/bin/python`.
- If the router exits `2`, no configured script-callable image provider is available. At that point, use a runtime-native image tool if the active harness exposes one. If no runtime image tool exists, report that image generation is unavailable.
- If the router exits `3`, stop. That is a policy/safety rejection; do not try another provider.

### Provided image

If the user attaches or names an image, use it. Do not generate a replacement unless the user asks for one. Copy it into the slide folder and set `image:` to the copied filename.

### Default route: quality

When no image is provided and an image slide is needed, first choose the slide orientation, then use the shared image router from the repo root. Use landscape when the visual composition needs width: broad scenes, maps, diagrams, groups, or side-by-side relationships.

```bash
.venv/bin/python scripts/charlotte_image.py \
  --prompt "..." \
  --out "<out>/<slide-id>/<slide-id>.png" \
  --size 1K \
  --aspect-ratio 16:9 \
  --kind slide-background \
  --route quality \
  --json
```

Use `--aspect-ratio 16:9` for `orientation: landscape`. Use `--aspect-ratio 3:4` for `orientation: portrait`.

Use portrait when the visual composition or the slide UI needs vertical room: single people, portraits, book-page-like images, tall objects, composer/author/painter likenesses, artwork/document study, dense informational text, longer essay prompts, or multiple-choice slides with four or more choices.

```bash
.venv/bin/python scripts/charlotte_image.py \
  --prompt "..." \
  --out "<out>/<slide-id>/<slide-id>.png" \
  --size 1K \
  --aspect-ratio 3:4 \
  --kind slide-background \
  --route quality \
  --json
```

The router reads `image-generation.yaml`. Use the JSON `path` in the result as the actual media file path; some providers return `.jpg` even when the requested path ended in `.png`. Use the JSON `route`, `source`, `model`, and `prompt_mode` fields when naming what generated the image.

Use `--dry-run --json` on the same command to inspect the resolved route and final provider prompt without calling an image provider or writing files.

Exit codes:

- `0` success. Use the JSON output to name the source/model in delivery.
- `1` configured providers were called but failed. Report the failure; do not hide it.
- `2` no script-callable provider is configured or available. Use a runtime-native image tool if available.
- `3` policy/safety rejection. Stop.

### Fast route

If the user explicitly asks for a fast/cheap/simple generated image, use `--route fast`:

```bash
.venv/bin/python scripts/charlotte_image.py \
  --prompt "..." \
  --out "<out>/<slide-id>/<slide-id>.png" \
  --size 1K \
  --aspect-ratio 16:9 \
  --kind slide-background \
  --route fast \
  --json
```

The route named `fast` receives the configured aesthetics skill's compact image summary when the file provides one (the optional `#### Image-router summary` section), and the full skill text otherwise. Other routes always receive the full aesthetics skill text as image prompt context unless `--prompt-mode` is explicitly overridden. The aesthetics skill is set by `pedagogy.aesthetics` in `runtime.yaml` (default `skills/mason-aesthetics`).

### Prompt rules

- State the visual register explicitly: botanical plate, watercolor in a living-book register, period map, quiet textbook diagram, art reproduction style, etc.
- Always include `no text, no labels, no captions`.
- **Full-bleed for the Android lock screen.** The illustration must extend to all four edges with no borders, paper margin, vignette, frame, or blank rectangle. Affirm this in the prompt (e.g. *"the painted scene extends to every edge of the canvas"*) and include explicit negatives: *"no border, no paper margin, no vignette, no frame, no blank space at the edges."*
- **Compose for the panel overlay, don't reserve space for it.** The app's translucent question panel overlays the lower portion of the image. Anchor the focal subject in the upper or center portion of the frame so the panel falls over painted-but-less-essential content (foreground, ground plane, table surface, grass) — keep that region painted, just not where the focal subject lives. **Do not** ask for "empty space," "room for text," or "a text panel" at the bottom — image models interpret that literally and paint a blank rectangle into the image.
- Use enough contrast that the subject still reads once the panel overlays the bottom.
- Prefer calm, specific, non-novelty imagery aligned with the configured aesthetics skill.
- Name the image source/model in delivery, or say that the user provided the image.

## Media Rules

Images:

- Prefer `.jpg` for photos/art reproductions and provider-returned JPEGs; prefer `.png` for generated diagrams when the provider actually returns PNG.
- Use `orientation: portrait` when the image composition or bottom-panel UI needs vertical room: single people, portraits, book-page-like images, tall objects, composer/author/painter likenesses, artwork/document study, dense informational text, longer essay prompts, or multiple-choice slides with four or more choices. Use `landscape` when the visual composition needs width: broad scenes, maps, diagrams, groups, or side-by-side relationships.
- The app crops landscape images full-screen and fills height for portrait images, so the important subject should be centered.

Audio:

- Use `.mp3` when possible.
- An audio-only slide is valid, but still include `orientation: landscape`.
- If both image and audio are present, the image remains the visual background and the audio player appears in the question panel.

## Validation Rules

The Android parser effectively enforces:

- YAML frontmatter begins and ends with `---`.
- `id` and `type` are present.
- `type` is `question`, `essay`, `gratitude`, or `informational`. Put category metadata in `subject`, not `type`.
- Question slides include `answer` and at least one of `image` or `audio`.
- Essay slides include a body prompt and at least one of `image` or `audio`; they do not use answer fields.
- Gratitude slides include a body prompt and at least one of `image` or `audio`; they do not use answer fields.
- Informational slides include at least one of body text, `image`, or `audio`.
- Declared `image`/`audio` files exist in the same folder.
- `orientation` is exactly `landscape` or `portrait` if present.
- The folder name equals `id`.
- Slide folder names cannot contain `/`, `\`, or start with `.`.

The bundled validator mirrors those checks and adds practical warnings for long text, duplicate choices, missing answer variants, ignored answer fields, and legacy category values in `type`.

## Relationship To Other Skills

This skill owns the app-specific slide package. Use `mason-materials-builder` only as a source of pedagogy, curriculum grounding, and image-generation procedure. Do not route this through `mason-print-design` unless the user separately asks for a printable/PDF version of the same material.

## Delivery

Report the slide id, full path, type, subject if present, media filename, visible text/question, answer when present, whether choices were used, and validation result. For essay slides, note that the response is free-form and parent-visible in Stats after submission. For gratitude slides, note that the response is free-form, recorded in the gratitude journal, and the slide remains active. Name the resolved student (or "no student / fallback") and which resolution rule applied (`--out`, student's `tablet_slides_dir`, or fallback). If an image was generated, name the image source/model.
