---
name: ao-composer-study
description: Prepare and archive the next AmblesideOnline composer study for a configured student, including the scheduled musical work, an exact reusable curriculum study, a primary informational MindFeast listening slide with the real recording, and a secondary informational podcast slide with a short narrated study. Use when the user asks for the next AO composer study, AO music study, Ambleside composer-study slides, or an AO composer podcast.
---

# AO Composer Study

Prepare one complete composer-study presentation from AmblesideOnline's current rotation. Music is the primary encounter: create and select the listening slide first in importance, while treating the narrated study as a secondary companion. Track what this workflow delivered, never what was taught; do not read or write lesson logs.

## Student and output

Read `students.yaml` at runtime and resolve the student by slug, `display_name`, or `aliases`. Require:

- `grade`
- `curricula_dir` and a curriculum whose id or alias is `ao-composer-study`
- `tablet_slides_dir`
- `mindfeast.remote_url` and `mindfeast.remote_token`

Never hard-code students, grades, paths, remote URLs, or tokens. Stop before media creation if a required field is absent, and never print the token.

## Workflow

Keep the run noninteractive and safe for cron. Use installed dependencies and the active environment's normal file-producing image and TTS capabilities. Never install software, invoke `sudo`, request a password, launch an interactive program, or alter runtime configuration during a study run. If a capability is unavailable, stop and report it.

### 1. Resolve the next presentation

From the repository root, run:

```bash
.venv/bin/python skills/ao-composer-study/scripts/rotation.py next \
  --student <student>
```

The helper fetches `https://www.amblesideonline.org/composers`, parses AO's numbered selections, resolves the configured curriculum, and reads only this student's delivery cursor under `.state/ao-composer-study/`. It returns the exact work, AO recording links, scratch directory, curriculum study path, two slide ids, and whether this presentation repeats a long selection.

- With no cursor, start at the first selection in the current or next published term.
- Otherwise advance after the last successfully delivered presentation.
- Honor AO's combined numbers and four-week instructions. A selection occupying two AO slots has `presentation_count: 2`.
- On presentation 2, reuse the existing study and slide packages. Revalidate and resync both, reselect the primary work slide, and commit the repeated presentation. Do not regenerate the podcast, images, recording, or curriculum file.
- When AO lists alternatives, use the first recording before `OR`; try later URLs only when the primary fails.
- For an explicit starting point, pass `--school-year`, `--term`, `--selection-number`, and optionally `--presentation`.
- If AO's page cannot be parsed confidently, stop instead of guessing.

An existing matching study or slide folder with an earlier cursor is a resumable partial run. Reuse established content, repair missing media when the persisted sources permit it, and continue from validation. Never replace established prose merely because a prior run stopped late.

### 2. Acquire the real musical work

Acquire the actual AO-selected recording, never generated music.

1. Prefer a suitable public-domain or explicitly reusable recording when one is readily available and clearly matches AO's specified work, movement, arrangement, or excerpt.
2. Otherwise use AO's primary recording URL. For YouTube and other supported pages, run:

```bash
.venv/bin/python skills/ao-composer-study/scripts/download_audio.py \
  --url <recording-url> \
  --output-dir <scratch-dir> \
  --stem work-recording
```

3. If acquisition fails, try AO's alternate recording URLs in page order. Stop if none succeeds.

The checked-in helper uses the shared `yt-dlp` dependency and `ffmpeg`, extracts audio only, ignores user-level downloader configuration, and returns source/performance metadata as JSON. Keep the returned source URL, title, performer/uploader, and duration. This use is for the family's private study package: never publish, redistribute, or commit downloaded recordings. Keep working downloads in the returned scratch directory; Step 7 persists the selected recording only in the gitignored curriculum tree.

Check that the recording is audible, substantially complete for AO's selection, and not obviously mislabeled. Do not silently substitute a different movement or abridgment.

### 3. Research the composer and work

Research before writing, using this hierarchy:

1. Composer foundations, thematic catalogues, manuscript archives, national libraries, and authoritative institutional collections
2. Orchestra, opera house, museum, university, conservatory, scholarly-edition, and reputable music-history sources
3. AO's notes and linked biographies
4. Reputable general publications for supplementary context
5. Wikipedia, Grokipedia, video descriptions, and search snippets for discovery only

