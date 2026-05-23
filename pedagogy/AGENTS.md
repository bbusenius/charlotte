# Pedagogy Wiki — Schema & LLM Instructions

This is a personal knowledge base about pedagogy, homeschooling, and educational theory. The LLM maintains all wiki files; the human curates sources and asks questions.

## Directory Structure

```
raw/            # Immutable source documents — never modify
raw/assets/     # Downloaded images referenced by sources
wiki/           # LLM-maintained knowledge base
wiki/index.md   # Master catalog of all wiki pages
wiki/log.md     # Append-only chronological activity log
wiki/overview.md# High-level synthesis of the whole wiki
wiki/entities/  # People, organizations, curricula, books (proper nouns)
wiki/concepts/  # Theories, methods, ideas, frameworks
wiki/sources/   # One summary page per ingested source
wiki/queries/   # Filed answers to notable questions
templates/      # Reference templates (do not modify)
```

## Page Types & Frontmatter

### Source Summary (`wiki/sources/`)
Filename: `slug-of-title.md`
```yaml
---
title: "Full Title"
author: "Author Name(s)"
year: YYYY
type: article | book | paper | podcast | video | gist | other
tags: [tag1, tag2]
source_path: "raw/filename.md"
date_ingested: YYYY-MM-DD
---
```

### Entity Page (`wiki/entities/`)
Filename: `entity-name.md` (lowercase, hyphens)
```yaml
---
name: "Entity Name"
type: person | organization | curriculum | program | book-series
tags: [tag1, tag2]
sources: [source-slug1, source-slug2]
---
```

### Concept Page (`wiki/concepts/`)
Filename: `concept-name.md`
```yaml
---
name: "Concept Name"
tags: [tag1, tag2]
sources: [source-slug1, source-slug2]
---
```

### Query Answer (`wiki/queries/`)
Filename: `YYYY-MM-DD-short-question.md`
```yaml
---
question: "Full question text"
date: YYYY-MM-DD
tags: [tag1, tag2]
sources_cited: [page-link1, page-link2]
---
```

## Workflows

### Ingest a New Source

1. Confirm the source file exists in `raw/`
2. Read the source thoroughly
3. **Discuss** key takeaways with the user if they want interaction; otherwise proceed
4. Create `wiki/sources/<slug>.md` — a comprehensive summary with:
   - Abstract/overview (2–4 sentences)
   - Key claims or arguments (bulleted)
   - Notable quotes (2–5, with context)
   - Entities mentioned (linked to entity pages)
   - Concepts covered (linked to concept pages)
   - Connections to existing wiki content
   - Open questions or gaps
5. Update or create entity pages for any person, org, curriculum mentioned
6. Update or create concept pages for any idea, theory, method discussed
7. Update `wiki/index.md` — add the new source and any new pages
8. Append an entry to `wiki/log.md`:
   `## [YYYY-MM-DD] ingest | Source Title`
9. Update `wiki/overview.md` if the source meaningfully shifts the synthesis

**A single ingest typically touches 5–15 wiki pages.** Be thorough with cross-references — this is the whole point.

### Answer a Query

1. Read `wiki/index.md` to identify relevant pages
2. Read those pages
3. Synthesize an answer with citations to wiki pages (not raw sources directly)
4. If the answer is substantive, ask the user if they want it filed as `wiki/queries/<date>-<slug>.md`
5. If filed, update `wiki/index.md` and append to `wiki/log.md`:
   `## [YYYY-MM-DD] query | Question summary`

### Lint the Wiki

1. Scan all pages for:
   - **Contradictions** between pages — flag with `> [!warning] Contradiction: ...`
   - **Stale claims** superseded by newer sources
   - **Orphan pages** with no inbound links — add links or note for deletion
   - **Missing pages** — concepts/entities mentioned but lacking their own page
   - **Broken links** — references to pages that don't exist
2. Report findings to user; fix with approval
3. Append to log: `## [YYYY-MM-DD] lint | Brief summary`

## Cross-Reference Conventions

- Use wiki-style links: `[[Page Name]]` (Obsidian format)
- When mentioning an entity or concept that has its own page, always link it on first occurrence in each page
- In entity and concept pages, maintain a **Mentioned in** section at the bottom listing source pages that reference this page
- Use Obsidian callouts for flags:
  - `> [!note]` — interesting aside
  - `> [!warning]` — contradiction or stale claim
  - `> [!question]` — open question, data gap

## Naming Conventions

- All filenames: lowercase, hyphens for spaces, no special characters
- Entity filenames: `firstname-lastname.md` for people, `org-name.md` for orgs
- Concept filenames: short but unambiguous, e.g., `socratic-method.md`
- Source filenames: match the raw source slug, e.g., `raw/some-article.md` → `wiki/sources/some-article.md`

## Index Maintenance

`wiki/index.md` is the LLM's primary navigation tool. On every ingest or query-file:
- Add the new source to the Sources table
- Add any new entity or concept pages to their tables
- Update the page counts at the top

When answering a query, read `wiki/index.md` first to find relevant pages before reading individual files.

## Obsidian Tips for This Vault

- **Graph view** shows hub pages (most-linked = most important concepts)
- **Dataview plugin** can query frontmatter for dynamic tables
- **Obsidian Web Clipper** converts web articles to markdown for `raw/`
- After clipping, use Ctrl+Shift+D (if configured) to download inline images to `raw/assets/`
- The wiki is a git repo — version history, branching, and collaboration are free
