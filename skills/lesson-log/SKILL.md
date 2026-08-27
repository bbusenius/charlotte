---
name: lesson-log
description: Record what was actually taught in a homeschool session as a durable lesson log — captured photos, screenshots, and voice notes, their extracted text, and a written account of what was covered and how it went. Use when the user asks to log time, log lessons, log what we did, process lesson messages, or write up a class. This is the primary record; the Homeschool-Dashboard spreadsheet projection is a separate skill (hsd-time-log).
argument-hint: [child-name]
---

# Lesson Log

Write the durable record of a teaching session: what was taught, how it went, and
the material that proves it. One directory per session under `lesson-logs/`.

This is the **system of record**. The Homeschool-Dashboard spreadsheet row is a
thin projection of it, written separately by `hsd-time-log`. **This skill never
touches a spreadsheet.**

## Usage

- `/lesson-log` — process every student who has material waiting
- `/lesson-log <student>` — only that student

Also runs when the user says "log time", "log Eliana's time", "log what we did",
or describes a lesson directly in conversation.

## What a session looks like

```
lesson-logs/<student>/<grade>/<year>/<month>/<day>/<subject>-<slug>/
    log.md          the synthesis — the deliverable
    messages.md     what the parent said: text verbatim, voice transcribed
    images.md       what Charlotte saw: description always, text when present
    sources/        image-01.jpg, image-02.jpg, voice-01.ogg
```

`sources/` holds the raw files exactly as they arrived, named only by kind and
arrival order. What an image actually is — which workbook page, whether she
filled it in, what the scene shows — goes in `images.md`, never in a filename.

Never build these paths by hand. `scripts/lesson_log_new.py` owns directory
naming, grade directories, collision handling, and source-file numbering.

## Three rules that decide most questions

1. **The log is content.** It records what happened. It never records how it was
   captured, which queue it came from, message IDs, whether a spreadsheet row was
   written, or how many passes assembled it. The inbox tracks what it has
   consumed; the spreadsheet tracks what it has written. Neither belongs here.
2. **Synthesis, not amendment.** Material accumulates; `log.md` is rewritten from
   everything present. There is no "adding to" a log versus "creating" one — a
   screenshot arriving three minutes or three days late is just a source that
   was not there yet. Nothing in a finished log marks it as revised.
3. **Date comes from the content, never from the clock.** "Here are yesterday's
   science photos" logs to yesterday. Stated times are authoritative; a message
   timestamp is never a lesson time.

## Workflow

### Step 0: Load configuration

Read `runtime.yaml` for the `logging` block:

- `logging.lesson_log` — if `false`, this workflow is disabled. Say so and stop.
- `logging.time` — when `false`, lessons carry no clock times. Do not ask for
  them and omit `start_time`/`end_time` from frontmatter.
- `logging.hsd` — informational here. It does not change what this skill writes;
  it only means `hsd-time-log` will later project these logs into spreadsheets.

Defaults when `runtime.yaml` or a key is absent: `lesson_log: true`,
`time: true`, `hsd: false`.

`logging.hsd: true` with either `logging.lesson_log: false` or
`logging.time: false` is a configuration error. Report it rather than silently
running only part of the configured record pipeline.

Read `students.yaml` for each student to process:

- `display_name`, `aliases` — resolving who the user means
- `grade` — the scaffolder turns this into the grade directory
- `subjects` — the valid subject names; a log's subject must match one **exactly**
- `curricula_dir`, `curricula` — curriculum lookup (an empty map means none)
- `inbox` — `kind` names the adapter, `queue` is that adapter's queue name.
  Legacy registries spell this `signal_group_alias`; treat it as
  `kind: signal`. A student with no `inbox` has no queue.

Also read the top-level `teacher:` fallback.

If `$ARGUMENTS` names a child by slug or alias, restrict to that student.

### Step 1: Gather material

Material reaches Charlotte two ways. Both are first-class, and a finished log
looks identical either way.

**From a queue** (when the student has an `inbox`). The queue name already says
which workflow and which student this is, so nothing needs to be inferred. For
`kind: signal`:

```bash
.venv/bin/signal-sieve list --group <inbox.queue>
```

Use the exact configured queue name — case-sensitive, never derived from a
display name. Each message carries a timestamp, sender alias, body text, and
attachment paths. If no student has unprocessed material, say so and stop.

