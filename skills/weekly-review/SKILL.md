---
name: weekly-review
description: >
  Write a household digest of a week's lesson logs — highlights and standouts,
  with extra weight on problems and things that need attention. Chat only; no
  saved file. Safe for a scheduled weekly cron run. Use when the user asks for
  a weekly review, how the week went, a week in review, a parent report of the
  week, or a weekly summary of learning, or when a scheduled job invokes this
  skill. Do not use for a single-lesson question, hours, books, dashboards, or
  MindFeast slides.
argument-hint: "[student-name] [from YYYY-MM-DD] [to YYYY-MM-DD]"
---

# Weekly Review

A short digest of the week's lesson logs for the household's adults. The logs
are the durable record. This message is the few things worth noticing across
the week.

One message, scannable on a phone. A few bullets. Not a class-by-class recap,
not a reconstruction of the pages, and not a file.

## Usage

- `/weekly-review` — every student in `students.yaml`
- `/weekly-review <student>` — only that student
- Range from the prompt (`last week`, `the week of the 1st`, `--from` / `--to`)

Also runs when the user says "how did the week go", "week in review", or asks
for a parent report of the week's learning, and when the harness cron invokes
it on a weekly schedule.

Do not create slides, write logs, or touch a spreadsheet.

Keep the run noninteractive and safe for cron. A scheduled job has no one to
answer a question. Use the defaults when the prompt names no student and no
range: every student, seven calendar days ending today. Never ask which child
or which week. Never wait for confirmation. If a required capability is
unavailable, stop and report it.

## Workflow

1. Read `students.yaml`. Default: every student. If the prompt names a student
   by slug, display name, or alias, only that one. Never hard-code names.

2. Resolve the range. Default: the seven calendar days ending today, inclusive.
   Honor explicit dates. Treat "last week" the same as the default. A weekly
   cron run with no range uses this default.

3. For each covered student:

```bash
.venv/bin/python scripts/lesson_log_read.py list \
  --student <student> --from YYYY-MM-DD --to YYYY-MM-DD \
  --include-section "how it went" --include-section "what comes next" \
  --limit 50
```

`--limit` must be high enough to return the whole week; the helper defaults to
20. Do not use `skills/mindfeast-weekly-slides/scripts/collect_week.py`.

4. For sessions whose condensed "how it went" mentions struggle, confusion,
   retrying, mistakes, incomplete work, or concern, pull the full sections:

```bash
.venv/bin/python scripts/lesson_log_read.py show \
  --session <session-dir> --section "how it went" --section "what comes next"
```

Leave other sessions on the condensed list. Do not pull curriculum files,
captured pages, or video transcripts unless a flagged session's "how it went"
is too thin to stand on and the extra context would change the note.

5. Read the week's observations as a whole. Most of what you read stays out of
   the message. Write one digest covering everyone in the run.

6. Reply with that digest in the current conversation. That is delivery,
   including on a scheduled run — the harness posts it back to the
   conversation that owns the job. Do not write a report file. Do not write
   into a student's `inbox` queue.

If `list` returns nothing, say that no lesson logs were found for the range.
Do not fall back to spreadsheet rows.

## Editorial contract

Write for the household's adults. One concrete locator is enough for a
co-parent to know which work you mean. Do not retell the lesson.

The message is bullets under three headings, after a one-line frame. A bullet is one sentence. Do not write a paragraph under a heading.

1. **Frame** — who is covered and the date range. Not a greeting.
2. **Highlights** — at most 3 bullets for the whole run. Skip routine work
   that went as expected.
3. **Needs attention** — at most 2 bullets per student. This is the point of
   the skill. Name the pattern and one example. "Spelling in her own sentences
   is the running trouble — because, and the doubling in shipped — not the
   copied lists" is the right grain. "Math needs work" is not. A walk through
   every letter, every problem, or every blank is not.
4. **Next** — at most 2 bullets per student. The action to take, drawn from
   "What comes next" and from the patterns above. Not a plan of the coming
   lessons.

When more than one student is covered, name the student inside the bullet.
Use the display name from `students.yaml`. Never hard-code a household.

Rules:

- Most of what you read stays out of the message. Do not list every
  misspelling, every problem, every blank, or every unfinished page.
- Do not invent observations. If a session has no "how it went" signal, it is
  not a highlight and not a problem.
- Name the student as a person doing specific work, not as a deficit.
- A quiet week is valid. Fewer bullets, not padding.
- Do not include hours, spreadsheet paths, session paths, or how material was
  ingested.
- Do not read `schedules/` or flag subjects that were "supposed" to happen.
  Talk about what the logs show.
