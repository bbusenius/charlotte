---
name: mindfeast-slide-builder
description: Use for any request to make a slide, tablet slide, lock-screen slide, unlock question, or MindFeast slide package. Generates MindFeast question, essay, informational, narration, or conversation slides and supports MindFeast's special gratitude package type; resolves the output directory per student from students.yaml (`tablet_slides_dir`); creates `<dir>/<id>/` folders containing slide.md plus optional image/audio media; validates the MindFeast package contract; uses provided prompt images when available; and can generate images in the configured aesthetic register when none are provided. Do not route slide requests through mason-materials-builder or mason-print-design unless the user separately asks for a printable/PDF material.
argument-hint: <slide request in prose, optionally referencing a student, lesson, provided image, or media> [--out PATH] [--id SLUG] [--image quality|fast|provided] [--difficulty easy|medium|hard] [--type question|essay|gratitude|informational|narration|conversation] [--subject SUBJECT]
---

# MindFeast Slide Builder

Create one or more MindFeast question, essay, informational, narration, or conversation slides, with support for MindFeast's special gratitude package type. A slide is not a printable material; it is an app package synced from a configured slide directory. Output directory is resolved per student from `students.yaml`; see *Output resolution* below.

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
  image.png | image.jpg | audio.mp3  (optional by type)
  script.md | passage.md | context.md  (required by type)
```

The folder name must exactly match the frontmatter `id`. The app imports only files directly inside each slide folder. Question, essay, and gratitude slides must declare at least one of `image` or `audio`; informational slides must include at least one of body text, `image`, or `audio`. Narration slides require exactly one of `audio`, `script`, or `passage`. Conversation slides require `intent`, `turns`, and `context`. A missing image does not fail validation for either type, and conversation audio is optional. Every referenced file must exist directly in that folder.

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

Required fields: `id`, `type`. Use `type: question` for answerable challenge slides, `type: essay` for one-time free-response prompts that accept any non-blank student response, `type: gratitude` for recurring free-response prompts recorded in the gratitude journal, and `type: informational` for dismissible information slides. Use `type: narration` to supply a passage for the student to retell, and `type: conversation` for a short guided exchange with the app's AI. Use `subject` for category metadata such as `painting`, `composer`, `geography`, or `science`.

Optional fields:

- `subject` — content category metadata. The app currently ignores it, but keep it useful for humans and future tooling.
- `answer` — required for question slides; omit for all other types.
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
- For narration slides, the first paragraph is the retelling prompt. For conversation slides, it is the opening question. Both must be non-blank; neither type uses answer fields or a hint.
- Keep visible text short enough for the bottom panel of a tablet lock screen.

## Workflow

1. Parse the prompt for slide type, subject, student, lesson reference, requested slide count, image/audio input, answer style, and difficulty.
2. Read `students.yaml` and resolve the output directory per *Output resolution* above. Bind it to `<out>` for the rest of the workflow. If a student or lesson is referenced, also read the lesson content before writing the challenge.
3. If an image is provided in the prompt, use that image as the slide media. Copy it into the slide folder with a slugged filename and preserve the extension when practical.
4. If no image is provided and the slide is not audio-only, choose `orientation` from the image composition and expected UI load before generating the image, then generate one using the image generation rules below. Do this for narration and conversation slides as well as the other types. Prompt for no text, no labels, no captions.
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

For narration, use `--question` for a short retelling prompt and exactly one source: `--audio`, `--script-text`/`--script-file`, or `--passage-text`/`--passage-file`. The `-text` flags accept literal Markdown; the `-file` flags read an existing UTF-8 file. Each pair is mutually exclusive. The script writes the text to `script.md` or `passage.md`, preserving its content. Audio keeps the provided file's basename.

Script narration, read aloud by the app:

```bash
.venv/bin/python skills/mindfeast-slide-builder/scripts/make_slide.py \
  --out <out> --id seed-script --type narration --orientation portrait \
  --image path/to/image.png \
  --question "Tell back how the seed began to grow." \
  --script-text "The seed absorbed water. A root emerged and grew into the soil."
```

Passage narration, read on screen:

```bash
.venv/bin/python skills/mindfeast-slide-builder/scripts/make_slide.py \
  --out <out> --id seed-passage --type narration --orientation portrait \
  --image path/to/image.png \
  --question "Tell back what you read about the seed." \
  --passage-file path/to/seed-passage.md
```

Audio narration, using a provided, licensed recording. This is the audio-only case, so it has no image:

```bash
.venv/bin/python skills/mindfeast-slide-builder/scripts/make_slide.py \
  --out <out> --id seed-audio --type narration --orientation landscape \
  --question "Tell back what you heard about the seed." \
  --audio path/to/seed-recording.wav
```

For a conversation, supply an opening `--question`, non-blank `--intent`, integer `--turns` of at least 1, and `--context-text` or `--context-file`. Context uses the same text/file convention and is written to `context.md`. Intent and context are hidden from the learner.

```bash
.venv/bin/python skills/mindfeast-slide-builder/scripts/make_slide.py \
  --out <out> --id roots-conversation --type conversation --orientation portrait \
  --image path/to/image.png \
  --question "How do roots help a plant?" \
  --intent "Draw out how roots absorb water and anchor plants. Use gentle, concrete language for an early reader." \
  --turns 3 --context-text "Roots absorb water and minerals from soil and anchor the plant."