**From conversation** — the user describes a lesson directly and attaches photos
or voice notes. Resolve the student from what they said, from context, or by
asking. Everything downstream is the same.

### Step 2: Read the material

Take all of a student's material together before writing anything; several
messages usually describe one session.

**Images.** Use the active runtime's configured vision capability on every
image. The runtime decides whether that means the main model's native vision or
an auxiliary vision model; do not select or prefer a provider-specific MCP
because it happens to be installed. Include in the prompt that the image may be
rotated or sideways and should be read in every orientation before concluding
anything, especially lesson numbers.

For each image, get **both**: a short description of what it is, and any text it
contains. Description is the frame, not the fallback — a labeled diagram whose
labels read perfectly still needs its arrangement described, and a completed
worksheet's erasures and letter formation matter more than its answers.

**Voice notes.** Transcribe with the runtime's STT layer when it has one,
otherwise:

```bash
.venv/bin/python scripts/transcribe_media.py <path-to-audio>
```

**Extract per session:** the subject (exact match against the student's
`subjects`), the date, start and end times when stated, the lesson number and
title if identifiable, the teacher (`sender_alias`, else the `teacher` fallback,
else `""` when the message says the student worked independently), and which
other children took part.

### Step 3: Look up the curriculum

When the student has a non-empty `curricula` map and the material identifies a
curriculum, resolve its configured file entrypoint with the shared helper:

```bash
.venv/bin/python scripts/curriculum_resolve.py \
  --student <student> --curriculum <id-alias-or-configured-path>
```

When only the subject is known, use `--subject <subject>`. Subject fallback is
valid only when exactly one configured curriculum matches; never choose the
first of several curricula with the same subject.

Treat zero configured curricula matching the subject as normal. Continue from
messages, captured material, and observations with `lesson.curriculum` set to
null and `lesson.sources` set to an empty list. Absence or ambiguity affects
only curriculum enrichment, never whether the lesson is logged.

Inspect the configured entrypoint and its linked native components:

```bash
.venv/bin/python scripts/curriculum_read.py --student <student> inspect \
  --curriculum <id-alias-or-configured-path>
```

Search by the strongest locator supplied by the lesson material. Numbered
lessons can use `--lesson`; unnumbered material can use `--unit`, `--chapter`,
or `--query`. Start with `--role primary-lessons` when the index identifies one:

```bash
.venv/bin/python scripts/curriculum_read.py --student <student> search \
  --curriculum <id-alias-or-configured-path> --lesson <number> \
  --role primary-lessons
```

The helper reads Markdown/text directly and extracts PDF text in memory for the
invocation. Its normalized search view is temporary and is not a converted
curriculum. Search results are candidates: inspect their text and locations,
then read the exact selected source. For PDF pages whose layout, diagrams, or
illustrations matter, supply a temporary `--render-dir`, inspect the rendered
page images, and delete that scratch directory after the session is written:

```bash
.venv/bin/python scripts/curriculum_read.py --student <student> read \
  --source <exact-source-path> --pages <first-last> \
  --render-dir <temporary-scratch-directory>
```

Read the whole bounded lesson, not just the search hit. Expand or trim the page
range until the complete lesson is present. Follow explicit references from the
primary lesson into reader, workshop, card, or other indexed components and add
each source actually used. Skip rather than guess when candidates remain
ambiguous.

**Cross-check the lesson number.** Compare what vision described against the
curriculum title for that lesson number. A mismatch usually means the number was
misread: search for a lesson whose title fits what was described and use that
one instead. If nothing fits, write the log from what vision actually showed —
not from the mismatched curriculum title — and flag it in your summary.

Curriculum and captured pages are not alternatives. When both exist, use both.

### Step 4: Place the session

Look for an existing session before creating one:

```bash
.venv/bin/python scripts/lesson_log_new.py find \
  --student <slug> --date YYYY-MM-DD --subject "<Subject>"
```

Treat the result as a list of **candidates**, not an identity match. Compare the
new material with each candidate's path slug, lesson frontmatter, times, and
existing account. Reuse the candidate this material belongs to. If none is the
same lesson, create a new session — even when there is exactly one candidate.
Do not turn slug, lesson number, or time into a mechanical key: late material
may describe the same lesson differently, and the content is what establishes
the match.

