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
  script.md
  passage.md
  context.md
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

The first body paragraph is the visible question, prompt, or informational text. For question slides only, the second paragraph is an optional hint. MindFeast ignores additional paragraphs. Essay, gratitude, and narration prompts and conversation opening questions must be non-blank. Informational body text is optional when media is present.

## Frontmatter fields

| Field | Status | Meaning |
|---|---|---|
| `id` | Required | Stable slide identifier; must equal the directory name. |
| `type` | Required for conforming packages | `question`, `informational`, `essay`, `gratitude`, `narration`, or `conversation`. MindFeast treats a missing or unrecognized legacy value as `question`. |
| `image` | Conditionally required | Image filename in the slide directory. |
| `audio` | Conditionally required | Audio filename in the slide directory. For `narration`, the audio of the passage. |
| `script` | One possible source for `narration` | Markdown filename in the slide directory. The passage text, meant to be read aloud. |
| `passage` | One possible source for `narration` | Markdown filename in the slide directory. The passage text, meant to be read on screen. |
| `intent` | Required for `conversation` | Instructions for the AI. Not shown to the learner. |
| `turns` | Required for `conversation` | Number of turns, an integer of at least 1. One turn is one learner reply plus one AI reply. |
| `context` | Required for `conversation` | Markdown filename in the slide directory. Background text for the AI. Not shown to the learner. |
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

A narration slide asks the learner to take in a passage, then narrate it back. It requires a non-blank first body paragraph, which is the narration prompt, and exactly one passage source:

- `audio`: audio of the passage;
- `script`: passage text meant to be read aloud;
- `passage`: passage text meant to be read on screen.

`image` is optional. `answer`, `accept`, and `choices` are ignored.

### Conversation

A conversation slide asks the learner an opening question, followed by a conversation with an AI. The first body paragraph is the opening question and must be non-blank. The slide also requires:

- `intent`: instructions for the AI, such as "draw out the right answer" or "explain and inform". It is not shown to the learner.
- `turns`: the number of turns, an integer of at least 1. One turn is one learner reply plus one AI reply. The opening question is not a turn.
- `context`: a Markdown file of background text for the AI. It is not shown to the learner.

`image` and `audio` are optional. `answer`, `accept`, and `choices` are ignored.

## Media and Markdown files

`image`, `audio`, `script`, `passage`, and `context` values are local filenames, not paths. The referenced file must exist beside `slide.md`. Known-good image extensions are `.jpg`, `.jpeg`, `.png`, and `.webp`. Known-good audio extensions are `.mp3`, `.m4a`, `.wav`, `.ogg`, `.flac`, and `.aac`.

`script`, `passage`, and `context` name Markdown files with the `.md` extension. These files must contain non-blank UTF-8 text. For narration sources and the conversation context file, the validator reports any other extension, including `.txt`, as a warning, not an error.

Question, essay, and gratitude slides require at least one image or audio file. Informational slides may be text-only. Narration requires exactly one audio or Markdown source, with an optional image. Conversation requires a Markdown context file, with optional image and audio files. A package may contain both image and audio.

## Validation and compatibility

A conforming version 1 producer:

1. writes the required package layout and frontmatter fields;
2. uses one of the six supported `type` values;
3. follows the content requirements for that type;
4. keeps referenced files inside the slide directory; and
5. uses a valid orientation when one is supplied.

MindFeast retains compatibility with older packages whose `type` is missing or contains category metadata: it interprets them as question slides. New packages should put category metadata in `subject` and use a supported `type`.

The companion [frontmatter schema](mindfeast-slide-frontmatter-v1.schema.json) validates the YAML mapping after it has been parsed as JSON-compatible data. The schema requires exactly one narration source and all three conversation fields. It checks filename syntax for narration sources and the conversation context file, non-blank intent, and the minimum turn count. Unknown fields remain allowed through `additionalProperties: true`.

Charlotte's `mindfeast-slide-builder` validator checks directory layout, file existence, UTF-8 text content, and Markdown body rules. It rejects blank Markdown files and warns about ignored answer fields. The validator also rejects float values for `turns`, including `3.0`. JSON Schema treats a number with no fractional part as an integer, so the schema alone cannot reject `3.0`.

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

This example requires `passage.md` containing the passage text.

```markdown
---
id: seed-narration
type: narration
subject: nature-study
passage: passage.md
orientation: portrait
---

Tell back what you read about how a seed begins to grow.
```

### Conversation

This example requires `context.md` containing the factual background for the AI, such as how roots absorb water and anchor a plant.

```markdown
---
id: roots-conversation
type: conversation
subject: nature-study
intent: Draw out how roots help a plant grow.
turns: 3
context: context.md
orientation: portrait
---

How do roots help a plant grow?
```

The question example earlier in this document completes the six supported types.

## Naming and branding

“Compatible with MindFeast” and similar factual compatibility statements are welcome. The Apache License for Charlotte does not grant permission to use MindFeast logos, app icons, official-looking badges, or claims of endorsement, approval, certification, partnership, or “Official MindFeast” status.
