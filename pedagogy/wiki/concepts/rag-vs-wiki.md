---
name: "RAG vs. LLM Wiki"
tags: [knowledge-management, llm-tooling, rag]
sources: [karpathy-llm-wiki]
---

# RAG vs. LLM Wiki

## Definition

Two contrasting approaches to LLM-assisted document knowledge bases. RAG (Retrieval-Augmented Generation) retrieves from raw sources at query time. The LLM Wiki compiles knowledge into a maintained wiki at ingest time.

## Core Distinction

RAG is **stateless** — the LLM rediscovers knowledge from scratch on every query. The LLM Wiki is **stateful** — knowledge accumulates in the wiki and compounds over time.

## RAG

- Retrieve relevant document chunks at query time using embeddings
- LLM synthesizes an answer from retrieved fragments
- No persistent artifact beyond the raw documents
- Works well for: large, stable document collections; one-off questions
- Limitation: no accumulation; complex synthesis questions require re-deriving relationships every time
- Examples: NotebookLM, ChatGPT file uploads, most enterprise RAG systems

## LLM Wiki

- LLM reads each source on ingest and integrates knowledge into wiki pages
- Queries hit the already-synthesized wiki
- Cross-references, contradictions, and synthesis pre-built
- Works well for: ongoing research; domains where synthesis matters; building understanding over months
- See [[concepts/llm-wiki-pattern]] for full description

## When to Use Each

RAG is better when you have many documents and need flexible retrieval without curation overhead. The LLM Wiki is better when you're building deep understanding in a specific domain over time and want the knowledge to compound.

> [!note] The two approaches aren't mutually exclusive — at large scale, the LLM Wiki could use a search engine (e.g., qmd) over wiki pages as a hybrid.

## Mentioned In

- [[sources/karpathy-llm-wiki]] — RAG introduced as the foil to motivate the wiki pattern
