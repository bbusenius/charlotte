---
name: ao-picture-study
description: Prepare and archive the next AmblesideOnline picture study for a configured student, including the scheduled artwork, an exact reusable curriculum study file, a short grade-appropriate single-narrator audio study, and an informational MindFeast slide that is validated, synced, and selected as the tablet's next slide. Use when the user asks for the next AO picture study, the next AO artist painting, an Ambleside picture-study slide, or an AO art-study podcast.
---

# AO Picture Study

Prepare one complete picture-study experience from the current AmblesideOnline artist rotation. Persist the finished study as reusable curriculum content, but never infer that it was taught: this workflow tracks only what it created and never reads or writes lesson logs.

## Student and output

Read `students.yaml` at runtime. Resolve the student by slug, `display_name`, or `aliases`; never hard-code students, grades, paths, URLs, or tokens.

Require these fields:

- `grade` for transcript level
- `curricula_dir` and a `curricula` entry whose `id` or alias is `ao-picture-study`
- `tablet_slides_dir` for the package destination
- `mindfeast.remote_url` and `mindfeast.remote_token` for sync and selection

If the student or any required field is missing, stop before creating media and report the missing value. Never print the remote token.

## Workflow

Keep the workflow unattended-safe. Use the active environment's normal noninteractive capabilities and the checked-in helper scripts below. Never install software, invoke `sudo`, request a password, or launch an interactive program during a run. If a required capability or dependency is unavailable, stop and report it instead of changing the runtime.

### 1. Resolve the next AO work

From the repository root, run:

```bash
.venv/bin/python skills/ao-picture-study/scripts/rotation.py next \
  --student <student-slug-or-name>
```

The helper fetches `https://amblesideonline.org/artists`, parses the year/term rotation, reads the student's last-created cursor from the repository's canonical `.state/ao-picture-study/`, resolves the AO curriculum by identity through `scripts/curriculum_resolve.py`, and returns JSON containing the curriculum entrypoint, exact state path, per-run root scratch directory, suggested exact study path, artist, picture number, title, date, AO link, suggested slide id, output directory, grade, and `introduce_artist` decision.

Use the returned `scratch_dir` for every working file in this run. Do not pass `--state-dir` during a normal workflow. If the returned state or scratch location is not writable, stop and report the runtime problem; never relocate either one into `curricula/`, another content root, or a harness profile.

- With no cursor, begin at picture 1 of the current or upcoming AO term. July through November selects Term 1, December through March selects Term 2, and April through June selects Term 3.
- Otherwise, choose the numbered work after the last successfully created one. After the final numbered work, advance to the first work in the next AO term available on the page.
- Assume the previous picture study was completed. Do not inspect lesson logs and do not track unfinished lessons.
- For an explicit starting point, pass all three of `--school-year`, `--term`, and `--picture-number`.
- Treat the first AO-linked work on a numbered line as the primary selection when AO lists alternatives.
- If AO's page cannot be parsed confidently, stop rather than guessing.

If the suggested study file or target slide folder already exists while the cursor still points to the preceding work, treat it as a resumable partial run. Reuse the established study text and artwork, inspect and repair incomplete slide media, then continue with validation, sync, selection, and cursor commit. Do not advance to another painting or replace an established study with newly generated prose.

### 2. Acquire the actual artwork

Use the real painting or illustration, never generated art. Search in this order:

1. Wikimedia Commons
2. AO's linked page
3. The owning museum or Google Arts & Culture
4. General web or image search

Prefer the highest practical resolution suitable for a tablet. Download working files into the `scratch_dir` returned by Step 1, not a content root. The finished image is persisted beside the exact curriculum study by Step 7 and copied from there into the MindFeast package. Remove temporary originals after success.

- Preserve the complete artwork; do not crop away any part of it.
- Do not add labels, frames, captions, or generated decoration to the image.
- Choose `portrait` or `landscape` from the artwork's composition and aspect ratio.
- Prefer JPEG for paintings and illustrations unless the best source is natively PNG or WebP.
- Keep the source URL for the delivery report.

### 3. Inspect the artwork

Examine the acquired artwork itself with the default image-understanding capability available in the active environment. Require genuine pixel-level inspection; image dimensions, file metadata, alt text, source-page prose, and search snippets do not satisfy this step. Do not name or directly call a provider when the environment already supplies an image-understanding capability.

Record concise visual notes in the run's research notes:

- the overall composition and focal area
- important figures, objects, gestures, and spatial relationships
- significant uses of color, light, texture, or repeated shapes
- anything uncertain or too indistinct to claim confidently

