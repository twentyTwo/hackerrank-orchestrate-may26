# Build Log: What Was Done and Why

> This file is updated after every task. Read it before the AI Judge interview.
> It explains every decision, trade-off, and implementation detail in plain language.

---

## How to Read This File

Each entry follows this format:
- **Task**: which task was completed
- **What**: what was built or changed
- **Why**: the reasoning behind the decision
- **Trade-off**: what alternatives were considered and rejected
- **Files touched**: which files were created or modified

---

## Build Timeline

*(Entries will be added below as tasks are completed)*

---

### Phase 1: Setup & Corpus Indexing

#### Task 1.1 — Project Setup
*(pending)*

#### Task 1.2 — Corpus Loader
*(pending)*

#### Task 1.3 — Section Chunker
*(pending)*

#### Task 1.4 — Embedding & Indexing
*(pending)*

#### Task 1.5 — Retrieval Smoke Test
*(pending)*

---

### Phase 2: Agent Pipeline

#### Task 2.1 — System Prompt
*(pending)*

#### Task 2.2 — LLM Call
*(pending)*

#### Task 2.3 — Agent Core
*(pending)*

#### Task 2.4 — Edge Cases
*(pending)*

---

### Phase 3: Pipeline, Validate & Run

#### Task 3.1 — CSV Pipeline
*(pending)*

#### Task 3.2 — Sample Validation
*(pending)*

#### Task 3.3 — Full Run
*(pending)*

#### Task 3.4 — Cloud Quality Upgrade (Optional)
*(pending)*

---

### Phase 4: Ship

#### Task 4.1 — Documentation
*(pending)*

#### Task 4.2 — Final Checks
*(pending)*

#### Task 4.3 — Submit
*(pending)*

---

## Architecture Summary

*(Will be filled in as the agent takes shape)*

```
[Ticket CSV] → [Corpus Loader + Chunker] → [Embedding + ChromaDB Index]
                                                     ↓
[For each ticket] → [Retrieve top-5 chunks] → [LLM (system prompt + context + ticket)] → [Parse JSON] → [Output CSV]
```

## Key Decisions Register

| # | Decision | Chosen | Rejected | Why |
|---|----------|--------|----------|-----|
| 1 | Chunking strategy | Markdown section-based | Token-count with overlap | Docs are already structured by headings; section chunks are semantically coherent, no tokenizer needed |
| 2 | Vector store | ChromaDB in-memory | FAISS / persistent ChromaDB | Corpus is small (~3K chunks); in-memory is simpler, re-indexing takes seconds |
| 3 | Embedding model | Ollama mxbai-embed-large (local) / Voyage voyage-3-large (cloud) | OpenAI text-embedding-3-large | Voyage is highest quality; Ollama is free for dev; dual-backend via simple if/else |
| 4 | LLM | Ollama qwen2.5:14b (local) / Claude Sonnet 4 (cloud) | GPT-4o-mini, local 8B models | Claude Sonnet 4 is best at structured output + grounding; qwen2.5:14b is best local option for 16GB VRAM |
| 5 | Pipeline style | Single LLM call per ticket (all 5 fields at once) | Separate classify → route → generate calls | One call = better coherence, fewer API calls, simpler debugging |
| 6 | Backend switching | Single PROVIDER env var with if/else | Separate modules, factory pattern, named collections | YAGNI — for 31 tickets, simplicity wins over abstraction |
| 7 | Retrieval | Semantic search with company filter | BM25, hybrid BM25+vector | Semantic handles paraphrased queries better; company filter reduces noise |
| 8 | Escalation philosophy | Escalate when uncertain | Always try to answer | Evaluation penalizes hallucination more than unnecessary escalation |
