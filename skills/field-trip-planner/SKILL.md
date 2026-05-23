---
name: field-trip-planner
description: Build a pedagogically grounded field trip plan for a given theme and location. Produces a ranked list of nearby venues (each with a Google Maps link and a website or social page) and a full markdown plan for the chosen option.
argument-hint: <theme + location in prose, optionally referencing lessons> [--auto] [--save PATH]
---

# Field Trip Planner

Produce a field trip plan for a given theme and location, grounded in this project's Charlotte Mason pedagogy wiki at `pedagogy/wiki/`. Every venue mentioned MUST carry a Google Maps link and either a website or a social-media page — no exceptions, no invented URLs.

## Usage

- `/field-trip-planner In our Guatemalan history class, we're studying how the Maya used jade. Let's plan a field trip in the Antigua, Guatemala area, no more than 30 miles from Antigua.`
- `/field-trip-planner We've just finished Math-3 Lessons 40–45 (rounding and estimation). Plan a field trip in the Hyde Park / South Side area of Chicago.`
- `/field-trip-planner Biology lesson on competition and resources. It's winter in Rochester, MN. --auto`

### Flags

- `--auto` — skip the interactive ranked list; take the top-ranked option and produce the full plan directly. Intended for future curriculum-builder integration.
- `--save PATH` — write the final plan to PATH instead of the default location.

## Inputs (parsed from the prompt)

The prompt is free-form prose. Extract:

1. **Theme / topic** (required) — what is being studied, typically as a reference to lessons already covered (e.g. "Math-3 Lessons 40–45", "this week's biology lesson on competition and resources"). If the prompt names a curriculum file under `curricula/`, read the referenced lessons to understand exactly what was covered — those lessons are the pre-trip preparation, not something to be repeated on the trip.
2. **Location** (required) — city, address, neighborhood, or named region. If missing, stop and ask.
3. **Bounds** (optional) — distance or drive-time limits (e.g. "no more than 30 miles", "within 45 minutes"). Respect them exactly.
4. **Season / weather / ages / other context** (optional) — carry through to Logistics or observation prompts as relevant.
5. **Flags** — as listed above.

## Pedagogical framing (applied to every trip, not selectively)

The wiki's pedagogical framework applies to every plan. These are not a menu to choose from by theme — they are the method, applied every time. What varies with the theme is *which relations* the trip opens, not *whether* the framework applies.

