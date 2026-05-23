---
name: time-log
description: Process Signal messages from homeschool lesson groups, identify lessons covered, and log time entries to spreadsheets.
argument-hint: [child-name]
---

# Time Log

Process unprocessed Signal messages to identify homeschool lessons and log them to time tracking spreadsheets.

## Usage

- `/time-log` — process all children
- `/time-log alice` — process only Alice's messages
- `/time-log charlie` — process only Charlie's messages

## Workflow

### Step 0: Load student registry

Read `students.yaml` at the repo root. This is the single source of truth for all per-student configuration. From it, extract for each student:

- `display_name` — used for backup directory names and summaries
- `signal_group_alias` — the group name passed to signal-sieve
- `aliases` — alternate names the user may supply as `$ARGUMENTS`
- `time_tracking_spreadsheet` — path to the xlsx file (expand `~`)
- `curricula_dir` — base directory for curriculum markdown files (relative to repo root)
- `curricula` — map of filename → `{ subject, lesson_header_pattern, lesson_title_on_next_line }`. An empty map means no curricula are available for this student.
- `subjects` — valid sheet names for this student

Also read the top-level `teacher:` field — this is the fallback name written to the Teacher column if a message has no `sender_alias`.

Use the project-local console commands `.venv/bin/signal-sieve` and `.venv/bin/xlsx-append`. These are installed by `.venv/bin/pip install -e .`.

If `$ARGUMENTS` names a child (by slug or any alias), restrict processing to that student. Otherwise process all students.

### Step 1: Fetch messages

For each student to process, run:

```bash
.venv/bin/signal-sieve list --group <signal_group_alias>
```

If there are no unprocessed messages for any student, tell the user and stop.

### Step 2: Analyze messages

Look at ALL messages for a student together to understand the full context. Messages may arrive as:
- Text describing what was covered (e.g. "Math lesson 45, 9:00-9:45")
- Screenshots of lesson pages or completed work
- A mix of text and images for the same lesson
- Multiple messages about the same lesson session

For each message with image attachments, use the Grok Vision MCP (`mcp__grok-mcp__chat_with_vision`) to analyze the image. The attachment `path` field in the JSON gives the full file path to pass to Grok. **Important**: Include in your Grok prompt that the image may be rotated or sideways, and to try reading it in all orientations before determining lesson numbers and titles.

From the messages, extract:
- **Subject** (must match one of the student's `subjects` exactly — case-sensitive)
- **Lesson number** (if identifiable)
- **Start time and end time** — ALWAYS use the times stated by the sender in the message text. Never use the message timestamp for start/end times.
- **Date** — use the date from the message `timestamp` field (convert from milliseconds epoch to local date)
- **Teacher** — use `sender_alias` from the message if present; fall back to `teacher` from students.yaml. If the message indicates the student worked independently (e.g. "did this on her own", "worked independently", "she did this herself"), set teacher to `""` regardless of sender_alias.

### Step 3: Curriculum lookup and cross-check

If the student's `curricula` map is non-empty and a lesson number and subject are identified, find the curriculum file whose `subject` matches, then look up the lesson using its `lesson_header_pattern`:

```bash
grep -n "<lesson_header_pattern with number substituted>" <curricula_dir>/<filename>
```

Then read the content around that line to understand what the lesson covers. If `lesson_title_on_next_line` is `true` for that file, the lesson title is on the line immediately following the header match.

If the configured lesson-header regex misses, do not stop immediately. Curriculum markdown is often produced from OCR/PDF extraction and may contain broken spacing or malformed headings. Fall back to a targeted text search in the same curriculum file using the lesson number, visible title/topic, book/chapter names, assessment label, or distinctive terms from the screenshot. If the fallback search finds a clear match, use it and note the regex miss only if it matters to the final summary. If the fallback search is ambiguous, skip that entry rather than guessing.

**Cross-check**: Compare the topic Grok described from the image against the curriculum title for the looked-up lesson number. If they don't match (e.g. Grok described "Highway Themes" but the curriculum says "Adjectives and Adverbs"), the lesson number was likely misread. In that case:
1. Search the curriculum file for a lesson whose title better matches what Grok described.
2. If a better match is found, use that lesson number instead.
3. If no match is found, flag the entry in the summary as uncertain and still log it using Grok's description (not the mismatched curriculum title).

Use the confirmed lesson info to write the description for the spreadsheet entry.

If the student's `curricula` map is empty, skip this step — write the description based on message context alone.

### Step 4: Back up spreadsheets

Before making any edits, copy each spreadsheet that will be modified.

```bash
mkdir -p .backups/<display_name>/
```

```bash
cp "<time_tracking_spreadsheet>" ".backups/<display_name>/<YYYYMMDD-HHMMSS>-<filename>"
```

Only back up once per spreadsheet per invocation, even if logging multiple entries.

### Step 5: Log entries

For each lesson identified, append a row to the spreadsheet using the `teacher` value read from students.yaml:

```bash
.venv/bin/xlsx-append "<time_tracking_spreadsheet>" "<Sheet Name>" "<Date>" "<Start Time>" "<End Time>" "<Description>" "<teacher>" --json
```

Column order: Date, Start Time, End Time, Description, Teacher

- **Date**: format as `M/D/YYYY` (no leading zeros on month or day, e.g. `2/7/2026`, `3/2/2026`). Plain text, not a date field.
- **Start Time / End Time**: format as 12-hour clock with AM/PM (e.g. `9:00 AM`, `2:15 PM`). The parent may write times informally (e.g. "1-2", "2 o'clock to 2:10", "9-9:45"). Normalize these to proper times. Infer AM/PM from context — school hours are roughly 8 AM to 4 PM. A time like "2" or "2:10" means PM. A time like "9" or "9:45" means AM.
- **Description**: a concise summary of the lesson. If curriculum was looked up, include the lesson number, title, and a brief note on what was covered (e.g. "Lesson 45: Comparing Rounded Amounts with Actual Amounts — rounding to nearest dollar and comparing estimates to exact prices"). Keep it to one sentence. If no curriculum is available, describe based on message context.
- **Teacher**: use the teacher value derived in Step 2 (sender_alias, fallback, or `""` for independent work)

### Step 6: Mark processed

After all entries are logged successfully, mark all handled message IDs as processed in one call:

```bash
.venv/bin/signal-sieve mark-processed <id1> <id2> <id3> ...
```

### Step 7: Summary

Output a summary of what was logged:
- How many entries per child
- Subject, lesson, and time for each entry
- Any messages that couldn't be processed (and why)

## Important notes

- The sender's stated times are authoritative. Never substitute message timestamps for lesson times.
- Multiple messages may relate to the same lesson — group them logically before logging.
- If you cannot determine the subject or times from a message, skip it and include it in the summary as unprocessed. Do NOT mark it as processed.
- If a message is clearly not about a lesson (e.g. casual conversation), mark it as processed and skip it.
- The spreadsheet sheet names must match exactly (case-sensitive) — use the student's `subjects` list from students.yaml.
- Always back up before writing.
- Never hard-code student names, paths, subjects, or the teacher name — derive everything from students.yaml.
