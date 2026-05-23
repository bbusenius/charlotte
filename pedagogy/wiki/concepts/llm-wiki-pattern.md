---
name: "LLM Wiki Pattern"
tags: [knowledge-management, llm-tooling, meta, workflow]
sources: [karpathy-llm-wiki]
---

# LLM Wiki Pattern

## Definition

A method for building personal knowledge bases where an LLM incrementally writes and maintains a persistent, interlinked markdown wiki from curated source documents — rather than retrieving from raw sources at query time (RAG).

## Core Ideas

- **Compile once, keep current.** Knowledge is extracted from sources and integrated into wiki pages on ingest. Queries hit the already-synthesized wiki, not raw documents.
- **Compounding artifact.** Each new source enriches existing pages. Over time the wiki reflects a synthesis of everything ingested, not just the most recent retrieval.
- **Human + LLM division of labor.** Human: curation, questions, direction. LLM: summarizing, cross-referencing, filing, consistency maintenance.
- **The schema drives discipline.** A CLAUDE.md (or AGENTS.md) file defines conventions and workflows, turning the LLM into a reliable wiki maintainer rather than a generic assistant.

## Three-Layer Architecture

1. **Raw sources** — immutable input files (articles, papers, books, clips). The source of truth. LLM reads but never writes here.
2. **Wiki** — LLM-owned markdown files: source summaries, entity pages, concept pages, query answers, index, log, overview.
3. **Schema** — CLAUDE.md defining directory structure, page types, frontmatter, and operational workflows (ingest, query, lint).

## Three Operations

- **Ingest** — add a source, produce ~5–15 updated wiki pages
- **Query** — ask questions answered from the wiki with citations; file notable answers back
- **Lint** — periodic health check: contradictions, orphans, broken links, missing pages

## Contrast with RAG

| | RAG | LLM Wiki |
|---|---|---|
| Where synthesis happens | Query time | Ingest time |
| Accumulation | None | Compounding |
| Cross-references | Derived on demand | Pre-built |
| Contradiction detection | None | Flagged during ingest |
| Human maintenance burden | Low initially, grows | Near zero (LLM does it) |

## In Practice (This Vault)

This vault implements the pattern for a pedagogy / homeschooling knowledge base. Obsidian is the browsing interface; Claude Code is the LLM maintainer; this wiki is the codebase.

## Key Proponents / Origins

- [[entities/andrej-karpathy]] — described and popularized this pattern
- [[entities/vannevar-bush]] — intellectual predecessor (Memex, 1945): private, curated, associative trails

## Mentioned In

- [[sources/karpathy-llm-wiki]] — original description of the pattern