- **`concepts/science-of-relations.md`** — Mason's master curricular theory (Principle 12). The child has latent relations to an enormous range of domains — persons, nature, art, country, past, present, mathematics, language, God — and the work of education is to *open* those relations. A field trip is therefore designed around the question *which relations does this trip open?* Every plan answers that question explicitly. The theme determines *which* relations (a trip about the Maya opens relations to past, persons, country, art; a trip about rounding opens relations to mathematics and present); it does not determine whether the concept applies.
- **`concepts/narration.md`** — Mason's single universal method across every subject and every age: the child tells back what was seen/read, without prompts, without leading questions, without interruption. Every trip ends in narration; no trip ends in a worksheet or quiz.
- **`concepts/single-reading.md`** — the rule that pairs with narration: any reading associated with the trip is read attentively once, not drilled.
- **`concepts/living-books.md`** — whenever a book is suggested alongside a trip, it is a living book (first-hand, narrative, author's voice), not a textbook summary. Twaddle cannot be narrated.
- **`concepts/education-is-atmosphere-discipline-life.md`** — the trip *is* the atmosphere. It is not a supplement to the "real" schoolwork; it is the real schoolwork, in the same sense the dinner table is.
- **`concepts/children-are-born-persons.md`** — prompts are written as invitations to a person who is already capable, not drills on a pupil.

Before writing the plan, re-read any of the concept pages whose language you are about to use — the wiki's vocabulary is load-bearing and shouldn't be paraphrased loosely. But don't skip the framework for any trip: every field trip is a Mason-shaped trip under this skill.

### Mason's canonical on-site activities

The wiki does not (yet) have dedicated concept pages for these — they live inside `concepts/science-of-relations.md` and `concepts/knowledge-of-god-man-universe.md`. They are Mason's named, load-bearing practices and should be the default on-site activity wherever the venue admits them:

- **Nature study / field study** — `concepts/knowledge-of-god-man-universe.md` describes it as "field study, nature notebooks, bird lists, plant lists." Close observation of one organism or scene, a dated sketch in a nature notebook, a running list of birds/plants seen. Mason's conviction that children belong out of doors — at length and often — is load-bearing. Outdoor / wild / semi-wild places are not second-best venues; for many themes they are the best venues.
- **Picture study** — `concepts/science-of-relations.md` and `concepts/knowledge-of-god-man-universe.md`: one artist's work examined **in silence** for a set time, then narrated from memory. Directly transferable to any art-museum or gallery trip.
- **Music appreciation** — listening with attention to a single piece or short set, then narrating. Transferable to any concert, live-music, or composer-focused trip.
- **Handicraft observation** — the PUS programme included handicrafts; watching and (where allowed) trying a craft at an artisan's workshop, working farm, or demonstration belongs in this family.

Pick the activity pattern(s) that fit the venue. A nature preserve calls for nature study; an art museum calls for picture study; a concert calls for music appreciation. A mixed venue (e.g. a natural-history museum) may combine several. The chosen pattern should appear explicitly in the "Things to do there" section of the plan.

## Google Maps MCP

The skill depends on the Google Maps MCP server (tool prefix expected to be `mcp__google-maps__`). Before calling any such tool, load it via ToolSearch:

```
ToolSearch(query: "select:mcp__google-maps__maps_geocode,mcp__google-maps__maps_search_places,mcp__google-maps__maps_place_details,mcp__google-maps__maps_directions", max_results: 10)
```

If the MCP is not installed/configured, stop and tell the user to install it and set `GOOGLE_MAPS_API_KEY` first.

If the actual tool names differ (some forks prefix differently), call ToolSearch with a keyword query like `google maps places` to discover them, and use whatever names are returned.

## Workflow

### Step 1 — Parse the prompt

Extract theme, location, bounds, flags, and any extra context. If the theme references a curriculum file or specific lesson numbers (`Math-3`, `Level-3-Language-Arts`, "Lessons 40–45", etc.), read those lessons from wherever `students.yaml` resolves them to, and pull out what was actually covered. Treat that content as **already studied**; the trip should extend, apply, or culminate it, not re-teach it.

**Also extract owning-unit / owning-curriculum context if the prompt supplies it.** When unit-builder or curriculum-builder invokes this skill, the prose prompt names the owning unit (and, if present, curriculum) slug and path. Record both paths — they go into the trip file's frontmatter (`owning_unit`, `owning_curriculum`) and drive the "Part of:" header line, so a teacher opening the trip file can navigate back up to the unit that owns it.

Also read `students.yaml` to identify the student(s) this trip is for. If the prompt names a child, match them by display name or alias. If no child is named, use the grade mentioned in the prompt, or fall back to all students. Record the matched student's `display_name` and `grade` — these inform observation prompt language and the enrichment book buckets in Step 7a. Do not hard-code any student names.

If location is missing, ask and stop.

### Step 2 — Geocode the location

Call `mcp__google-maps__maps_geocode` with the location string. Keep `lat`, `lng`, `formatted_address`, `place_id`.

Convert any stated bound to meters (1 mile = 1609 m). If none was given, use a sensible default radius based on the location type (city: 15 km; small town: 30 km; region: 50 km).

### Step 3 — Search for candidate venues

Brainstorm 5–10 search queries that surface venues opening genuine relations to the theme. Examples:

- "Maya use of jade" → `jade museum`, `mesoamerican archaeology`, `maya museum`, `mercado de jade`, `pre-columbian art`.
- "prairie ecosystems" → `prairie preserve`, `tallgrass prairie`, `nature center`, `native plant garden`.
- "rounding and estimation" → `farmers market`, `hardware store`, `grocery store`, `coin shop` — real-world prices and measurements to estimate against.
- "competition and resources (biology)" → `nature center`, `arboretum`, `zoo`, `aquarium`, `botanical garden`.

Run `mcp__google-maps__maps_search_places` for each query with the geocoded lat/lng and the computed radius. Deduplicate by `place_id`. Keep 8–15 promising candidates.

**Natural places deserve an extra pass.** Mason treats nature study (field study, bird/plant lists, nature notebooks) as first-class curriculum, and for many themes — biology, ecology, earth science, weather, geography, even seasonal literature — an outdoor / wild place is the right venue. Google Maps undercounts these: a trout stream, a public-land ridge trail, a prairie remnant, a birding hotspot, or a free-access fishing pier often doesn't appear as a searchable "place" the way a museum does. When the theme plausibly admits an outdoor venue, supplement the Maps search with a WebSearch pass:

- Terms worth trying: `nature center`, `state park`, `national park`, `wildlife refuge`, `wildlife management area`, `preserve`, `trailhead`, `birding hotspot`, `trout stream`, `public fishing access`, `arboretum`, `conservation area`, plus theme-specific terms (e.g. `glacial erratic`, `native prairie remnant`, `old-growth forest`, `tide pool`).
- Sources worth citing when they surface a venue: state Department of Natural Resources pages, National Park Service pages, eBird hotspots, AllTrails, The Nature Conservancy, local land trusts.
- Any outdoor venue surfaced this way still needs a Google Maps link — geocode the specific trailhead / access point / preserve name via `mcp__google-maps__maps_geocode` to get a valid `place_id` or, failing that, a lat/lng Maps URL (`https://www.google.com/maps/?q=<lat>,<lng>`).
- A website or official managing-agency page (DNR, NPS, land trust, state park service) counts as the "website or social" link for outdoor venues.

### Step 4 — Fetch details

For each candidate, call `mcp__google-maps__maps_place_details` and record:

- `name`, `formatted_address`, `place_id`
- `website`, `international_phone_number`
- `opening_hours` (summary)
- `rating`, `user_ratings_total`
- `types`
- `business_status` — drop `CLOSED_PERMANENTLY`.

Build a Google Maps URL from the `place_id`:
`https://www.google.com/maps/place/?q=place_id:<place_id>`

If `website` is missing, run a WebSearch for `"<name>" <city>` to find an official website OR a clearly official social page (Facebook/Instagram). If neither can be verified, note "no website or social page found" — never fabricate a URL.

**Step 4b — Surface programs and structured activities**

For each shortlisted candidate (after Step 5 narrows the field), do two additional passes:

1. **Mine the reviews** returned by `maps_place_details` for activity signals: tour names, workshop names, class names, durations, whether booking is required, and any pricing mentioned. Reviews often name programs that don't appear in the structured fields (e.g. "short guided tour", "two-hour carving class", "they walked us through the museum first").

2. **Fetch the venue website** (WebFetch on the homepage or an obvious sub-page like `/tours`, `/workshops`, `/programs`, `/activities`). Extract: structured program names, durations, prices, booking URLs, and any programs not mentioned in reviews.

Record a `programs` field summarizing what was found (name, duration, price if known, booking requirement). This feeds directly into "Things to do there" and the Logistics section of the plan — it determines whether advance booking is needed and how long to block on the calendar.

### Step 5 — Rank 3–5 candidates

Rank by the quality of relations each venue would open to the theme — not by star rating. Ratings/reviews are a tiebreaker only. Eliminate candidates that don't open real relations to the theme.

### Step 6 — Print the ranked list

Output to the console in this shape (omit or mark "unknown" any field you can't verify):

```
# Field Trip Options: <theme> near <location>

1. <Venue name> — <one-line pedagogical rationale in terms of relations opened>
   - Maps: <google maps link>
   - Web: <website url>   (or "Social: <url>"  or "no website/social found")
   - Hours: <summary or "unknown">
   - Distance: <miles or "unknown">

2. ...
```

If `--auto` was supplied, skip asking and go straight to Step 7 with rank 1. Otherwise ask the user which option to flesh out.

### Step 7a — Research enrichment materials

Before writing the plan, gather real enrichment candidates. Every title that appears in the plan must come from one of these sources — never from model memory.

**Books — run `scripts/openlibrary/subject_search.py`:**

```bash
.venv/bin/python scripts/openlibrary/subject_search.py "<narrow topic>" --limit 15
```

Run from the project root.

Start with the specific theme (e.g. `"ancient Maya jade"`). If fewer than 5 results come back, run a second pass with a broader query (e.g. `"ancient Maya civilization"`). Deduplicate by title across passes.

The script returns a `type` field for each result: `picture_book`, `chapter_book`, `middle_grade`, `young_adult`, `adult`. Use these to split into two buckets — don't filter by Lexile, and don't add a Lexile annotation. The parent knows the child.

- **Independent reading bucket:** `picture_book` and `chapter_book` results. Pick 2–3 that are most directly on-theme.
- **Read-aloud bucket:** `middle_grade`, `young_adult`, and `adult` results. Pick 1–2 strong narrative (living-book quality) candidates. Avoid reference books, encyclopedias, and committee-written surveys — these cannot be narrated.

If the script returns `no_results` on both passes, note "no results found via Open Library" and leave the books section sparse rather than inventing titles.

**Other enrichment — WebSearch:**

Run 2–3 quick searches for non-book materials:

- Poems: `"<theme>" poem children` — one well-chosen poem can carry a relation as well as a chapter.
- Short readings / articles: `"<theme>" article kids` — look for Nat Geo Kids, Smithsonian Magazine, DK Findout, museum sites.
- Artwork: `"<theme>" artwork painting — a pre-trip picture-study candidate surfaced by the theme.
- Video: `"<theme>" documentary short children` — a 5–15 min clip. Flag as "parent to preview" always.
- Virtual alternative: search for the venue by name + "virtual tour" or "YouTube", and also search `"<theme>" museum virtual tour`. Only include in the plan if a real, working URL is found (venue's own channel, a museum collection page, a vetted short documentary). Do not invent or guess URLs.

Only include items with a real, verifiable URL. If nothing useful surfaces for a category, omit it.

### Step 7 — Build the full plan

For the chosen venue, call `mcp__google-maps__maps_directions` from the stated location to the venue to get drive time/distance.

Print the following markdown to the console. **Also always save it to disk** — use the path from `--save PATH` if supplied, otherwise write to `field-trips/<venue-slug>.md` at the project root (e.g. `field-trips/casa-del-jade.md`). If a file at that path already exists from a prior trip on a different theme, disambiguate by appending the theme: `field-trips/<venue-slug>-<theme-slug>.md` (e.g. `field-trips/casa-del-jade-maya-jade.md`). No dates in trip filenames — trip files are date-portable just like lessons, units, and curricula. Create the `field-trips/` directory if it doesn't exist. Confirm the save path to the user after writing.

```markdown
---
theme: "<theme>"
location: "<city/region>"
venue: "<venue name>"
owning_unit: <relative path to ../curricula/<class>/<unit>/unit.md, or null>          # set when invoked by unit-builder or curriculum-builder
owning_curriculum: <relative path to ../curricula/<class>/curriculum.md, or null>    # set when the owning unit lives under a curriculum
concepts: [science-of-relations, narration, ...]
---

# Field Trip: <Venue Name>

**Theme:** <theme>
**Part of:** [<Unit Name>](<owning_unit path>)<!-- append "· [<Curriculum Name>](<owning_curriculum path>)" when owning_curriculum is not null; omit the whole line when there is no owning unit -->
**Where:** [<venue name>](<google maps link>) · [Website](<url>)  <!-- or social link, or "no website/social found" -->
**Address:** <formatted_address>

## Relations this trip opens

<Name, concretely, which of the relations in `[[concepts/science-of-relations]]` this trip opens — persons, nature, art, country, past, present, mathematics, language, God — and how. 2–3 sentences. This is the plan's pedagogical rationale; it should not read as decoration.>

## Connections

### Prior lessons (what we've already studied)

<List the lessons/topics the user provided in the prompt. Phrase them as already-covered ground that the trip will extend, apply, or culminate — not as things to re-teach. If the prompt didn't reference specific lessons, write a single-line note saying the trip assumes the theme has been touched on in class and omit this subsection.>

### Optional enrichment (possibilities, not requirements)

None of this is required. All titles and URLs come from Step 7a — never from model memory.

#### Books to read aloud
<From Step 7a read-aloud bucket (middle_grade / young_adult / adult). 1–2 titles. For each: author, one sentence on why it opens a relation to the theme, and the type label so the parent can calibrate. Prefer narrative, single-author books over reference works — see `[[concepts/living-books]]`. If the bucket was empty, write "none found via Open Library for this topic.">

#### Books for independent reading
<From Step 7a independent bucket (picture_book / chapter_book). 2–3 titles. For each: author, type label, one sentence on theme relevance. Do not add a Lexile number. If the bucket was empty, write "none found via Open Library for this topic.">

#### Short readings & poems
<From Step 7a WebSearch pass. 0–3 items with title/source and verified URL. Omit this subsection entirely if nothing useful was found.>

#### Artwork
<From Step 7a WebSearch pass. One picture-study candidate — artist name, work title, and a verified URL to a reproduction. Omit if nothing relevant was found.>

#### Video
<From Step 7a WebSearch pass. One short clip (5–15 min) with title, source, and verified URL. Always note: "parent to preview before showing." Omit if nothing useful was found.>

Any reading is read attentively once — see `[[concepts/single-reading]]`. Not drilled, not quizzed.

## On-site

### What to see

<A brief preview of specific exhibits, objects, or areas the venue contains that are relevant to this theme — sourced from Step 4b (venue website and reviews), not invented. 3–5 bullet points. This orients the teacher before they walk in the door. Examples: "jade jewelry and funerary masks," "a working carving station," "lavender jadeite specimens (unique to Guatemala).">

### On the day

A rough phase-by-phase sequence the teacher can follow on site. Time estimates are approximate; adapt to the child's pace.

| Phase | What happens | ~Time |
|---|---|---|
| Arrival & orientation | Locate the entrance, get oriented, let the child take in the space quietly before any directed activity | 10–15 min |
| <phase 2 name> | <what happens> | <estimate> |
| <phase 3 name — core activity> | <what happens> | <estimate> |
| Wrap-up | Leave the venue; brief quiet walk or ride home before narration — let impressions settle | 10–15 min |

### Observation prompts

<If the prompt named a child or age range, split into age-appropriate lists. Otherwise write prompts for a mid-elementary reader and note that younger/older differentiation is available on request. Prompts are invitations to notice, not questions with right answers — see `[[concepts/children-are-born-persons]]`.>

- <prompt 1>
- <prompt 2>
- <prompt 3>

### Things to bring

- <Only what the activity actually uses. Defaults:>
  - Outdoor / nature trip: **nature notebook**, pencil, hand lens, field guide (birds / plants / rocks / whatever the theme calls for), water/snacks if away from amenities.
  - Art museum / gallery: sketchbook, pencil (pens are typically not allowed near artworks).
  - Concert / music venue: nothing required; optionally a small notebook for post-concert narration.
  - Historic site / working farm / workshop: notebook for narration; any venue-specific items noted on their website.

### Things to do there

The four Mason activity patterns below are **defaults, not a closed list.** Where one fits the venue, use it and name it — it gives the trip a pedagogically grounded backbone. Feel free to propose a venue-specific activity instead of, or alongside, a canonical pattern when the place invites something distinctive. A non-canonical activity is still Mason-faithful if it rests on first-hand experience, sustained attention, and post-activity narration — not on a right-answer quiz or a scavenger hunt. Use judgement.

Mason's canonical patterns:

- **Nature study** (outdoor / natural-history venues): pick one organism or scene; observe in silence for several minutes; sketch and date the entry in a nature notebook; start or add to a running bird / plant / specimen list. See `concepts/knowledge-of-god-man-universe.md`.
- **Picture study** (art museum / gallery): pick one or two works; look at each in silence for a set time (3–5 minutes); then step away and narrate from memory what was seen. See `concepts/science-of-relations.md`.
- **Music appreciation** (concert / music venue): listen attentively to a single piece or short set, without talking or device use; narrate afterwards. See `concepts/science-of-relations.md`.
- **Handicraft observation** (artisan workshop / working farm / demonstration): watch the craftsperson work; if permitted, try a small part of the process; narrate the sequence afterwards.

## Post-trip

- **Narration:** each child tells back what they saw and thought about, without prompts or leading questions — see `[[concepts/narration]]`. This is the assessment.
- **Feeding forward:** what came up during narration can seed the next lesson — note 1–2 threads the trip might open up for future study. (Coordinating trips and lessons more tightly is the job of a future curriculum-builder skill; here we just flag the threads.)

## Logistics

- **Hours:** <from place details, or "call ahead / check website">
- **Cost:** <only if verified from the website or place details; otherwise "unknown — check website">
- **Programs / tours:** <from Step 4b: list each program with name, duration, price if known, and whether advance booking is required. If nothing structured was found, omit this line.>
- **Drive from <location>:** <from Maps directions: "X miles · Y min">
- **Total time:** <rough total: prep + travel + on-site + wrap-up; e.g. "~3–4 hrs">
- **Season/weather note:** <only if the prompt raised it>
- **Virtual alternative:** <only if Step 7a found a real, verifiable URL — e.g. a venue video tour, the venue's own YouTube channel, or a museum collection page directly relevant to the theme. Format: "[Title](url) — one sentence on what it covers." If nothing was found, omit this line entirely.>
```

## Rules (hard)

- **Links are mandatory.** Every venue named in the plan must have a Google Maps link (named place ID preferred; lat/lng `https://www.google.com/maps/?q=<lat>,<lng>` is acceptable for unsearchable outdoor locations). Every venue must also have a website or a social-media page — for outdoor venues, the managing agency's page (state DNR, NPS, land trust, etc.) counts. If neither a website nor a social/agency page exists, say so explicitly — never fabricate.
- **Outdoor venues are first-class.** Do not bias toward indoor, for-profit, or heavily-reviewed venues. Trout streams, prairie remnants, trailheads, birding hotspots, and public fishing access points are valid field-trip destinations when the theme admits them. Supplement Google Maps with WebSearch for this category.
- **Every activity must be Mason-faithful, but not necessarily canonical.** The four named patterns (nature study, picture study, music appreciation, handicraft observation) are defaults — use them when they fit the venue. A venue-specific creative activity is equally welcome, provided it rests on first-hand experience, sustained attention, and post-activity narration. What's not acceptable is a generic "walk around and look" or a right-answer scavenger hunt.
- **No hallucinated facts.** Hours, prices, addresses, and book titles come from the MCP, a verified website, or a source you can cite. If you don't know, write "unknown" — do not guess.
- **Respect bounds.** A stated radius or drive-time limit is a hard filter, not a suggestion.
- **Treat prior lessons as done.** When the prompt references lessons already studied, the trip extends them; it does not re-teach them. Additional readings/books are presented as optional enrichment.
- **Pedagogical framework is applied every time.** Science of relations, narration, single reading, and living books are not a menu to pick from by theme. Every trip opens relations; every trip ends in narration; any reading is single-reading of a living book.
- **No Wikipedia.** Wikipedia is not a citation source for this skill's enrichment lists. Books go through Open Library; short encyclopedic articles come from sources the user names (e.g. Grokipedia) or are left out. Every citation already needs a verifiable URL; Wikipedia doesn't qualify.
- **Back-link to the owning unit when invoked by unit-builder or curriculum-builder.** Set `owning_unit` and (if applicable) `owning_curriculum` in frontmatter. Render the "Part of: [<Unit>](<path>)" header line in the body. A trip file generated inside a unit context must be navigable from the unit's `unit.md` down, and from the trip file back up. When invoked standalone (a loose `/field-trip-planner` command with no parent context), both fields are null and the "Part of:" line is omitted.
- **No calendar-anchor dates anywhere — including in trip filenames or frontmatter.** Trip files are date-portable just like lessons, units, and curricula. The same trip should be reusable next year without renaming. Filenames are `<venue-slug>.md` (or `<venue-slug>-<theme-slug>.md` when a venue is used twice on different themes). Venue opening hours pulled from Google Maps render exactly as returned (e.g. "Tue–Sun 9am–5pm") in the Logistics section, and time-of-day qualifiers (morning, afternoon, evening, dusk, dawn) are fine when the activity genuinely depends on them — those are not calendar anchors.
