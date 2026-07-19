---
title: "LLM Wiki"
author: "Andrej Karpathy"
year: 2026
type: gist
tags: [knowledge-management, llm-tooling, meta, workflow]
source_path: "raw/karpathy-llm-wiki.md"
source_url: "https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f"
date_ingested: 2026-04-18
---

# LLM Wiki

**Author:** [[entities/andrej-karpathy]]  
**Year:** 2026  
**Type:** gist / idea file

## Overview

Karpathy's LLM Wiki pattern proposes using LLMs not as query-time retrievers (RAG) but as active maintainers of a persistent, interlinked markdown wiki. The human curates sources; the LLM does all the bookkeeping — summarizing, cross-referencing, filing, and keeping the wiki current. The result is a compounding knowledge artifact rather than a static document collection.

## Key Claims

- **RAG rediscovers knowledge on every query.** There is no accumulation — complex synthesis questions require the LLM to piece together fragments from scratch each time.
- **The wiki is a persistent, compounding artifact.** Cross-references are already there; contradictions already flagged; synthesis already reflects everything ingested.
- **Three-layer architecture:** raw sources (immutable), wiki (LLM-owned), schema/CLAUDE.md (configuration).
- **Three core operations:** ingest, query, lint.
- **A single ingest touches 10–15 wiki pages** — summary, entity updates, concept updates, index, log.
- **Good query answers should be filed back into the wiki** so explorations compound like ingested sources.
- **The schema (CLAUDE.md/AGENTS.md) is the key configuration file** that makes the LLM a disciplined maintainer rather than a generic chatbot.
- **The human's bottleneck is maintenance, not reading.** LLMs solve this — they don't get bored and can touch 15 files in one pass.
- Relates in spirit to **Vannevar Bush's Memex (1945)** — private, actively curated, with associative trails between documents.

## Attributed Paraphrases

- A maintained wiki accumulates synthesis and cross-references instead of
  recreating them for every question.
- Karpathy presents the note browser, the agent, and the wiki as parts of one
  working environment.
- Agent maintenance reduces the repetitive bookkeeping that often causes
  human-maintained wikis to decay.
- The proposal connects this maintenance role to the unfinished practical
  challenge in Vannevar Bush's Memex idea.

## Entities Mentioned

- [[entities/andrej-karpathy]] — author; AI researcher (Tesla Autopilot, OpenAI)
- [[entities/vannevar-bush]] — cited as intellectual predecessor (Memex, 1945)

## Concepts Covered

- [[concepts/llm-wiki-pattern]] — the core idea of this source
- [[concepts/rag-vs-wiki]] — RAG as the foil; wiki as the alternative
- Knowledge-base maintenance — why humans abandon wikis; why LLMs don't (no dedicated concept page; covered within [[concepts/llm-wiki-pattern]])

## Tooling Mentioned

- **Obsidian** — recommended IDE for browsing the wiki
- **Obsidian Web Clipper** — browser extension to clip articles to markdown
- **Marp** — markdown slide decks (Obsidian plugin)
- **Dataview** — Obsidian plugin for querying page frontmatter
- **qmd** — local BM25/vector search engine for markdown, with MCP server

## Connections to Existing Wiki

This is the foundational source for the wiki itself — it describes the pattern this vault implements. All future sources will build on the architecture described here.

## Open Questions & Gaps

> [!question] How does this scale beyond ~hundreds of pages — at what point does index.md break down as the navigation mechanism?

> [!question] What are good homeschool-specific entity and concept types to standardize on as the wiki grows?
