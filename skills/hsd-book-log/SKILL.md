---
name: hsd-book-log
description: Process Signal messages from book-logging groups, identify books (from title or cover image), look up metadata, and log to Homeschool-Dashboard-compatible reading-list spreadsheets configured in students.yaml.
argument-hint: [child-name]
---

# HSD Book Log

Process unprocessed Signal messages to identify books read (by or to a child) and log them to Homeschool-Dashboard-compatible reading-list spreadsheets.

## Usage

- `/hsd-book-log` — process both children
- `/hsd-book-log <student>` — process only one student's book messages

## Workflow

### Step 0: Load student registry

Read `students.yaml` at the repo root. This is the single source of truth for all per-student configuration. From it, extract for each student:

- `display_name` — used for backup directory names and summaries
- `aliases` — alternate names the user may supply as `$ARGUMENTS`
- `reading.inbox` — the queue book messages arrive in: `kind` names the adapter (`signal` uses signal-sieve) and `queue` is the queue name that adapter knows. Older registries spell this `reading.signal_group_alias`; treat that as `kind: signal` with `queue` set to its value.
- `reading.spreadsheet` — path to the reading list xlsx file (expand `~`)
- `reading.read_by_self_sheet_index` — sheet index for books the student reads themselves
- `reading.read_to_sheet_index` — sheet index for books read to the student
- `reading.default_sheet` — which sheet to use when the message doesn't specify (`read_by_self` or `read_to`)

Use the project-local console commands `.venv/bin/signal-sieve` and `.venv/bin/xlsx-append`. These are installed by `.venv/bin/python -m pip install -e .`.

If `$ARGUMENTS` names a child (by slug or any alias), restrict processing to that student. Otherwise process all students.

### Step 1: Fetch messages

Do not derive the queue name from the display name or user capitalization. Always use the exact `reading.inbox.queue` value from `students.yaml` (or the legacy `reading.signal_group_alias`); queue names are case-sensitive.

For `kind: signal`, run `.venv/bin/signal-sieve list --group <reading.inbox.queue>` to get unprocessed messages as JSON. If `$ARGUMENTS` specifies a child, only fetch that queue; otherwise fetch both. A student with no `reading.inbox` has no book queue — skip them here; their books are logged from what the user tells you directly.

If there are no unprocessed messages, tell the user and stop.

### Step 2: Extract the book from each message

For each message, you need: **title**, and optionally **author** and a **language hint**.

- **Text-only message**: the text is typically just the book title. It may occasionally include author ("Frog and Toad Are Friends by Arnold Lobel"), language cues ("this is a Spanish book"), or context flags — parse these out.
- **Image attachment**: use the active runtime's configured vision capability to read the cover. The runtime decides whether that means the main model's native vision or an auxiliary vision model; do not select or prefer a provider-specific MCP because it happens to be installed. Prompt it to extract **title, author, and apparent language** from the cover — and note if the image shows an audiobook/app UI (Audible, Libby, etc.) rather than a physical book. Include in the prompt that the image may be rotated; try all orientations. If trusted runtime vision is unavailable or fails, do **not** load ad-hoc fallback skills or call provider-specific chat APIs directly. Skip that message and leave it unprocessed so it can be retried later.
- **Text + image**: combine. Text context (e.g. "this was an audiobook") overlays flags onto whatever the image identifies.

Cover text beats API data when both are present — the cover is ground truth for that specific edition.

Group multiple messages that clearly refer to the same book (e.g. a cover photo plus a follow-up text saying "we listened to this one").

### Step 3: Determine target language

- Default: **english**
- Switch to **spanish** if: the vision tool flagged the cover as Spanish, the title is obviously Spanish ("Caperucita Roja", "Vámonos a Antigua"), or the message text says so.

### Step 4: Determine target sheet

Use the student's `reading.default_sheet` as the default. Only flip to the other sheet when the message makes it clear — e.g. a message like "I read this to [student]" or "we read this to her" means `read_to`. A message like "[student] read this by herself" means `read_by_self`. With no such context, use the default.

Resolve the sheet name from the index before calling xlsx-append:

```bash
.venv/bin/python scripts/get-sheet-name.py "<spreadsheet_path>" <index>
```

### Step 5: Determine flag columns

Read the message text (and vision output for images) holistically. Default both flags to blank.

- **Audiobook** = `Yes` if: the message mentions listening to it, or mentions Audible / Libby / Spotify / audiobook / audio book, or the image is of an audiobook app UI.
- **Part of coursework?** = `Yes` if: the message says it was for a class, for school, for a subject (history, language arts, science, etc.), for curriculum, or for coursework.

### Step 6: Look up book metadata

