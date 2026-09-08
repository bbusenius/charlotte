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
are the durable record; this is a refocus — what stood out, and what to give
attention to next.

One message. Not a class-by-class recap. Not a file.

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

5. Read the week's observations as a whole, not as a pile of classes. Write
   one digest covering everyone in the run. When more than one student is
   covered, group highlights and attention items by child.

6. Reply with that digest in the current conversation. That is delivery,
   including on a scheduled run — the harness posts it back to the
   conversation that owns the job. Do not write a report file. Do not write
   into a student's `inbox` queue.

If `list` returns nothing, say that no lesson logs were found for the range.
Do not fall back to spreadsheet rows.

## Editorial contract

Write for the household's adults. Do not assume how many there are, or that
the reader was in every lesson. Give enough concrete context that someone who
was not there can follow the observation. Do not recap the timetable.

Keep it short enough to read as a single chat message. If the runtime has a
message length limit, stay under it.

Shape:

1. **Frame** — who is covered and the date range. Not a greeting.
2. **Highlights** — the few things that were genuinely notable. Skip routine
   work that went as expected.
3. **Needs attention** — the point of the skill. Concrete, named, and specific.
   Group related issues across sessions. "Spelling is the running trouble this
   week — family, because, again, and the doubling in shipped/getting/running"
   is the right grain. "Math needs work" is not. When more than one child is
   covered, say whose observation it is.
4. **Carry-forward** — what to actually do next, drawn from "What comes next"
   and from patterns across the week. Short. Actionable.

Rules:

- A locator is not a recap: "in the Lesson 1 nouns/verbs/adjectives work, she
  defaulted to 'nouns' for mixed boxes" is the right amount of scene-setting.
- Do not invent observations. If a session has no "how it went" signal, it is
  not a highlight and not a problem.
- Name the child as a person doing specific work, not as a deficit.
- Quiet weeks are valid. Say so in a few sentences rather than padding.
- Do not include hours, spreadsheet paths, session paths, or how material was
  ingested.
- Do not read `schedules/` or flag subjects that were "supposed" to happen.
  Talk about what the logs show.
