# Wiki Log

Append-only chronological record of all activity. Each entry starts with `## [YYYY-MM-DD] type | description` for easy grep parsing.

```bash
# Last 5 entries:
grep "^## \[" wiki/log.md | tail -5
```

---

## [2026-04-18] init | Wiki initialized

Created full vault structure: directories, CLAUDE.md schema, templates, index, log, overview.

## [2026-04-18] ingest | LLM Wiki (Andrej Karpathy)

**Source:** `raw/karpathy-llm-wiki.md`  
**Pages created:**
- `wiki/sources/karpathy-llm-wiki.md`
- `wiki/concepts/llm-wiki-pattern.md`
- `wiki/concepts/rag-vs-wiki.md`
- `wiki/entities/andrej-karpathy.md`
- `wiki/entities/vannevar-bush.md`

**Pages updated:**
- `wiki/index.md`
- `wiki/overview.md`
- `wiki/log.md`

**Notes:** Foundational source — describes the pattern this wiki implements. Meta-ingest establishing the system before any pedagogy content is added.

## [2026-04-18] ingest | Charlotte Mason — _Towards a Philosophy of Education_, Book I

**Source:** `raw/An-Essay-Towards-a-Philosophy-of-Education.txt` (Book I section; originally ingested from a temporary split file)
**Pages created:**
- `wiki/sources/towards-a-philosophy-of-education-book-1.md`
- `wiki/entities/charlotte-mason.md`
- `wiki/entities/pneu.md`
- `wiki/entities/parents-union-school.md`
- `wiki/entities/house-of-education.md`
- `wiki/concepts/20-principles-of-education.md`
- `wiki/concepts/children-are-born-persons.md`
- `wiki/concepts/education-is-atmosphere-discipline-life.md`
- `wiki/concepts/science-of-relations.md`
- `wiki/concepts/narration.md`
- `wiki/concepts/single-reading.md`
- `wiki/concepts/living-books.md`
- `wiki/concepts/way-of-the-will.md`
- `wiki/concepts/knowledge-of-god-man-universe.md`

**Pages updated:**
- `wiki/index.md`
- `wiki/overview.md`
- `wiki/log.md`

**Notes:** First substantive pedagogy source. Establishes Charlotte Mason as a hub entity and seeds the conceptual spine (20 Principles, narration, single reading, living books, science of relations, way of the will, knowledge of God/Man/Universe). Book II of the same 1923 volume ("Theory Applied") is the natural next ingest. Further candidate entity pages not created in this pass but worth writing later if a second source cites them: Henri Bergson, Karl Marx, H. A. L. Fisher, H. W. Household, Plutarch, N. F. S. Grundtvig, Comenius.

## [2026-04-18] ingest | Charlotte Mason — _Towards a Philosophy of Education_, Book II

**Source:** `raw/An-Essay-Towards-a-Philosophy-of-Education.txt` (Book II section, "Theory Applied"; originally ingested from a temporary split file)
**Pages created:**
- `wiki/sources/towards-a-philosophy-of-education-book-2.md`
- `wiki/entities/nfs-grundtvig.md`
- `wiki/entities/plutarch.md`
- `wiki/entities/comenius.md`
- `wiki/entities/matthew-arnold.md`
- `wiki/concepts/liberal-education-for-all.md`
- `wiki/concepts/act-of-knowing.md`
- `wiki/concepts/knowledge-as-food.md`
- `wiki/concepts/too-wide-a-mesh.md`

**Pages updated (source list + Mentioned In):**
- `wiki/entities/charlotte-mason.md`
- `wiki/entities/pneu.md`
- `wiki/entities/parents-union-school.md`
- `wiki/entities/house-of-education.md`
- `wiki/concepts/20-principles-of-education.md`
- `wiki/concepts/children-are-born-persons.md`
- `wiki/concepts/education-is-atmosphere-discipline-life.md`
- `wiki/concepts/science-of-relations.md`
- `wiki/concepts/knowledge-of-god-man-universe.md`
- `wiki/concepts/narration.md`
- `wiki/concepts/single-reading.md`
- `wiki/concepts/living-books.md`
- `wiki/concepts/way-of-the-will.md`
- `wiki/index.md`
- `wiki/overview.md`

**Notes:** Second half of Mason's 1923 valedictory. Shifts the corpus from single-volume to single-author-two-volume. Book II adds a social-political dimension (liberal-education-for-all, Danish vs. Munich Continuation-School models) and an explicit epistemology (the "act of knowing" that narration reveals). Four new entity pages named from Book II cite both Books I and II where appropriate; thirteen existing pages were retrofitted with Book II as an additional source and a new "Mentioned In" line. Overview rewritten to acknowledge Book II's extension and to separate the "Book I skeleton" from the "Book II social dimension." Still no independent (non-Mason) pedagogy source in the wiki; that remains the next natural direction. Further candidate entity pages not created in this pass but worth writing later: Dr. Georg Kerschensteiner (the antithesis in Ch. III), Dr. Thomas Arnold of Rugby, H. A. L. Fisher, Rudolf Eucken, H. W. Household.