Otherwise create one:

```bash
.venv/bin/python scripts/lesson_log_new.py create \
  --student <slug> --date YYYY-MM-DD --subject "<Subject>" \
  --slug <short-content-slug>
```

The slug names the content: `lesson-112-guide-words`, `charlottes-web-ch-8`,
`forest-plot-survey`. Not the time, not the date, not the subject again.

Two sessions in one subject on one day are normal — a Language Arts lesson in
the morning and reading in the afternoon both log as Language Arts. The messages
say which is which through their times and their content, so create a session
for each. Creating with a slug that already exists returns that session rather
than making a duplicate.

### Step 5: Copy in the sources

Copy every captured file into the session. Never reference an inbox path: those
directories are transient, and a log pointing into one is a dead link within
months.

```bash
.venv/bin/python scripts/lesson_log_new.py add \
  --session <session-dir> --role image --file <path> --file <path>
```

Roles are `image` and `voice` — the only distinction that is never a judgement
call. The script assigns names, continues numbering from what is already there,
never renumbers existing files, and reuses the existing name when the bytes are
identical.

### Step 6: Write `messages.md`

Every inbound message in arrival order. Existing entries are never rewritten;
new material appends.

```markdown
# Source messages

## 2026-07-24 10:22 · Brad · signal

Science this morning, 9:15-10:05. We staked out the plot behind the shed
and she labeled everything herself.

## 2026-07-24 10:47 · Brad · signal

Voice note — [voice-01.ogg](sources/voice-01.ogg):

> She got the idea of decomposers right away but kept calling the fern patch
> a "fern forest," which honestly is better.
```

Text messages verbatim — do not clean up, summarize, or correct them. Voice notes
as transcript with a link to the audio. Provenance is timestamp, sender, and
channel; never message IDs, which point into an inbox that gets pruned.

### Step 7: Write `images.md`

One section per file in `sources/` that was looked at, named for the file.

```markdown
# What the images show

## sources/image-03.jpg
kind: page
ref: Workbook p. 47, Lesson 12

Investigation 3: Mapping a plot. Choose a section of ground roughly four paces
square. Mark the corners...

## sources/image-04.jpg
kind: page
ref: Workbook p. 48
confidence: low

Page 48 with her answers filled in, pencil. Three erasures in the second column.
The plot diagram is hers: four corner boxes with labels, north arrow drawn
bottom-left instead of top.

Labels: white oak / moss - north side / fallen log - decomposers / fern patch

## sources/image-05.jpg
kind: scene
ref: null

A roughly square plot staked at the corners with orange-flagged garden stakes,
at the edge of mixed hardwood. Handwritten index cards tied to four stakes:
"white oak," "moss — north side," "fallen log / decomposers," "fern patch."
```

- `kind` is `page` (any printed or written material) or `scene`. A workbook page
  she has written on is still a page — say so in the description rather than
  trying to file it as something else.
- **`ref` is the real page in the real book** — "Workbook p. 47", "Chapter 4",
  "Lesson 12". This matters: the filename's number is only the order the image
  arrived in and means nothing, while `ref` is what answers "what page are we on
  in Language Arts?" and what would later let a year of captured pages be put
  back in order. Record it whenever the page number is visible. Use `null` only
  when there is genuinely nothing to reference, as with scenes.
- Add `confidence: low` when reading is uncertain, which is normal for a child's
  handwriting.
- Scenes matter. A workbook explains the procedure but cannot record *this*
  staked plot — which corner, which species, which labels. That is
  site-specific and irreplaceable.

### Step 8: Write `log.md`

The synthesis, and the thing anyone will actually read. Rewrite it in full from
everything now in the session — sources, `messages.md`, `images.md`, and the
curriculum. Do not append to what is already there.

```markdown
---
schema: lesson-log/v1
student: eliana
grade: 3
date: "2026-07-24"
start_time: "9:15 AM"
end_time: "10:05 AM"
subject: Science
class: null
lesson:
  curriculum: science-3
  number: 12
  title: "Mapping a Plot"
  sources:
    - path: curricula/third-party/science-3/Science-3.pdf
      role: primary-lessons
      pdf_pages: [53, 54]
  pages: "47-48"
teacher: Brad
also_present: [isamaya]
concepts: [decomposers, habitat, observation]
---

# Science — Mapping a Plot

**2026-07-24 · 9:15–10:05 AM · with Brad**

## What we did

...

## How it went

...

## What comes next

...

## Pages covered

- [Workbook p. 47 — Investigation 3](images.md) · ![](sources/image-03.jpg)
- [Workbook p. 48 — her plot diagram](images.md) · ![](sources/image-04.jpg)

## Source messages

[messages.md](messages.md)
```