Require at least one tier-1/2 anchor source supporting the central story and important claims. For a composer's first episode in the term, seek a second independent institutional or scholarly source. Build a short claim ledger in scratch and remove anecdotes or interpretations that lack adequate support. `write_study.py` rejects AO, Wikipedia, Grokipedia, Wikimedia, and YouTube as anchor sources.

Search is only for discovering candidate URLs. After choosing sources, open and read every principal source through the active environment's browser/page-reading capability before writing the claim ledger. A search snippet, URL, extraction error, or response from a search-only backend is not evidence. Do not discard a stronger source merely because the first reader cannot extract it: retry through another available noninteractive page-reading method. When generic HTTPS retrieval is necessary, save the response to scratch as data and inspect or convert it in a separate command. Never pipe a network response into a shell or interpreter, and never use a retrieval method that requires interactive approval. Replace a source only when it remains genuinely inaccessible after safe retrieval attempts. Stop before drafting when the required anchors have not actually been retrieved.

Seek a living human or artistic thread: the circumstances of composition, a musical or practical problem, the composer's world, the work's subject or text, a documented artistic aim, reception, or a connection among the term's works. Biblical, literary, dramatic, historical, and liturgical meaning is welcome when it truly belongs to the work. Distinguish documented fact from interpretation.

### 4. Write the secondary audio study

Write for the exact configured grade in a warm single-narrator, story-shaped voice.

- When `introduce_composer` is true, aim for roughly 5–7 minutes and establish the composer and artistic world before concentrating on the work.
- Otherwise aim for roughly 2–4 minutes and center the individual selection. Shorten further for a younger child; never exceed 7 minutes.
- Avoid repeating the same biography. Let the term's studies build cumulative acquaintance.
- Estimate 130–150 spoken words per minute and verify the rendered duration when possible.

Tell one verified story or living idea and connect it to the work as needed. Discuss form, subject, text, instrumentation, compositional choices, or historical meaning when those facts serve understanding. It is appropriate to explain that an Impressionist sought an effect unlike photographic realism, or that a sacred work tells a biblical story.

Do not turn the podcast into a guided-listening inventory or place an adult mediator between child and music. Avoid prescribing what the child must hear, imagine, feel, or conclude. Do not announce a sequence of cues to hunt for, including `listen for`. State verified movement names, forms, subjects, or meanings neutrally. End with a simple open invitation to listen, remember, or narrate, without supplying possible answers.

Before calling TTS, complete a transcript preflight: count the words, estimate the spoken duration at 130–150 words per minute, verify every substantive claim against the claim ledger, and reread the closing invitation. Revise the transcript before audio generation when it misses the target duration, contains an unsupported claim, prescribes the child's response, or supplies examples of what the child might remember or narrate. Generate TTS only after this preflight passes.

### 5. Create the two generated images

Generate two distinct full-bleed images through the configured Charlotte image router on its quality route. The capability order is mandatory: when the runtime exposes a file-producing image capability that explicitly identifies itself as Charlotte-backed, call it directly for both images and do not probe or attempt `scripts/charlotte_image.py` first. Invoke that script only when no such runtime-native capability exists. Runtime-managed image caches are valid working locations; the writer persists the returned files beside the study.

Require each result to report `route: quality`, the source and model configured for that route, and `prompt_mode: full`. Never call a provider directly, write an ad-hoc HTTP request, or try an unrelated image tool after the configured route fails. Stop before persistence, slide creation, sync, selection, and cursor commit if either image fails these checks.

- **Work image:** an understated visual grounded in the work's period, subject, setting, or artistic world. It may convey verified programmatic, literary, biblical, or historical subject matter, but must not dictate a single private mental image for abstract music.
- **Podcast image:** a visual grounded in the composer and the episode's verified living story.

Neither image contains text, musical notation, notation labels, UI, or explanatory callouts. Use the active pedagogy's configured visual register without invoking print-material skills. Choose slide orientation from the generated composition.

Inspect the actual pixels of both generated images through the active environment's image-understanding capability before persistence. Reject and regenerate an image through the same configured Charlotte route if it contains forbidden text, notation, or UI; conflicts with the requested subject or composition; introduces an obvious factual anachronism; or fails to leave usable space for the compact slide label. Correct only the failed content or composition constraint in the retry prompt; do not add aesthetic direction.

### 6. Create podcast audio