For each book, run the lookup chain in order and stop at the first sufficient answer.

#### 6a. Lexile lookup (primary)

```bash
.venv/bin/python scripts/lexile/lookup.py "<title>" --language <english|spanish>
```

- Exit 0 with JSON → use all 5 fields (title, author, language, isbn, lexile). Done.
- Exit 2 (`no_results`) → fall through to Open Library.

#### 6b. Open Library lookup (secondary)

```bash
.venv/bin/python scripts/openlibrary/lookup.py "<title>" --language <english|spanish> [--author "<author>"]
```

Pass `--author` whenever you have one (from the vision tool or from the message text).

The script returns a `confidence` tier:

- `high` → use all fields as-is. Lexile (Level column) stays blank. Done.
- `medium` → use title/author/language/isbn, then send to Grok for **confirmation** (step 6c).
- `low` → fall through to Grok **fresh search** (step 6c).

Exit 2 (`no_results`) → fall through to Grok.

#### 6c. Search-capable tool (last resort)

Use a search-capable runtime tool. Grok live search MCP is the preferred implementation when available, but an equivalent live/web search tool is acceptable. Never use a generative model to supply a Lexile number; leave Lexile blank in this path.

- **Confirmation** (following a medium OL result): prompt the search-capable tool something like:
  > "Confirm this book exists and give its ISBN-13. Title: `<X>`. Author: `<Y>`. Language: `<english|spanish>`. Respond strictly as JSON: `{\"confirmed\": true|false, \"isbn\": \"<isbn13>\" or null, \"corrected_title\": \"<...>\" or null, \"corrected_author\": \"<...>\" or null}`."

  If `confirmed: true`, fill in the ISBN from the tool response. If `confirmed: false` but corrections are provided, swap them in. If the search result flat-out disagrees, surface this in the summary so it can be reviewed rather than silently logged.

- **Fresh search** (low-confidence OL, or both Lexile and OL missed): prompt the search-capable tool to identify the book and return structured JSON:
  > "Find book metadata: title `<X>` (possibly `<author>`, possibly `<language>`). Respond as JSON: `{\"title\": \"...\", \"author\": \"...\", \"language\": \"english\"|\"spanish\", \"isbn\": \"<isbn13>\" or null}`."

  If the response is empty or clearly wrong, log what you have (even just the title) and flag in the summary as uncertain.

### Step 7: Back up spreadsheets

Before any edits, copy the spreadsheet. Only back up once per spreadsheet per invocation.

```bash
mkdir -p .backups/<display_name>/
```

```bash
cp "<spreadsheet_path>" ".backups/<display_name>/<YYYYMMDD-HHMMSS>-Reading List-<N>.xlsx"
```

### Step 8: Log entries

For each book, append a row:

```bash
.venv/bin/xlsx-append "<spreadsheet_path>" "<sheet_name>" \
  "<title>" "<author>" "<language>" "<isbn>" "" "<lexile>" "<audiobook>" "<coursework>" \
  --json
```

Formatting rules:

- **Language**: capitalize first letter — `English`, `Spanish` (matches existing rows in the spreadsheet).
- **ISBN**: pass as a string, not a number. ISBN-13 preferred; ISBN-10 is acceptable if that's all we have.
- **Lexile** (Level column): format as `<code><number>L`, e.g. `400L`, `AD470L`, `BR200L`. Blank if not measurable or not found.
- **Audiobook** / **Part of coursework?**: `Yes` or blank (empty string). Never `No`.
- Missing author: pass empty string.

### Step 9: Mark processed

After all entries are logged successfully, mark all handled message IDs as processed in one call:

```bash
.venv/bin/signal-sieve mark-processed <id1> <id2> ...
```

### Step 10: Summary

Report what was logged:

- Per child: how many books, which sheet each went to.
- For each book: title, author, language, ISBN (present or absent), Lexile (present or absent), flags, and which source supplied the data (lexile / openlibrary / grok).
- Any messages that couldn't be resolved or had conflicting sources — flag these clearly so they can be reviewed.

## Important notes

- Sheet selection is by **position**, not name — sheet names can change without breaking the skill. Resolve the name at runtime with `get-sheet-name.py`.
- Never use Grok to supply a Lexile number. If the Lexile API doesn't have it, leave the Level column blank.
- Only mark messages as processed after their row has been successfully appended.
- Casual chat in the book groups that isn't about a book should be marked processed and skipped.
- If you cannot confidently identify a book from a message, skip it and leave it unprocessed so it can be retried later.
- Column names in the spreadsheet are identical across both sheets; only the sheet *names* differ by student.
- Never hard-code student names, paths, or spreadsheet locations — derive everything from students.yaml.
