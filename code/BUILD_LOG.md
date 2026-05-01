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

**What:** Created `code/requirements.txt`, `.env.example`, `code/config.py`, added `chroma_db/` to `.gitignore`.

**Why:**
- `requirements.txt` pins only the 5 top-level packages we actually need. No `pip freeze` dump — that creates noise and version conflicts across machines.
- `.env.example` documents all env vars in one place. `PROVIDER=local` is the default so the agent works out of the box without any API keys.
- `config.py` centralises paths, model names, and the system prompt. This means you change things in one place, not scattered across files.
- `chroma_db/` added to `.gitignore` — it’s a runtime artefact (the vector index), not source code. Committing it would bloat the repo.

**Trade-off:** Could have used a `pyproject.toml` instead of `requirements.txt`. Rejected — requirements.txt is simpler and universally understood.

**Files touched:** `code/requirements.txt`, `.env.example`, `code/config.py`, `.gitignore`

#### Task 1.2 — Corpus Loader

**What:** `load_corpus()` in `indexer.py`. Walks `data/` recursively, parses YAML frontmatter, extracts title/body/company/category/source_path for each article. Skips `index.md` navigation files and files shorter than 50 chars.

**Why:**
- The markdown files have YAML frontmatter (`---`) with metadata like `title`. We parse that first, then fall back to the first `#` heading, then the filename. This gives us the best title for each article.
- Company is inferred from the top-level directory (`data/hackerrank/` → `HackerRank`). No hardcoding needed.
- Category comes from the second-level directory (`screen`, `interviews`, `pricing-and-billing`). This becomes a metadata field in ChromaDB, usable for debugging retrievals.
- `source_path` is stored relative to `data/` (not absolute) so the project works on any machine.

**Trade-off:** We skip `index.md` files. These are navigation pages with article lists, not content — including them would add noise to retrieval.

**Files touched:** `code/indexer.py`

#### Task 1.3 — Section Chunker

**What:** `chunk_article()` and `chunk_corpus()` in `indexer.py`. Splits articles on `##`/`###` headings. Short articles (≈ fewer than 800 chars body) stay whole. Sections exceeding 3000 chars are further split on paragraph boundaries.

**Why:**
- The support documents are already structured with headings. Each section is about one specific topic. Splitting on headings gives semantically coherent chunks without needing a tokenizer.
- Short articles (many Visa docs, FAQs) don’t need splitting — they’re already small enough.
- Very long sections (e.g. the Claude release notes covering months of updates) would dominate a single chunk’s context window. We split those further on paragraph boundaries to keep them manageable.
- Each chunk **prefixes the article title** (e.g. `Managing Tests — Expiration Settings\n\n<section body>`). This means even if a section is retrieved without the article title in the heading, the LLM still knows what article it came from.

**Trade-off:** We chose heading-based over token-count chunking. Token-count with overlap (the typical approach) requires a tokenizer dependency and can cut mid-sentence. Heading-based is faster to build, easier to debug, and produces cleaner context windows for this corpus.

**Files touched:** `code/indexer.py`

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
