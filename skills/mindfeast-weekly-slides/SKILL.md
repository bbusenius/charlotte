---
name: mindfeast-weekly-slides
description: Review a student's recent homeschool time logs, choose a small set of useful weekly review opportunities, create MindFeast-compatible tablet slides with mindfeast-slide-builder, and optionally trigger the student's MindFeast remote sync endpoint. Use when asked to make weekly learning slides, review slides, lock-screen questions, or MindFeast slides from a week of logged lessons.
---

# MindFeast Weekly Slides

Create a small, judgment-driven set of MindFeast slides from a student's week of logged homeschool work. The goal is useful review, not coverage. A normal week should produce fewer than 8 slides, and quiet weeks may produce 0.

This skill orchestrates:

- `hsd-time-log` data already written to the student's time-tracking spreadsheet.
- `mindfeast-slide-builder` for the actual slide packages.
- MindFeast remote sync via the per-student config in `students.yaml`. The standalone sync contract lives in `mindfeast-slide-sync`.

## Student Config

Read `students.yaml` at runtime. Resolve the student by slug, `display_name`, or `aliases`. Never hard-code names, paths, URLs, or tokens.

Use these existing fields:

- `display_name`
- `grade`
- `aliases`
- `time_tracking_spreadsheet`
- `subjects`
- `tablet_slides_dir`
- `curricula_dir`
- `curricula`

This skill also expects per-student MindFeast config:

```yaml
mindfeast:
  remote_url: http://192.0.2.10:8787
  remote_token: "token from MindFeast remote settings"
```

`remote_url` is the base MindFeast remote URL, including scheme, host, and port, with no path or token fragment. `remote_token` is the required token from MindFeast remote settings. Always POST to `<remote_url>/api/sync` and send the token in the `Authorization: Bearer ...` header.

If MindFeast config is missing, still generate slides when appropriate, but skip sync and report exactly which field is missing.

## Workflow

1. Parse the prompt for student, week/range, sync preference, and any explicitly requested subject focus. Normally infer subject weighting from the time-log rows themselves rather than asking for or assuming a subject focus. If no range is specified, review the seven calendar days ending today, inclusive.
2. Run the bundled helper from the repo root to collect relevant rows:

```bash
.venv/bin/python skills/mindfeast-weekly-slides/scripts/collect_week.py \
  --student <student-slug-or-name> \
  --week-start YYYY-MM-DD
```

Omit `--week-start` to use the seven-day period ending today. The helper outputs JSON grouped from the student's time-tracking workbook, including optional `Notes`/`Note` column values when present.

3. When a row references a configured curriculum lesson, use the student's `curricula_dir` and `curricula` map the same way `hsd-time-log` does: find the curriculum whose configured `subject` matches the row's subject, locate the lesson with `lesson_header_pattern`, and read the full matched lesson or covered section when it is available. Do this even when the time-log description is already useful; the curriculum or source material gives better context for choosing and writing slides. If the configured regex misses, do a targeted search in the curriculum file using the lesson number and any distinctive terms from the row. Also read any other lesson material explicitly named in the row when it is available. Skip material lookup only when the curriculum/source is unavailable or the lookup remains ambiguous.
4. Read the enriched rows as a whole week. Consider subject, lesson description, recovered curriculum material, time spent, notes, and repetition across the week.
5. Decide whether slides are warranted. It is valid and sometimes best to create no slides.
6. Build a slide plan before writing files. Keep the plan small: usually 3-6 slides, hard cap 8 unless the user explicitly asks for more.
7. Use `mindfeast-slide-builder` to create each planned slide in the student's `tablet_slides_dir`.
8. Validate every created slide folder with `skills/mindfeast-slide-builder/scripts/validate_slide.py`.
9. If at least one slide was created and sync is not disabled, trigger MindFeast sync with `mindfeast-slide-sync`, run it exactly once, and wait for it to finish.
10. Report created slides, skipped opportunities, validation results, and the completed sync result. Never print the remote token.

## Selection Heuristics

