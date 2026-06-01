---
name: hsd-records-read
description: Answer questions from Homeschool-Dashboard-compatible time and reading-list spreadsheets configured in students.yaml. Use when the user asks what a student last did in a subject, what lessons/books were logged, hours by date range, recent reading, whether a book is logged, or other read-only questions about homeschool records.
argument-hint: [question about logged records]
---

# HSD Records Read

Answer read-only questions from the student's configured Homeschool-Dashboard-compatible workbooks.

## Routing

Use this skill for questions such as:

- "What was the last thing Eliana did in Math?"
- "What books has Isamaya read lately?"
- "How many Science rows were logged this month?"
- "Did we log Frog and Toad?"

Do not use this skill to append records. Use `hsd-time-log` or `hsd-book-log` for write workflows.

## Workflow

1. Resolve the student from `students.yaml` by slug, display name, or alias. Never hard-code names, paths, subjects, or sheet names.
2. Map the user's question to `scripts/hsd_read.py`.
3. Run the narrowest useful query and read the JSON result.
4. Answer from the returned rows. Keep workbook paths out of the answer unless the user asks for provenance or debugging.

## Commands

Time records:

```bash
.venv/bin/python scripts/hsd_read.py --student <student> time \
  [--subject "Math"] [--from YYYY-MM-DD] [--to YYYY-MM-DD] \
  [--query "text"] [--latest N] [--limit N]
```

Reading records:

```bash
.venv/bin/python scripts/hsd_read.py --student <student> books \
  [--query "title or author"] [--list-type all|read_by_self|read_to] \
  [--latest N] [--limit N]
```

## Interpretation

- `--latest` returns newest matching time rows first. For books, "latest" means latest appended rows because reading-list workbooks do not contain dates.
- For questions about "last thing in <subject>", use `time --subject "<subject>" --latest 1`.
- For subject names, use the exact configured subject/sheet name when known. If the prompt uses a clear lowercase equivalent, map it to the configured subject from `students.yaml`.
- If the JSON returns no rows, say that no matching logged record was found.
- Do not expose raw spreadsheet dumps to the model. If a query needs more context, rerun the script with a slightly broader filter.
