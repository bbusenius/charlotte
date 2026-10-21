# MindFeast Slide Package Format, Version 1

This document specifies the slide packages that Charlotte creates for MindFeast. It defines the package format without a version field in `slide.md`.

“Version 1” versions this specification. A package conforming to this document does not contain a format-version field, and existing unversioned MindFeast packages are version 1 packages.

## Package layout

Each slide is one directory containing `slide.md` and any files it references. The optional files below cover all six types:

```text
<slide-id>/
  slide.md
  image.jpg
  audio.mp3
  script.txt
  passage.txt
  context.txt
```

The directory name must equal the frontmatter `id`. A slide id uses lowercase ASCII letters, digits, and hyphens, begins with a letter or digit, and does not contain `/` or `\` or begin with `.`. Referenced files live directly in the slide directory and are named by basename, not by a path.

## `slide.md`

`slide.md` is UTF-8 Markdown consisting of YAML frontmatter between `---` delimiters followed by a Markdown body.

```markdown
---
id: france-capital
type: question
subject: geography
image: france-map.png
answer: "Paris"
accept:
  - "paris"
choices:
  - "Lyon"
  - "Paris"
  - "Marseille"
difficulty: easy
orientation: landscape
---

What is the capital of France?

It is also called the City of Light.
```

The first body paragraph is the visible question, prompt, or informational text. For question slides only, the second paragraph is an optional hint. MindFeast ignores additional paragraphs. Essay, gratitude, and narration prompts must be non-blank. Conversation opening questions must also be non-blank. The narration prompt appears only in phase 2. Informational body text is optional when media is present.

## Frontmatter fields

| Field | Status | Meaning |
|---|---|---|
| `id` | Required | Stable slide identifier; must equal the directory name. |
| `type` | Required for conforming packages | `question`, `informational`, `essay`, `gratitude`, `narration`, or `conversation`. MindFeast treats a missing or unrecognized legacy value as `question`. |
| `image` | Conditionally required | Image filename in the slide directory. |
| `audio` | Conditionally required | Audio filename in the slide directory. One possible narration source. |
| `script` | One possible source for `narration` | Filename of non-blank UTF-8 plain text for on-device text-to-speech. |
| `passage` | One possible source for `narration` | Filename of non-blank UTF-8 plain text for the child to read on screen. |
| `intent` | Required for `conversation` | Non-blank string of parent instructions to the AI, hidden from the child. |
| `turns` | Required for `conversation` | Integer of at least 1. One turn is one child reply plus one AI reply. Booleans, strings, and floats are invalid. |
| `context` | Required for `conversation` | Filename of non-blank UTF-8 text sent only to the AI, never shown to the child. |
| `answer` | Required for `question` | Correct free-text answer. Ignored by other slide types. |
| `accept` | Optional for `question` | List of alternate accepted free-text answers. Ignored by other slide types. |
| `choices` | Optional for `question` | Multiple-choice options. Ignored by other slide types. |
| `difficulty` | Optional | Difficulty label; defaults to `easy`. Charlotte normally uses `easy`, `medium`, or `hard`. |
| `orientation` | Optional | `landscape` or `portrait`; defaults to `landscape`. |
| `subject` | Extension | Human/tooling category metadata. The current MindFeast application ignores it. |

MindFeast currently ignores unknown frontmatter fields. Extensions therefore must not change the meaning of standard fields or be required to render or answer a slide. Producers should omit fields they do not use.

## Slide types

### Question

A question slide requires a non-blank first body paragraph, `answer`, and at least one of `image` or `audio`. `accept` adds free-text equivalents. When `choices` is present, MindFeast presents the values as answer buttons. A second body paragraph is an optional hint.

### Informational

An informational slide requires at least one of first-paragraph body text, `image`, or `audio`. It has no answer and is dismissed with the continue control.

### Essay

An essay slide requires a non-blank first body paragraph and at least one of `image` or `audio`. It accepts any non-blank free-form response. After submission, MindFeast records the response and deactivates the slide until a parent reactivates it.

### Gratitude

MindFeast ships with a standard recurring gratitude starter slide. The `gratitude` type represents that special application feature and compatible variations. It has the same package requirements and free-form submission behavior as an essay slide, but MindFeast records its responses in the gratitude journal and leaves the slide active after submission.

### Narration

A narration slide requires a non-blank first body paragraph and exactly one of `audio`, `script`, or `passage`. An optional `image` is decorative.

The slide has two phases in a single pass:

1. Phase 1 presents the passage from the declared source. The app plays `audio`, reads `script` aloud with on-device text-to-speech, or displays `passage` for the child to read.
2. Phase 2 hides the passage and shows the first body paragraph as the narration prompt. The child tells back the passage by typing or keyboard voice typing, as on an essay slide.

Once phase 2 starts, the passage cannot be reopened or replayed. Narration has no AI interaction or turns. It accepts any non-blank response. The app records the response like an essay response and deactivates the slide until a parent reactivates it. `answer`, `accept`, and `choices` are ignored.

### Conversation

A conversation slide requires a non-blank first body paragraph as its visible opening question. It also requires `intent`, `turns`, and `context`. Both `image` and `audio` are optional.

`intent` contains the parent's instructions to the AI, such as "draw out the right answer" or "explain and inform". The child never sees this field. `context` names a UTF-8 text file sent only to the AI, never displayed to the child. Both the intent and the context file must be non-blank.

`turns` specifies the number of exchanges after the opening question. One turn consists of one child reply followed by one AI reply. The opening question does not count as a turn. The conversation finishes after the AI reply in the final turn. `turns` must be an integer of at least 1. Booleans, strings, and floats are invalid.

The AI follows the intent and context, including when the child replies "I don't know". There is no special handling for that reply. `answer`, `accept`, and `choices` are ignored.

## Expected app behavior (non-normative)

This section gives package authors context for future app implementation. These behaviors are not package validation requirements and do not describe implemented app support.

- Conversation slides are enabled only through a parent-only settings switch that displays a consent notice. Until enabled, conversation slides cannot be created, and synced conversation slides are not shown.
- A conversation slide cannot be created on the device unless an AI key is configured there.
- If the AI cannot run, the slide displays a clear warning with the reason, then offers a written answer. Reasons include no key, no connection, or an AI service report that zero data retention is not in effect for the request. The app records the answer as a written response, not a conversation. It never falls back silently.
- Voice is a per-device setting. Voice input uses on-device speech recognition, and replies use on-device text-to-speech. Only text is sent to the AI.
- Each finished conversation produces one stats entry that holds all its turns. An interrupted conversation restarts from the beginning. Unfinished conversations are not saved.
- Each AI reply has a flag control that opens a prefilled email to the publisher for the parent to send.
- Narration is a single pass. Once phase 2 starts, the passage cannot be reopened or replayed.

## Media and text files

`image`, `audio`, `script`, `passage`, and `context` values are local filenames, not paths. The referenced file must exist beside `slide.md`. Known-good image extensions are `.jpg`, `.jpeg`, `.png`, and `.webp`. Known-good audio extensions are `.mp3`, `.m4a`, `.wav`, `.ogg`, `.flac`, and `.aac`.

The known-good text extension for `script`, `passage`, and `context` is `.txt`. Text files must contain non-blank UTF-8 plain text. For narration sources and the conversation context file, the validator reports unknown extensions as warnings, not errors.

Question, essay, and gratitude slides require at least one image or audio file. Informational slides may be text-only. Narration requires exactly one audio or text source, with an optional decorative image. Conversation requires a context text file, with optional image and audio files. A package may contain both image and audio.

## Validation and compatibility

A conforming version 1 producer:

1. writes the required package layout and frontmatter fields;
2. uses one of the six supported `type` values;
3. follows the content requirements for that type;
4. keeps referenced files inside the slide directory; and
5. uses a valid orientation when one is supplied.

MindFeast retains compatibility with older packages whose `type` is missing or contains category metadata: it interprets them as question slides. New packages should put category metadata in `subject` and use a supported `type`.

The companion [frontmatter schema](mindfeast-slide-frontmatter-v1.schema.json) validates the YAML mapping after it has been parsed as JSON-compatible data. The schema requires exactly one narration source and all three conversation fields. It checks filename syntax for narration sources and the conversation context file, non-blank intent, and the minimum turn count. Unknown fields remain allowed through `additionalProperties: true`.

Charlotte's `mindfeast-slide-builder` validator checks directory layout, file existence, UTF-8 text content, and Markdown body rules. It rejects blank text files and warns about ignored answer fields. The validator also rejects float values for `turns`, including `3.0`. JSON Schema treats a number with no fractional part as an integer, so the schema alone cannot reject `3.0`.

## Examples

These examples show complete `slide.md` files. Each referenced file must exist in the same directory and meet the content requirements above.

### Informational

```markdown
---
id: moon-context
type: informational
subject: astronomy
image: moon.jpg
difficulty: easy
orientation: landscape
---