```

Script, passage, and conversation slides take the generated or provided file with `--image`. An audio narration slide can stay audio-only. Optional `--audio` also works for conversation. The builder rejects blank prompts or source text, invalid conversation fields, and `--answer`, `--accept`, `--choice`, or `--hint` before writing the package.

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

## Narration and conversation design

Use narration when the student takes in a supplied passage and then retells it. Ask for a retelling in the student's own words. Put the passage in the source file, keeping the visible prompt short. Choose `script` for listening, especially for younger learners or pre-readers, and `passage` for reading on screen. Use `audio` only for a provided, licensed recording. Generate an image for both types, using the image rules below, unless an image is provided or the slide is audio-only. Show the passage's scene, or the concrete subject of the conversation.

Start a conversation with one concrete question. In `intent`, name what the AI should draw out or explain, the learner's level, and the tone. Put accurate factual background in `context.md`, not directions to the AI. Usually choose 2 or 3 turns. A turn is one learner reply plus one AI reply; the opening question does not count. The app asks for short replies and one question at a time, then adds a wrap-up rule on the final turn.

Essay still fits observation, reflection, or a short written response from memory without a supplied passage or guided exchange.

## Gratitude Packages

MindFeast ships with a standard recurring gratitude starter slide. The `gratitude` type documents that special application feature and permits compatible variations. It uses the same package requirements and free-form submission behavior as `essay`, but remains active after submission and records responses in the MindFeast gratitude journal.

## Image Generation

Use the same image route policy as `mason-materials-builder`, but with slide-specific aspect ratios and output paths.

Image generation for this skill is route-based. Use the normal `quality` route unless the user explicitly asks for a fast/cheap slide image; `image-generation.yaml` decides which provider/model supplies that route.

- Prefer the runtime's active file-producing image tool. In Hermes this is `image_generate`, and the profile's `image_gen.provider` picks its backend. Accept either supported backend:
  - `gemini`: Charlotte's plugin. It runs the router, and its result reports `route`, `source`, `model`, and `prompt_mode`. Accept it only when those fields match the requested route.
  - `xai`: Hermes's built-in Grok provider. Its result reports `provider: xai` and `model`, with no route fields.
- When no runtime image tool is active, use the repo-local router below from the project root through `.venv/bin/python`.
- If the repo-local router exits `2`, no configured script-callable image provider is available. Report that image generation is unavailable unless a runtime image tool is active.
- If the router exits `3` or the image tool reports a policy or safety rejection, stop. Do not try another provider.
- Never bypass a failed image tool or route with a direct provider call, a handwritten HTTP request, another image tool, or the other provider. The profile config chooses the provider.

### Style in the prompt

Put the configured aesthetics register in every generated-image prompt, whichever tool makes the image. After the content request and the slide prompt rules below, add the `#### Image-router summary` section of the configured aesthetics skill (`pedagogy.aesthetics` in `runtime.yaml`, default `skills/mason-aesthetics/SKILL.md`). If that file has no such section, add its illustration-style guidance. The xai tool adds no style of its own. The Gemini router also adds the aesthetics profile, and that is expected.

### Runtime image tool

Pass `aspect_ratio: landscape` for `orientation: landscape` and `aspect_ratio: portrait` for `orientation: portrait`. Copy the file named by the result's `image` field into `<out>/<slide-id>/`, keeping its extension, and set `image:` to the copied filename. If `image` is an `https://` URL instead of a local path, xAI file storage is on. Download that URL into the slide folder and say in delivery that xAI keeps a stored copy.

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
- Name the image source/model in delivery, or say that the user provided the image. For the xai tool, name xAI Grok and the result's `model`.

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
- `type` is `question`, `essay`, `gratitude`, `informational`, `narration`, or `conversation`. Put category metadata in `subject`, not `type`.
- Question slides include `answer` and at least one of `image` or `audio`.
- Essay slides include a body prompt and at least one of `image` or `audio`; they do not use answer fields.
- Gratitude slides include a body prompt and at least one of `image` or `audio`; they do not use answer fields.
- Informational slides include at least one of body text, `image`, or `audio`.
- Narration slides include a non-blank prompt and exactly one of `audio`, `script`, or `passage`.
- Conversation slides include a non-blank opening question and `intent`, integer `turns` of at least 1, and `context`.
- Referenced files use basenames and exist in the same folder. `script`, `passage`, and `context` contain non-blank UTF-8 Markdown in `.md` files.
- `orientation` is exactly `landscape` or `portrait` if present.
- The folder name equals `id`.
- Slide folder names cannot contain `/`, `\`, or start with `.`.

The bundled validator mirrors those checks and adds practical warnings for long text, duplicate choices, missing answer variants, ignored answer fields, and legacy category values in `type`.

## Relationship To Other Skills

This skill owns the app-specific slide package. Use `mason-materials-builder` only as a source of pedagogy, curriculum grounding, and image-generation procedure. Do not route this through `mason-print-design` unless the user separately asks for a printable/PDF version of the same material.

## Delivery

Report the slide id, full path, type, subject if present, media filename, visible text/question, answer when present, whether choices were used, and validation result. For essay slides, note that the response is free-form and parent-visible in Stats after submission. For gratitude slides, note that the response is free-form, recorded in the gratitude journal, and the slide remains active. Name the resolved student (or "no student / fallback") and which resolution rule applied (`--out`, student's `tablet_slides_dir`, or fallback). If an image was generated, name the image source/model.