Create slides for durable ideas, weak spots, rich images, memory-worthy facts, and concepts that benefit from spaced review. Prefer the week's actual learning over generic quiz content.

Prioritize:

- Rows whose `Notes` mention struggle, confusion, retrying, needs practice, missed items, or parent concern.
- New vocabulary, people, places, works of art, composers, scientific observations, math ideas, scripture, poetry, phonics, and history episodes.
- Lessons with concrete content in the description.
- Subjects with notes or dense conceptual work, even if that means several slides from one subject and none from another.

Skip:

- Empty or very thin weeks.
- Routine handwriting or drill work with no durable content named.
- Lessons where the log only says a lesson number and no topic can be recovered from the configured curriculum files.
- Content that would create fake or trivial questions.
- Weeks where summer break or light review means slides would add noise.

Do not try to represent every subject. Do not create a fixed number of slides.

## Slide Type Rules

Let the content dictate the slide type:

- `informational`: a brief context card, reminder, quote, or observation prompt that should be dismissed rather than answered.
- Multiple-choice `question`: use when a closed set helps, spelling would get in the way, the answer is a name with accents or uncommon spelling, or the student is young. Put `choices` in final display order and vary correct-answer positions across the set.
- Free-text `question`: use for short recall where typing the answer is reasonable.
- `essay`: use for narration, observation, reflection, or a one-to-three-sentence response when the material calls for the student to answer in their own words. Parent-visible responses are part of the MindFeast workflow.

Write for the student's `grade` and reading level. Keep question text short enough for the lock-screen panel. Hints should reopen attention to the material, not give away the answer. If a slide comes from a specific book and the page, chapter, section, or lesson is known, the hint may point the student back to that source, such as "Look at page 42 of The Burgess Bird Book" or "Check the section on guide words in Lesson 112."

## Slide Generation

Use `mindfeast-slide-builder` as the source of truth for the slide package contract, image policy, validation, and delivery fields.

For planned slides that need images and have no provided image, let `mindfeast-slide-builder` generate calm, specific, full-bleed images using its normal configured image route. Do not generate images for slides that can be effective with existing media or audio, and do not invent copyrighted audio.

For painter or known-work-of-art slides, use the actual artwork image rather than a generated image. Prefer Wikimedia Commons (`https://commons.wikimedia.org/`) because most covered artists and paintings are public domain. Choose a mid-large rendition around 2,500 x 2,000 pixels when available; avoid tiny thumbnails and avoid the largest archival files when Commons offers extremely large versions. Save the image into the slide package through `mindfeast-slide-builder` as provided media, and keep the artwork title/artist in slide text and metadata rather than baking labels into the image.

Choose stable IDs from the topic, not from calendar dates. If an ID already exists, make the slug more specific rather than overwriting an existing slide unless the user explicitly asked to replace it.

## MindFeast Sync

Only sync after successful slide creation and validation. If no slides were created, do not POST unless the user explicitly asks.

Normalize the sync endpoint:

- Strip trailing slash.
- Append `/api/sync`.

Trigger sync with the standalone helper, then wait for it to finish before reporting. This may take a couple of minutes. Run the POST exactly once; never start a second sync because the first one is taking a while.

```bash
.venv/bin/python skills/mindfeast-slide-sync/scripts/sync.py --student <student-slug-or-name>
```

Use the harness's background-command mode when available (for example, `run_in_background: true`) so the agent can wait/poll without blocking the interface. When the command completes, inspect the exit code and JSON output. Report the endpoint host/path and response summary, but never print the token. If the POST fails because network access is blocked, the host is unreachable, authorization fails, or MindFeast returns a non-2xx response, leave the slides on disk and report that sync failed with the relevant status/message.

## Delivery

Summarize:

- Student and week range.
- Number of log rows reviewed.
- Number of slides created, with id, type, subject, and reason.
- Any notable skipped subjects or rows.
- Validation result for each slide.
- Sync status: skipped, completed successfully, or failed with the relevant status/message.

If no slides were created, say so directly and explain the main reason in one or two sentences.