## [2026-04-18] lint | Full-wiki link and orphan scan

**Scope:** Walked all 42 pages; extracted every `[[...]]` wiki-link; cross-checked against the page inventory; computed inbound-link counts.

**Findings:**
- **2 broken links found and fixed.**
  - `wiki/concepts/act-of-knowing.md:19` linked to `entities/henri-bergson` (wiki-link syntax); Bergson has no entity page. De-linked to plain-text "Bergson." Bergson remains a candidate entity page (already noted in the Book I log entry).
  - `wiki/sources/karpathy-llm-wiki.md:52` linked to `concepts/knowledge-base-maintenance` (wiki-link syntax); no such concept page exists. Converted to plain-text bullet with a pointer to the existing [[concepts/llm-wiki-pattern]] page, which already covers the idea.
- **0 orphan pages.** Every non-meta page has at least one inbound link.
- **Missing-page candidates (not fixed).** Entities mentioned in text but without pages: Henri Bergson, Kerschensteiner, H. W. Household, Karl Marx, Herbart, H. A. L. Fisher, Rudolf Eucken, Thomas Arnold of Rugby. The Book I and Book II ingest notes already flag these as candidates; none currently warrant a page on the strength of a single cite, but any second ingest that leans on one of them should trigger a page.

## [2026-05-16] ingest | Charlotte Mason — _Home Education_