Render the complete transcript with the default file-producing TTS capability available in the active environment, using its configured provider and voice. Save it in scratch, prefer MP3, and convert a successfully returned lossless or Ogg-family file to MP3 with `ffmpeg` when the persisted study needs MP3. Check for silence, truncation, severe pronunciation errors, and duration. Do not name or special-case a harness or provider. If local audio cannot be produced, stop without creating incomplete slides or advancing the cursor.

### 7. Persist the reusable study

Use the entrypoint returned in Step 1:

```bash
.venv/bin/python skills/ao-composer-study/scripts/write_study.py \
  --curriculum-entrypoint <entrypoint> \
  --curriculum-id <id> \
  --composer <composer> \
  --composer-details <details> \
  --title <AO-title> \
  --ao-url <AO-url> \
  --presentation-count <count> \
  --work-audio <downloaded-recording> \
  --work-image <generated-work-image> \
  --podcast-audio <tts-audio> \
  --podcast-image <generated-podcast-image> \
  --transcript <transcript-file> \
  --recording-source <recording-source-url> \
  --recording-title <recording-title> \
  --recording-performer <performer-or-uploader> \
  --recording-duration <seconds> \
  --anchor-source "<descriptive-label>|<tier-1-or-2-url>" \
  --research-source "<descriptive-label>|<supplementary-url>"
```

Repeat source flags as needed. The writer creates `composers/<composer>/<work>.md`, copies all four media files beside it, and idempotently links it from `curriculum.md`. It restores missing media/index pieces on retry but never overwrites a matching existing study, and stops on an identity collision. Its returned media paths are the sources for both slide packages. A later lesson log may cite the exact `study_path`; this workflow itself does not log a lesson.

### 8. Build and validate both slides

Use `mindfeast-slide-builder` to create two `type: informational`, `subject: composer` packages under the configured `tablet_slides_dir`.

The **primary work slide** uses the persisted work image and actual recording. Its visible text contains only:

```text
<AO work title>
<Composer name>
```

The **secondary podcast slide** uses the persisted podcast image and narration. Give it the same compact two-line label; do not add questions or explanatory slide text.

```bash
.venv/bin/python skills/mindfeast-slide-builder/scripts/make_slide.py \
  --out <tablet-slides-dir> --id <suggested-work-slide-id> \
  --type informational --subject composer \
  --image <persisted-work-image> --audio <persisted-work-audio> \
  --difficulty easy --orientation <orientation> --text <two-line-label>

.venv/bin/python skills/mindfeast-slide-builder/scripts/make_slide.py \
  --out <tablet-slides-dir> --id <suggested-podcast-slide-id> \
  --type informational --subject composer \
  --image <persisted-podcast-image> --audio <persisted-podcast-audio> \
  --difficulty easy --orientation <orientation> --text <two-line-label>
```

Validate each exact package with `skills/mindfeast-slide-builder/scripts/validate_slide.py`. Do not continue unless both pass.

### 9. Sync and select the primary slide

Sync once with `skills/mindfeast-slide-sync/scripts/sync.py --student <student>`. After success, select only the exact work slide:

```bash
.venv/bin/python skills/ao-composer-study/scripts/select_slide.py \
  --student <student> \
  --slide-id <suggested-work-slide-id>
```

Do not select the podcast slide and do not trigger either slide immediately. On any remote failure, leave valid packages on disk for retry and do not advance the cursor.

### 10. Commit and clean scratch

Only after persistence, both validations, sync, and primary selection succeed, commit every target field returned by Step 1:

```bash
.venv/bin/python skills/ao-composer-study/scripts/rotation.py commit \
  --student <student> --school-year <YYYY-YYYY> --term <1-3> \
  --composer <composer> --selection-number <N> \
  --slot-number <N> --title <title> \
  --presentation <N> --presentation-count <N> \
  --ao-url <url> --scratch-id <scratch-id> \
  --work-slide-id <work-slide-id> --podcast-slide-id <podcast-slide-id>
```

Repeat `--slot-number` for combined entries. Then clean only the committed run with:

```bash
.venv/bin/python skills/ao-composer-study/scripts/rotation.py cleanup \
  --student <student> --scratch-id <scratch-id>
```

Never delete AO scratch with `rm`, a glob, or an ad-hoc script.

## Delivery

Report the student/grade, AO year/term/composer/selection, presentation number and whether it was reused, recording title/performer/source/duration, podcast duration, both slide ids and paths, exact curriculum study and media paths, principal research sources, and validation/sync/selection/cursor/cleanup results. Never expose credentials or claim remote success without the response.
