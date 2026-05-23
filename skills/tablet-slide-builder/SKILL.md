---
name: tablet-slide-builder
description: Generate Android lock-screen question, essay, or informational slides for the Homeschool Screen Lock app. Resolves the output directory per-student from students.yaml (`tablet_slides_dir`), creates `<dir>/<id>/` folders containing slide.md plus optional image/audio media, validates the app-specific YAML/frontmatter contract, uses provided prompt images when available, and can generate Mason-shaped images when none are provided.
argument-hint: <slide request in prose, optionally referencing a student, lesson, provided image, or media> [--out PATH] [--id SLUG] [--image gemini|grok|provided] [--difficulty easy|medium|hard] [--type question|essay|informational] [--subject SUBJECT]
---

# Tablet Slide Builder

Create one or more Android lock-screen question, essay, or informational slides for the Homeschool Screen Lock app. A slide is not a printable material; it is an app package synced from a Samba share. Output directory is resolved per-student from `students.yaml`; see *Output resolution* below.

Use this skill when the user asks for tablet lock-screen slides, screen-lock challenges, unlock questions, essay prompts, informational unlock slides, or slides for the Homeschool Screen Lock app.

## Output resolution

Each student in `students.yaml` declares a `tablet_slides_dir` (e.g. `tablet-slides/eliana/active`). The skill writes one slide folder per slide into that directory.

Resolution order, highest priority first:

1. `--out PATH` — explicit override on the skill invocation. Used as-is.
2. **Student's `tablet_slides_dir`** — when the prompt names a student (by `display_name`, slug, or `aliases`) and that student has a `tablet_slides_dir` set. Match the same way `lesson-plan-builder` does: read `students.yaml`, lowercase-match the prompt against each student's slug and `aliases`.
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

The folder name must exactly match the frontmatter `id`. The app imports only files directly inside each slide folder. Question and essay slides must declare at least one of `image` or `audio`; informational slides must include at least one of body text, `image`, or `audio`. Every declared media file must exist in that folder.

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

Required fields: `id`, `type`. Use `type: question` for answerable challenge slides, `type: essay` for free-response prompts that accept any non-blank student response, and `type: informational` for dismissible information slides. Use `subject` for category metadata such as `painting`, `composer`, `geography`, or `science`.

Optional fields:

- `subject` — content category metadata. The app currently ignores it, but keep it useful for humans and future tooling.
- `answer` — required for question slides; omit for essay and informational slides.
- `accept` — alternate free-text answers for question slides. Include spelling/plain-ASCII variants when names include accents.
- `choices` — multiple-choice options for question slides. If present, the app shows buttons instead of free text.
- `difficulty` — `easy`, `medium`, or `hard`; default to `easy`.
- `orientation` — `landscape` or `portrait`; default to `landscape`.

Markdown body:

- For question slides, the first paragraph is the question shown to the student.
- For question slides, the second paragraph, if present, is the hint shown after an incorrect attempt.
- For essay slides, the first paragraph is the question/prompt shown to the student. There is no answer, choices, accept list, or hint.
- For informational slides, the first paragraph is optional display text. There is no answer, choices, or hint.
- Keep visible text short enough for the bottom panel of a tablet lock screen.

## Workflow

1. Parse the prompt for slide type, subject, student, lesson reference, requested slide count, image/audio input, answer style, and difficulty.
2. Read `students.yaml` and resolve the output directory per *Output resolution* above. Bind it to `<out>` for the rest of the workflow. If a student or lesson is referenced, also read the lesson content before writing the challenge.
3. If an image is provided in the prompt, use that image as the slide media. Copy it into the slide folder with a slugged filename and preserve the extension when practical.
4. If no image is provided and the slide is not audio-only, generate one using the image generation rules below. Prompt for no text, no labels, no captions.
5. If the request is for music/listening, prefer audio when the user provides an audio file. Do not invent or download copyrighted audio.
6. Choose a stable `id` slug from the subject unless `--id` is given. Use lowercase ASCII letters, digits, and hyphens only.
7. Write `slide.md` and media into `<out>/<id>/`. Prefer the bundled scaffold script for ordinary single-slide packages — pass the resolved `<out>` as `--out`:

```bash
python scripts/tablet-slides/make_slide.py \
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
python scripts/tablet-slides/make_slide.py \
  --out <out> \
  --id <slide-id> \
  --type informational \
  --subject <subject> \
  --image path/to/image.png \
  --text "..."
```

For essay slides:

```bash
python scripts/tablet-slides/make_slide.py \
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
python scripts/tablet-slides/validate_slide.py <out>/<slide-id>
```

For multiple slides, validate each folder.

## Question Slide Design

The lock-screen challenge should make the student retrieve or notice one meaningful thing, not fight the interface.

- Prefer concrete questions with one clear answer.
- Put accepted variants in `accept`.
- Use `choices` when spelling, accents, or young-reader typing would get in the way.
- For multiple-choice slides, put `choices` in their final display order and deliberately vary the correct answer's position across a set. Do not default to putting the correct answer first; when making several slides, spread correct answers among first, middle, and last positions.
- Use free text when recall matters and the answer is short.
- Avoid trick questions, vague wording, and overly long answers.
- Hints should reopen attention to the material, not give the answer away.
- For image slides, the image should be the main object of attention. Do not bake question text into the image.
- For generated images, follow `mason-aesthetics`: calm, specific, living-book register, no neon/novelty styling.

