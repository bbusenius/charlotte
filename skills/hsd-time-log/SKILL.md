---
name: hsd-time-log
description: Project lesson logs into Homeschool-Dashboard-compatible time-tracking spreadsheets configured in students.yaml. Use when the user asks to log homeschool dashboard time, update Homeschool-Dashboard records, or catch the spreadsheets up. Writing the lesson logs themselves is a separate skill (lesson-log).
argument-hint: "[child-name] [since YYYY-MM-DD]"
---

# HSD Time Log

Fill in the Homeschool-Dashboard spreadsheet rows for sessions that already have
a lesson log.

The lesson log under `lesson-logs/` is the system of record; a spreadsheet row is
a one-line receipt of it, and the dashboard renders that row when you hover a
date. This skill only ever adds missing rows.

## Usage

- `/hsd-time-log` — catch up every student
- `/hsd-time-log <student>` — one student
- `/hsd-time-log <student> since <date>` — narrow the range

Runs when the user says "log homeschool dashboard", "log HSD", or asks to bring
the dashboard spreadsheets up to date. Plain "log time" means writing the lesson
logs themselves — that is `lesson-log`, not this skill.

This skill is decoupled from capture on purpose. A log missing either start or
end time needs a conversation before it can be projected, and gap-filling means
running this later costs nothing.

## Three rules

1. **Gap-fill only.** If a session already has a row, do nothing. Never update,
   rewrite, or overwrite an existing row — Brad hand-edits these workbooks and
   those edits must survive. Running this twice writes nothing the second time.
2. **Only sessions with a lesson log.** Rows with no log behind them are never
   touched and never counted as missing. Years of pre-log history stay exactly
   as they are.
3. **Materials and ISBN are never written.** They describe the curriculum for a
   whole course and are set by hand at the start of the year. Writing them per
   row would fill the dashboard's curricula table with repeats.

## Workflow

### Step 1: Find the gaps

```bash
.venv/bin/python scripts/hsd_project.py gaps --student <student> \
  [--from YYYY-MM-DD] [--to YYYY-MM-DD]
```

Resolve the student from `students.yaml` by slug, display name, or alias; never
hard-code names or paths. With no student argument, run this for each student in
the registry.

The result gives you:

- `pending` — logged sessions with times and no row yet. These are the work.
- `waiting_on_times` — logs missing a usable start or end time. They cannot be
  projected; Homeschool-Dashboard requires both. Report them so the user can
  supply the times, then they will appear as `pending` next run.
- `unknown_subject` — a log whose subject has no matching sheet. Report it;
  do not invent a sheet.
- `already_logged` — the count that needed nothing.
- `hsd_enabled` — if `false`, the user has turned off `logging.hsd` in
  `runtime.yaml`. Say so and stop.

Scope is the student's current grade directory. A previous grade's logs belong
to a previous grade's workbook.

If nothing is pending for anyone, say so and stop.

### Step 2: Read each pending log

Read the session's `log.md`. You need two things from it:

- **Description** — one sentence, the row the dashboard will show when the user
  hovers that date. Lead with the lesson number and title when there is one, then
  what was actually covered. For example: *"Lesson 45: Comparing Rounded Amounts
  with Actual Amounts — rounding to the nearest dollar and comparing estimates to
  exact prices."* Draw it from the log's **What we did** section. Keep it to one
  sentence.
- **Notes** — the observation, drawn from the log's **How it went** section.
  Condense to a phrase or short sentence: *"Confused 6s and 9s; wanted to redo
  the last four."* Skip it when the log records nothing worth carrying over.

Do not re-derive either from curriculum files or images. The log already did that
work; this step is compression, not analysis.

### Step 3: Back up before the first write

Once per workbook per invocation, before any row is written:

```bash
mkdir -p .backups/<display_name>/
cp "<time_tracking_spreadsheet>" ".backups/<display_name>/<YYYYMMDD-HHMMSS>-<filename>"
```

### Step 4: Append

One call per session:

```bash
.venv/bin/python scripts/hsd_project.py append --student <student> \
  --log <session-directory> \
  --description "<one sentence>" \
  [--notes "<observation>"]
```

Date, start time, end time, and teacher come from the log's frontmatter — do not
pass them and do not retype them. The script places every value by header name,
so `Notes` lands in the right column on sheets that have one and is skipped
silently on sheets that do not (`notes_skipped_no_column` in the result says
when that happened). It also writes a hidden `Lesson Log ID` column based on the
session path. That stable ID prevents a corrected start time from making a
second row; older rows without IDs retain the date/start fallback. The script
re-checks for an existing row immediately before writing and returns
`written: false` rather than creating a duplicate.

## Summary

Report:

- Rows written per student, with date, subject, and lesson
- Sessions waiting on times, named specifically, since those need the user
- Any unknown subjects
- How many sessions already had rows
- Any sheet where a note was dropped for lack of a Notes column

Keep workbook paths out of the summary unless the user asks for provenance.