Frontmatter rules:

- `subject` must match the student's configured subject exactly — it is how
  every reader, including the spreadsheet projection, finds this log.
- Omit `start_time`/`end_time` entirely when times are unknown or when
  `logging.time` is `false`. Absence is meaningful: a log with no times is one
  that cannot be projected into Homeschool-Dashboard yet.
- `class` is for a generated curriculum this session belongs to; otherwise null.
- `lesson.curriculum` is the stable configured curriculum `id` when one exists,
  otherwise null.
- `lesson.sources` is always a list, empty when no configured source was used.
  Each item requires `path`, the exact leaf source rather than its index. Add the
  component `role` when known. For PDFs, `pdf_pages` records the inclusive PDF
  page index read; for Markdown/text, `section` or `lines` may locate the bounded
  passage. Include every indexed component actually used in the session.
- **`lesson.pages` is where the child actually is in the book** — the printed
  page numbers, as a string like `"47-48"` or `"47"`. Take it from the pages
  captured in `images.md`, from the curriculum lookup, or from what the parent
  said. It belongs in frontmatter, not only in an `images.md` ref, because
  "what page are we on in Language Arts?" should be answerable from the session
  summary without opening anything. Use `null` when the material has no page
  numbers, as with an experiment or a video lesson.
- `also_present` lists other children who took part.
- Never add an `hsd:` block, message IDs, or amendment history.

Body rules:

- **What we did** is the important part. Content, not administration: what was
  read, what the experiment was, what she concluded, what the argument was. A
  reader should learn the lesson from this, not just its name.
- **How it went** is where observations, struggles, and surprises go — "she
  confused 6s and 9s," "the T's are wobbly," "she got decomposers immediately."
  This is what `hsd-time-log` projects into the spreadsheet's Notes column and
  what makes review slides worth generating.
- **What comes next** is a note to your future self about progression.
- **Pages covered** links to `images.md` and embeds the images.
- Link to the sidecars; never inline their content. Duplicated text desyncs the
  moment new material arrives.
- Standard markdown links only. Never Obsidian `[[wiki-links]]`.

### Step 9: One log per student

When a session included more than one child, write a **separate log for each**,
with the narrative repeated and `also_present` naming the others. Each child's
log then carries the observations specific to her, which is usually the
interesting part, and every reader downstream gets one child's history as a
path rather than a query.

### Step 10: Mark the material consumed

Only after the durable log and its sidecars are written. For `kind: signal`:

```bash
.venv/bin/signal-sieve mark-processed <id1> <id2> <id3>
```

Mark successfully logged material even when the log has no times yet; missing
times block only the spreadsheet projection, not the lesson log. Never mark
material that could not be placed into a log. Material that is clearly not about
a lesson — ordinary conversation — can be marked processed and skipped.

## When something is missing

| Missing | What to do |
|---|---|
| Subject/class | No log can be placed; the subject is part of the directory name. Leave the material unprocessed and ask. |
| Times (with `logging.time: true`) | Write the log in full anyway. Every bit of content is preserved; only the spreadsheet row waits. Ask for the times when convenient. |
| Lesson number or curriculum match | Write the log from what the material shows. Note the uncertainty in your summary. |

**Report to the main conversation channel, never into the queue.** Writing into
a queue that exists to be consumed pollutes it — the question comes back as
input on the next run. When a run is unattended, send the report through the
runtime's normal outbound channel:

> I tried to log a Language Arts session from the `eliana` queue for 7/24, but
> there's no start time. Tell me the time when you have it and I'll update the
> pending log.

## Summary

Report per student:

- Sessions written or added to, with subject, date, and path
- What was captured: pages, work, photos, voice notes
- Sessions with no times yet, since those cannot reach Homeschool-Dashboard
- Anything left unprocessed, and what it needs
- Any lesson number that did not match its curriculum title

Do not report which ingest mode was used or how many passes it took. That is
not part of the record.