The Moon reflects sunlight; it does not make its own visible light.
```

### Essay

```markdown
---
id: cloud-observation
type: essay
subject: nature-study
image: clouds.jpg
difficulty: easy
orientation: landscape
---

Describe the cloud shapes you notice and what weather they might bring.
```

### Gratitude variation

```markdown
---
id: gratitude-noticing
type: gratitude
subject: reflection
image: gratitude-noticing.jpg
difficulty: easy
orientation: landscape
---

What is one good thing you noticed today?
```

This example deliberately uses an id other than the bundled starter slide's `daily-gratitude` id.

### Narration

This example requires `passage.txt` containing the passage for the child to read.

```markdown
---
id: seed-narration
type: narration
subject: nature-study
passage: passage.txt
orientation: portrait
---

Tell back what you read about how a seed begins to grow.
```

### Conversation

This example requires `context.txt` containing the factual background for the AI, such as how roots absorb water and anchor a plant.

```markdown
---
id: roots-conversation
type: conversation
subject: nature-study
intent: Draw out how roots help a plant grow.
turns: 3
context: context.txt
orientation: portrait
---

How do roots help a plant grow?
```

The question example earlier in this document completes the six supported types.

## Naming and branding

“Compatible with MindFeast” and similar factual compatibility statements are welcome. The Apache License for Charlotte does not grant permission to use MindFeast logos, app icons, official-looking badges, or claims of endorsement, approval, certification, partnership, or “Official MindFeast” status.