**Source:** `raw/Home-Education.txt` (Project Gutenberg eBook #71087, set from the 1906 fifth edition; the greater part first delivered as "Lectures to Ladies" in 1885 and published in 1886). This is **Volume I** of Mason's six-volume _Home Education Series_; the wiki's earlier Mason source, _Towards a Philosophy of Education_, is **Volume VI** of the same series.

**Pages created:**
- `wiki/sources/home-education.md`
- `wiki/concepts/habit-formation.md`
- `wiki/concepts/habit-of-attention.md`
- `wiki/concepts/nature-study.md`
- `wiki/concepts/masterly-inactivity.md`
- `wiki/concepts/method-vs-system.md`
- `wiki/entities/friedrich-froebel.md`
- `wiki/entities/william-carpenter.md`
- `wiki/entities/johann-herbart.md`

**Pages updated** (source list + "Mentioned In", with body edits where the source changes or originates the picture):
- `wiki/concepts/20-principles-of-education.md` — records the **eighteen-point** precursor synopsis
- `wiki/concepts/children-are-born-persons.md`
- `wiki/concepts/education-is-atmosphere-discipline-life.md`
- `wiki/concepts/science-of-relations.md`
- `wiki/concepts/narration.md`
- `wiki/concepts/single-reading.md`
- `wiki/concepts/living-books.md`
- `wiki/concepts/way-of-the-will.md`
- `wiki/concepts/knowledge-as-food.md`
- `wiki/concepts/phonics-and-literature-spelling.md`
- `wiki/concepts/developmental-writing-pedagogy.md`
- `wiki/entities/charlotte-mason.md`
- `wiki/entities/pneu.md`
- `wiki/entities/parents-union-school.md`
- `wiki/entities/house-of-education.md`
- `wiki/entities/plutarch.md`
- `wiki/index.md` (page counts 33 → 42; one source row, five concept rows, three entity rows)
- `wiki/overview.md`
- `wiki/log.md` (this entry)

**Notes:** The first Mason volume in the wiki earlier than the 1923 valedictory. The corpus shifts from "single-author, two-volume" to a single author across nearly four decades — Volume I (1885 lectures / 1886 / 1906 fifth edition) and Volume VI (1923) of one series.

The load-bearing finding is that the **conceptual spine predates the synthesis**. Children are born persons, narration after a single reading of living books, the science of relations, the Way of the Will, the triad of atmosphere/discipline/life, the formation of habit — all are present in 1906, and behind it in the 1885 lectures. The 1923 books refined and systematised; they did not originate. Eleven concept and entity pages previously sourced only to the 1923 volumes were therefore retrofitted with _Home Education_ as the earlier source, and several were re-titled in their "Mentioned In" sections to read chronologically (Home Education first).

A specific sub-finding, recorded on the [[concepts/20-principles-of-education]] page: the 1906 edition's prefatory synopsis has **eighteen** numbered points, not twenty. It is recognisably the same creed but is differently ordered, more openly polemical against [[entities/johann-herbart|Herbart]], and ends differently. The "20 Principles" count belongs to the final form, not to Mason's thought as a whole — a small correction to a document that circulates in the homeschool world as fixed and timeless.

Five new concept pages capture doctrines _Home Education_ carries that the 1923-sourced pages did not: [[concepts/habit-formation]] ("Habit is ten natures" — the central practical doctrine, with its Victorian brain physiology), [[concepts/habit-of-attention]], [[concepts/nature-study]] (out-of-door life — directly relevant to the homeschool-hub nature-notebook materials), [[concepts/masterly-inactivity]], and [[concepts/method-vs-system]]. Three new entity pages were triggered by substantive engagement, not passing mention: [[entities/friedrich-froebel|Froebel]] (honoured predecessor, critiqued system — two chapters), [[entities/william-carpenter|Carpenter]] (his _Mental Physiology_ is the cited source of the habit doctrine), and [[entities/johann-herbart|Herbart]] (the named theoretical antithesis of synopsis points 9–11). Froebel and Herbart had been flagged as candidates by the earlier ingest logs.

_Home Education_ grounds two language-arts concept pages in Mason's own method: [[concepts/phonics-and-literature-spelling]] records spelling as the visualising of words plus prepared dictation, and [[concepts/developmental-writing-pedagogy]] records "composition comes by nature" through narration before formal composition.

Deliberate scope choices: no separate concept page was created for **conscience**, although Part VI treats it at length; the material is folded into the [[concepts/way-of-the-will]] page's "Mentioned In" and into the source page. [[concepts/knowledge-of-god-man-universe]] was **not** retrofitted — _Home Education_ predates Mason's formalised threefold curriculum and the connection was judged too loose to source.

Candidate future ingests: the four middle volumes of the series remain un-ingested — _Parents and Children_ (II), _School Education_ (III), _Ourselves_ (IV), and _Some Studies in the Formation of Character_ (V). _School Education_ in particular carries the full chapter-length treatment of "masterly inactivity" and would close a flagged gap.

## [2026-05-16] query | The under-nine years (the scope of _Home Education_)

**Question:** What does _Home Education_ mean by the "under-nine years," and how does Charlotte Mason structure the education of that period?

**Filed:** `wiki/queries/2026-05-16-the-under-nine-years.md` — the wiki's first query page.

**Pages updated:**
- `wiki/index.md` (page count 42 → 43; Queries section now holds one entry)
- `wiki/log.md` (this entry)

**Notes:** Synthesised from the same-day _Home Education_ ingest. The "under-nine years" is the whole scope of the book — education from infancy to nine, worked in two phases: birth-to-six, a "quiet growing time" of out-of-door life and habit with no formal lessons; six-to-nine, short varied lessons, reading, and the beginning of narration. The page cites the source plus the [[concepts/nature-study]], [[concepts/habit-formation]], [[concepts/habit-of-attention]], and [[concepts/masterly-inactivity]] concept pages, and notes that this block corresponds to Form I of the later [[entities/parents-union-school|PUS]] scheme.

## [2026-05-16] query | Charlotte Mason's copywork technique

**Question:** How did Charlotte Mason apply copywork, and what exact technique did she use?

**Filed:** `wiki/queries/2026-05-16-charlotte-mason-copywork-technique.md`.

**Pages updated:**
- `wiki/index.md` (page count 43 → 44; Queries section now holds two entries)
- `wiki/log.md` (this entry)

**Notes:** Synthesised from the same-day _Home Education_ ingest and the language-arts concept pages. The query records Mason's "transcription" method: short, beautiful copywork; word-by-word visualisation before writing; one perfect line rather than volume; and the connection between copywork, spelling, attention, prepared dictation, and the broader [[concepts/developmental-writing-pedagogy|narration-before-composition]] sequence.

## [2026-05-22] lint | Cleanup pass after wiki lint

**Scope:** Follow-up cleanup from the 2026-05-22 wiki lint: fixed stale page-count notes, added contextual inbound links for query pages, and checked that the index, frontmatter, filenames, source paths, `Mentioned In` sections, and wikilinks remain consistent.

**Findings:**
- **0 broken links.**
- **0 hard orphan pages.**
- **2 contextual query orphans fixed.** Linked the under-nine query from [[concepts/nature-study]] and the copywork query from [[concepts/phonics-and-literature-spelling]] and [[concepts/developmental-writing-pedagogy]].
- **1 missing log entry fixed.** Added the 2026-05-16 copywork query entry that was present in the index but absent from this log.

## [2026-07-18] maintenance | Restore complete Philosophy of Education source

Replaced the two temporary Book I and Book II raw-file splits with the complete
official Project Gutenberg plain-text eBook #66369. A normalized comparison
confirmed that the split files contained the same text except for four blank
lines omitted at the Book I/Book II boundary.

The two existing sectional source summaries and all of their wiki slugs were
preserved. Both now point to
`raw/An-Essay-Towards-a-Philosophy-of-Education.txt` and declare their
respective Book I or Book II scope. No page count or cross-reference changed.
