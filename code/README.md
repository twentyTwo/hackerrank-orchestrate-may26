# Multi-Domain Support Triage Agent

A RAG-based support triage agent for the HackerRank Orchestrate hackathon (May 2026).

Given a support ticket (issue, subject, company), the agent:
1. Expands the ticket into 3 diverse search queries via LLM
2. Retrieves the most relevant knowledge-base chunks across 770+ articles (HackerRank, Claude, Visa)
3. Calls an LLM with the grounded context to produce a structured JSON response
4. Outputs: `status`, `product_area`, `response`, `justification`, `request_type`

---

## Architecture

```
support_tickets.csv
      │
      ▼
process_ticket()          ← agent.py
  │
  ├─ _expand_queries()    ← LLM generates 3 search queries from ticket
  │
  ├─ _retrieve_multi_query()  ← ChromaDB vector search (Voyage AI embeddings)
  │     └─ deduplication + top-k by score
  │
  ├─ _format_context()    ← numbered context block for LLM
  │
  └─ call_llm()           ← single Anthropic / Ollama call → JSON
        └─ _parse_response()   ← validation + retry on parse failure
              │
              ▼
        output.csv
```

**Key design decisions:**
- **2 LLM calls per ticket** (1 query expansion + 1 triage) — coherent output, vocabulary-aware retrieval
- Query expansion before retrieval — catches vocabulary mismatches between ticket and article titles
- Section-level chunking (split on `##`/`###` headings) — preserves semantic units
- Grounding rule baked into system prompt — no hallucinated phone numbers, URLs, or policies
- Dual backend: `PROVIDER=cloud` (Voyage AI + Claude) for final run; `PROVIDER=local` (Ollama) for dev

---

## Prerequisites

- Python 3.10+
- API keys: **Anthropic** and **Voyage AI** (for `PROVIDER=cloud`)
- Or: [Ollama](https://ollama.ai) running locally with `mxbai-embed-large` and `qwen3.5:9b` pulled (for `PROVIDER=local`)

---

## Install

```bash
# 1. Clone and enter repo
git clone <repo-url>
cd hackerrank-orchestrate-may26

# 2. Install dependencies
pip install -r code/requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env: set PROVIDER, ANTHROPIC_API_KEY, VOYAGE_API_KEY
```

---

## Run

```bash
# Step 1 — Build the vector index (only needed once, or after data changes)
python code/indexer.py

# Step 2 — Run on all support tickets → support_tickets/output.csv
python code/main.py
```

### Additional modes

```bash
# Validate against the 10 labelled sample tickets (prints accuracy table)
python code/main.py --validate

# Run on sample tickets only
python code/main.py --sample

# Run on a custom input CSV
python code/main.py --input path/to/tickets.csv

# Re-index from scratch (forces re-embedding)
python code/indexer.py --force

# Run indexer smoke tests
python code/indexer.py --test
```

---

## Configuration

All settings are in `code/config.py`. Secrets come from `.env` only — never hardcoded.

| Variable | Default | Description |
|---|---|---|
| `PROVIDER` | `local` | `cloud` = Voyage AI + Claude; `local` = Ollama |
| `ANTHROPIC_API_KEY` | — | Required for `PROVIDER=cloud` (LLM) |
| `VOYAGE_API_KEY` | — | Required for `PROVIDER=cloud` (embeddings) |
| `RETRIEVAL_TOP_K` | `7` | Chunks returned per query (after deduplication across expanded queries) |
| `EMBED_MODEL_CLOUD` | `voyage-3-large` | Voyage AI embedding model |
| `LLM_MODEL_CLOUD` | `claude-sonnet-4-5` | Anthropic chat model |
| `EMBED_MODEL_LOCAL` | `mxbai-embed-large` | Ollama embedding model |
| `LLM_MODEL_LOCAL` | `qwen3.5:9b` | Ollama chat model |

---

## Output schema

`support_tickets/output.csv` columns:

| Column | Values | Description |
|---|---|---|
| `issue` | string | Original ticket body |
| `subject` | string | Original ticket subject |
| `company` | string | HackerRank / Claude / Visa |
| `status` | `replied` \| `escalated` | Triage decision |
| `product_area` | string | Support category (e.g. `billing`, `screen`) |
| `request_type` | `product_issue` \| `feature_request` \| `bug` \| `invalid` | Ticket classification |
| `response` | string | User-facing reply, grounded in corpus |
| `justification` | string | Internal reasoning, cites article title |

---

## File structure

```
code/
  agent.py        — Core agent: query expansion, retrieval, LLM call, JSON parsing
  indexer.py      — Corpus loader, section chunker, embeddings, ChromaDB indexing
  config.py       — Paths, model names, provider switching, system prompt
  main.py         — CSV pipeline: read tickets → run_pipeline() → write output.csv
  log_entry.py    — AGENTS.md §5.2 log helper
  requirements.txt
  README.md       — This file

data/
  claude/         — 321 Claude support articles (markdown)
  hackerrank/     — 436 HackerRank support articles (markdown)
  visa/           — 13 Visa support articles (markdown)

chroma_db/        — Persistent ChromaDB vector store (4753 chunks, Voyage embeddings)

support_tickets/
  support_tickets.csv        — Input: 29 tickets to triage
  sample_support_tickets.csv — 10 labelled samples for validation
  output.csv                 — Agent output (submitted)
```
