---
name: hsd-records-read
description: Answer questions from homeschool records — the lesson logs under lesson-logs/ and the Homeschool-Dashboard-compatible time and reading-list spreadsheets configured in students.yaml. Use when the user asks what a student last did in a subject, what was covered, whether a topic or book has come up, how a lesson went, hours by date range, or recent reading.
argument-hint: [question about logged records]
---

# HSD Records Read

Answer read-only questions about what a student has done.

There are two record sets, and the question decides which one to open:

| Question is about | Source | Why |
|---|---|---|
| What was covered, how it went, whether a topic has come up, what a lesson contained | **Lesson logs** (`scripts/lesson_log_read.py`) | The log holds the full account, the observations, the text of the captured pages, and video transcripts. |
| Hours, totals, date-range time accounting | **Time workbook** (`scripts/hsd_read.py time`) | Hours are a spreadsheet computation, and history from before lesson logging exists only there. |
| Books read | **Reading workbook** (`scripts/hsd_read.py books`) | Reading lists are not lesson logs. |

Do not use this skill to write records. Use `lesson-log`, `hsd-time-log`, or
`hsd-book-log` for that.

## Workflow

1. Resolve the student from `students.yaml` by slug, display name, or alias.
   Never hard-code names, paths, subjects, or sheet names.
2. Decide which record set the question is about, using the table above.
3. Run the narrowest useful query and read the JSON result.
4. Answer from the returned rows or sessions. Keep file paths and workbook paths
   out of the answer unless the user asks for provenance.

## Lesson logs

Session summaries, newest first:

```bash
.venv/bin/python scripts/lesson_log_read.py list --student <student> \
  [--subject "Science"] [--from YYYY-MM-DD] [--to YYYY-MM-DD] \
  [--latest N] [--limit N]
```

Full-text search across the log, the captured page text, video transcripts,
and the parent's original messages:

```bash
.venv/bin/python scripts/lesson_log_read.py search --student <student> \
  --query "guide words" [--subject "..."] [--limit N]
```

Named sections of one session:

```bash
.venv/bin/python scripts/lesson_log_read.py show --session <session-dir> \
  [--file log.md|images.md|messages.md|videos.md] [--section "how it went"]
```

Question shapes:

- "What was the last thing she did in Science?" → `list --subject Science --latest 1`.
  The `summary` field usually answers it without a second call.
- "Have we covered guide words?" → `search --query "guide words"`.
- "What was in that experiment?" → `list` to find the session, then `show` with
  `--section "what we did"`.
- "How did last week go?" → `list --from --to`, then `show --section "how it went"`
  on the sessions that look relevant.

Prefer `--section` over `--full`. A session's log, page transcriptions, video
transcripts, and messages are large; pulling whole sessions into context
defeats the point of these commands.

## Time and reading records

```bash
.venv/bin/python scripts/hsd_read.py --student <student> time \
  [--subject "Math"] [--from YYYY-MM-DD] [--to YYYY-MM-DD] \
  [--query "text"] [--latest N] [--limit N]
```

```bash
.venv/bin/python scripts/hsd_read.py --student <student> books \
  [--query "title or author"] [--list-type all|read_by_self|read_to] \
  [--latest N] [--limit N]
```

- `--latest` returns newest matching time rows first. For books, "latest" means
  the most recently appended rows, because reading-list workbooks have no dates.
- Use the exact configured subject/sheet name when known. Map a clear lowercase
  equivalent from the prompt to the configured subject in `students.yaml`.

## Interpretation

- Lesson logs start from when lesson logging was turned on. For a content
  question about an earlier period, fall back to `hsd_read.py time --query`,
  and say that the older record is a one-line description rather than a log.
- If a query returns nothing, say no matching record was found rather than
  guessing from curriculum files.
- Never dump raw spreadsheet contents or whole log files into the answer. If a
  query needs more context, rerun it slightly broader.