Keep direct observation separate from interpretation. Use these notes to keep factual references to the artwork accurate, not to direct the child's gaze or supply observations the child can make from the picture. Do not turn them into a guided visual inventory. A visible detail may enter the narration when it meaningfully serves the verified historical or artistic story, but state it neutrally rather than instructing the child to find or notice it. If no available capability can inspect the actual image, stop before research, writing, or audio creation.

### 4. Research the artist and work

Research before writing. Use this source hierarchy:

1. Museum object records, collection catalogues, artist museums, archives, and catalogue raisonnés
2. Scholarly museum essays, universities, national archives, reputable books, and historical societies
3. AO's notes and linked biography
4. Reputable general publications for supplementary context
5. Grokipedia and Wikipedia for discovery only

Before drafting, establish a source gate:

- Require at least one **anchor source** from tiers 1–2 that directly supports the central story or living idea and the important factual claims built around it. `write_study.py` enforces the presence of an anchor and rejects AO, Wikipedia, Grokipedia, and Wikimedia as anchors.
- For an artist-introduction episode, seek a second independent tier-1/2 source: normally one artist or museum source and one archive, scholarly, or historical source. If only one is available after a genuine search, use it and keep unsupported detail out of the narration.
- Build a short claim ledger in the research notes: each specific historical claim intended for the transcript, followed by the source that supports it. Remove any attractive fact or anecdote that cannot be mapped to a sufficiently strong source.
- Use general publications only for details they directly report. Never treat search-result snippets as verification.
- Do not persist discovery pages merely because they were consulted. Persist the principal sources actually relied upon, using descriptive labels rather than `Research source`.

Seek historically truthful, memorable living ideas rather than an inventory of facts. Look for a documented human or artistic thread: a problem the artist faced, how the work arose, a revealing incident, an artistic decision, the historical moment, contemporary reception, or a connection among the term's works.

- Verify attractive anecdotes before using them. Do not repeat legends as facts.
- Distinguish documented fact from interpretation.
- Keep difficult history truthful while making the language suitable for the student's grade.
- Save research notes and the draft transcript in the returned `scratch_dir`. Research notes remain working files; the finished transcript becomes the `## Picture study` section of the curriculum study.

### 5. Write the audio study

Write for the exact `grade` value from `students.yaml`. Use a warm single narrator and a living, story-shaped voice rather than encyclopedia prose or artificial host banter.

- When `introduce_artist` is true, aim for roughly 7–9 minutes and give substantial attention to the artist and artistic world before concentrating on the selected work.
- Otherwise, aim for roughly 5–7 minutes and center the individual work, using only artist details that deepen it.
- Shorten further when the student's developmental level warrants it. Never exceed 10 minutes.
- Estimate duration at about 130–150 spoken words per minute, then verify the produced audio duration when the available tools permit.
- Avoid a repeated biography across the term. Let the six studies build a cumulative acquaintance with the artist.

Use this loose arc:

1. Invite a quiet first look without directing the child's gaze.
2. Tell one central, verified story or living idea about the artist, the work, an artistic problem, or its historical moment.
3. Connect that story to the work as needed for understanding, including its subject, iconography, artistic aims, and well-grounded interpretations, without prescribing a focal point or presenting an interpretation as the child's required conclusion.
4. Leave observations the child can make from the picture for the child to discover.
5. End with one open invitation to look again, wonder, or narrate, then stop.

Historical and biographical context, documented artistic decisions, and a substantial living idea remain welcome; the study should not contain a guided-looking section. Avoid gaze-directing imperatives such as `find`, `notice`, `look at`, and `see`. The rare exception is the minimum orientation needed to identify part of an unusual format, such as a multi-panel work.

Keep the closing invitation genuinely open. Do not follow it with examples of details the child might choose, possible answers, interpretive hints, or a list of things to notice. Trust the child as a complete person to decide what is significant in the work.

### 6. Create audio with available tools

Use the default file-producing text-to-speech capability available in the current environment, including the user's configured provider and voice. Do not name, prefer, or special-case a particular harness, agent, API, provider, model, or voice.

- Render the complete transcript to an audio file in the returned `scratch_dir`.
- Prefer MP3; any MindFeast-supported audio format is acceptable when the available tool produces another format.
- Listen to or otherwise inspect the result when possible for truncation, pronunciation problems, silence, and duration.
- If no available TTS capability can create a local audio file, stop and report the missing capability. Do not build an image-only slide and do not commit the cursor.

### 7. Persist the exact curriculum study