Good slide subjects include `painting`, `composer`, `geography`, `science`, `math`, `vocabulary`, `history`, `scripture`, `poetry`, and `phonics`.

## Informational Slide Design

Use `type: informational` when the slide should simply show context, a reminder, a quote, a label-free observation prompt, or a transition between challenge slides. Informational slides are dismissible and do not include `answer`, `accept`, `choices`, or hint text.

- Prefer one concise body paragraph.
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

## Image Generation

Use the same provider policy as `materials-builder`, but with slide-specific aspect ratios and output paths.

### Provided image

If the user attaches or names an image, use it. Do not generate a replacement unless the user asks for one. Copy it into the slide folder and set `image:` to the copied filename.

### Default: Gemini

When no image is provided and an image slide is needed, use the shared Gemini helper from the repo root:

```bash
.venv/bin/python scripts/gemini_image.py \
  --prompt "..." \
  --out "<out>/<slide-id>/<slide-id>.png" \
  --size 1K \
  --aspect-ratio 16:9
```

Use `--aspect-ratio 16:9` for `orientation: landscape`. Use `--aspect-ratio 3:4` for `orientation: portrait`.

The helper reads `GEMINI_API_KEY` from the environment. Exit code `2` means the key is missing or the SDK is unavailable. Exit code `1` means the API call failed.

### Fallback to Grok on missing Gemini key

If Gemini is the default provider and the helper exits `2` because `GEMINI_API_KEY` is missing, fall back to Grok automatically rather than blocking. Note the fallback in delivery.

Do not fall back on helper exit code `1`; that is an API-level failure such as policy, rate limit, or provider error. If the user explicitly passed `--image gemini`, do not fall back. Stop and ask because they named the provider.

### Grok (`--image grok` or fallback)

Use Grok when the user explicitly passes `--image grok`, or when the Gemini missing-key fallback applies. Generate a slide background image with the same visual prompt, save it into `<out>/<slide-id>/<slide-id>.png`, and then package it with `make_slide.py`.

If the Grok image tool is unavailable in the current environment, say so and stop rather than inventing a media file.

### Prompt rules

- State the visual register explicitly: botanical plate, watercolor in a living-book register, period map, quiet textbook diagram, art reproduction style, etc.
- Always include `no text, no labels, no captions`.
- **Full-bleed for the Android lock screen.** The illustration must extend to all four edges with no borders, paper margin, vignette, frame, or blank rectangle. Affirm this in the prompt (e.g. *"the painted scene extends to every edge of the canvas"*) and include explicit negatives: *"no border, no paper margin, no vignette, no frame, no blank space at the edges."*
- **Compose for the panel overlay, don't reserve space for it.** The app's translucent question panel overlays the lower portion of the image. Anchor the focal subject in the upper or center portion of the frame so the panel falls over painted-but-less-essential content (foreground, ground plane, table surface, grass) — keep that region painted, just not where the focal subject lives. **Do not** ask for "empty space," "room for text," or "a text panel" at the bottom — image models interpret that literally and paint a blank rectangle into the image.
- Use enough contrast that the subject still reads once the panel overlays the bottom.
- Prefer calm, specific, non-novelty imagery aligned with `mason-aesthetics`.
- Name the provider in delivery: Gemini, Grok, or provided image.

## Media Rules

Images:

- Prefer `.jpg` for photos/art reproductions and `.png` for generated illustrations or diagrams.
- Use `orientation: portrait` for tall portraits or book-page-like images; otherwise use `landscape`.
- The app crops landscape images full-screen and fills height for portrait images, so the important subject should be centered.

Audio:

- Use `.mp3` when possible.
- An audio-only slide is valid, but still include `orientation: landscape`.
- If both image and audio are present, the image remains the visual background and the audio player appears in the question panel.

## Validation Rules

The Android parser effectively enforces:

- YAML frontmatter begins and ends with `---`.
- `id` and `type` are present.
- `type` is `question`, `essay`, or `informational`. Put category metadata in `subject`, not `type`.
- Question slides include `answer` and at least one of `image` or `audio`.
- Essay slides include a body prompt and at least one of `image` or `audio`; they do not use answer fields.
- Informational slides include at least one of body text, `image`, or `audio`.
- Declared `image`/`audio` files exist in the same folder.
- `orientation` is exactly `landscape` or `portrait` if present.
- The folder name equals `id`.
- Slide folder names cannot contain `/`, `\`, or start with `.`.

The bundled validator mirrors those checks and adds practical warnings for long text, duplicate choices, missing answer variants, ignored answer fields, and legacy category values in `type`.

## Relationship To Other Skills

This skill owns the app-specific slide package. Use `materials-builder` only as a source of pedagogy, curriculum grounding, and image-generation procedure. Do not route this through `mason-print-design` unless the user separately asks for a printable/PDF version of the same material.

## Delivery

Report the slide id, full path, type, subject if present, media filename, visible text/question, answer when present, whether choices were used, and validation result. For essay slides, note that the response is free-form and parent-visible in Stats after submission. Name the resolved student (or "no student / fallback") and which resolution rule applied (`--out`, student's `tablet_slides_dir`, or fallback). If an image was generated, name the image provider.