Write the finished study before building the slide. Use the curriculum entrypoint returned by `rotation.py next`; never derive a content root from a student name or grade.

```bash
.venv/bin/python skills/ao-picture-study/scripts/write_study.py \
  --curriculum-entrypoint <resolved-entrypoint> \
  --curriculum-id <resolved-curriculum-id> \
  --artist <artist> \
  --artist-details <artist-details> \
  --title <title> \
  --date <creation-date> \
  --ao-url <ao-url> \
  --image <scratch-artwork-file> \
  --image-source <authoritative-image-url> \
  --transcript <scratch-transcript-file> \
  --anchor-source "<descriptive source label>|<tier-1-or-2-source-url>" \
  --research-source "<descriptive source label>|<supplementary-source-url>"
```

Pass `--anchor-source` at least once and repeat it for each tier-1/2 source actually used. Pass `--research-source` only for additional principal sources. Use human-readable labels such as `Norman Rockwell Museum — Four Freedoms feature` or `National Archives — Powers of Persuasion`; the writer persists those labels in the study. The writer creates one file under `artists/<artist>/<work>.md`, saves the artwork beside it, and links the study from `curriculum.md`. It is idempotent: on a retry it restores missing image/index pieces but reuses an existing matching study instead of overwriting its text. Stop on an identity collision.

The returned `study_path` is the exact file that a later `lesson-log` run records as `lesson.source`; this AO preparation run still does not write the log.

### 8. Build and validate the informational slide

Use `mindfeast-slide-builder` and its scaffold script. Create one `type: informational` package with `subject: painting`, the artwork image, and the narrated audio in the student's configured `tablet_slides_dir`.

The visible text is a compact two-line label, not explanatory prose:

```text
<Artwork title>
<Artist name> · <creation date>
```

Preserve AO or authoritative-source qualifications such as `c. 1775`, `before 1784`, or a date range. Never substitute the lesson date. Pass the two lines as one body block separated by a single newline so MindFeast displays both lines together.

```bash
.venv/bin/python skills/mindfeast-slide-builder/scripts/make_slide.py \
  --out <tablet-slides-dir> \
  --id <suggested-slide-id> \
  --type informational \
  --subject painting \
  --image <persisted-study-image-path> \
  --audio <scratch-audio-file> \
  --difficulty easy \
  --orientation <portrait-or-landscape> \
  --text <two-line-label>

.venv/bin/python skills/mindfeast-slide-builder/scripts/validate_slide.py \
  <tablet-slides-dir>/<suggested-slide-id>
```

Do not continue unless validation succeeds.

### 9. Sync and select this exact slide

Sync once and wait for completion:

```bash
.venv/bin/python skills/mindfeast-slide-sync/scripts/sync.py \
  --student <student-slug-or-name>
```

After a successful sync, select the exact new slide as next without triggering it immediately:

```bash
.venv/bin/python skills/ao-picture-study/scripts/select_slide.py \
  --student <student-slug-or-name> \
  --slide-id <suggested-slide-id>
```

If either operation fails, leave the valid package on disk, report the failure, and do not commit the cursor.

### 10. Commit the last-created cursor and clean scratch

Only after curriculum persistence, slide creation, validation, sync, and exact selection all succeed, commit the target returned by `rotation.py next`:

```bash
.venv/bin/python skills/ao-picture-study/scripts/rotation.py commit \
  --student <student-slug-or-name> \
  --school-year <YYYY-YYYY> \
  --term <1-3> \
  --picture-number <N> \
  --artist <artist> \
  --title <title> \
  --date <creation-date> \
  --ao-url <url> \
  --slide-id <slide-id>
```

After commit, remove only the exact committed run through the validated helper:

```bash
.venv/bin/python skills/ao-picture-study/scripts/rotation.py cleanup \
  --student <student-slug-or-name> \
  --slide-id <slide-id>
```

The helper requires the requested slide id to match the student's committed cursor and removes only that run directory. Never clean AO scratch with `rm`, a shell glob, or an ad-hoc script. Leave the shared root `.scratch/` directory and every other run untouched.

## Delivery

Report:

- Student and grade
- AO school year, term, artist, and picture number
- Artwork title and creation date
- Whether this was the artist-introduction episode
- Audio duration and the TTS voice/provider only when the active tool identifies them
- Slide id and package path
- Curriculum entrypoint, exact study path, and persisted artwork path
- Image source URL
- A concise list of principal research sources
- Validation, sync, selection, cursor-commit, and scratch-cleanup results

Never print credentials or claim sync/selection succeeded without the remote response.
