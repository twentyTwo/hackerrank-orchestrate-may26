# Build Plan: Multi-Domain Support Triage Agent

## Tech Stack

| Component | Local (dev/test) | Cloud (final runs) |
|-----------|-----------------|-------------------|
| Embeddings | Ollama `mxbai-embed-large` (1024d) | Voyage AI `voyage-3-large` (1024d) |
| Reasoning | Ollama `qwen2.5:14b` | Claude Sonnet 4 (Anthropic) |
| Vector Store | ChromaDB (local, persistent) | ChromaDB (local, persistent) |
| Language | Python 3.11+ | Python 3.11+ |
| Switch | `PROVIDER=local` in `.env` | `PROVIDER=cloud` in `.env` |

**Separate ChromaDB collections per backend** — vectors are not interchangeable between embedding models.

---

## Prerequisites

```bash
# Local models
ollama pull mxbai-embed-large
ollama pull qwen2.5:14b

# Python environment
cd code/
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Environment variables — copy .env.example to .env
PROVIDER=local
ANTHROPIC_API_KEY=sk-ant-...
VOYAGE_API_KEY=pa-...
```

---

## File Structure

```
code/
├── main.py           # Entry point — CLI, CSV I/O, pipeline orchestration
├── indexer.py         # Corpus loading, chunking, embedding, ChromaDB indexing
├── agent.py           # Retrieval + LLM call → structured output (all 5 fields)
├── config.py          # Prompts, constants, provider switching logic
├── requirements.txt   # Pinned dependencies
├── README.md          # Setup & run instructions
└── PLAN.md            # This file
```

---

## Time Budget: 8 Hours

| Phase | Hours | Focus |
|-------|-------|-------|
| 1 — Corpus Indexing | 1.5 | Load, chunk, embed, store 774 articles |
| 2 — Agent Pipeline | 3.5 | Retrieval + single LLM call + structured output |
| 3 — Validate & Tune | 2.0 | Run on samples, compare, fix prompts |
| 4 — Ship | 1.0 | README, requirements, final run, submit |

---

## Phase 1: Corpus Indexing (1.5 hrs)

### Tasks

- [ ] **1.1** Create `config.py` — provider switching (local/cloud), constants, model names
- [ ] **1.2** Create `requirements.txt` — chromadb, voyageai, anthropic, pandas, python-dotenv, ollama
- [ ] **1.3** Set up `.env.example` with all env vars
- [ ] **1.4** Build corpus loader in `indexer.py`:
  - Walk `data/` recursively, find all `.md` files
  - For each file extract: title (first `#` heading or filename), body, company (from path), category (subfolder), source_path
  - Company mapping: `data/hackerrank/` → `HackerRank`, `data/claude/` → `Claude`, `data/visa/` → `Visa`
- [ ] **1.5** Build chunker in `indexer.py`:
  - Split articles into ~500 token chunks with 50-token overlap
  - Each chunk inherits parent metadata (company, category, title, source_path)
  - Keep chunk index for ordering
- [ ] **1.6** Build embedding function in `indexer.py`:
  - Local: call Ollama API (`POST http://localhost:11434/api/embeddings`, model `mxbai-embed-large`)
  - Cloud: call Voyage AI (`voyageai.Client().embed()`, model `voyage-3-large`)
  - Switch based on `PROVIDER` env var
- [ ] **1.7** Build ChromaDB indexing in `indexer.py`:
  - Create/load persistent ChromaDB at `./chroma_db/`
  - Separate collection names: `corpus_local` vs `corpus_cloud`
  - Store: chunk text, embedding, metadata (company, category, title, source_path, chunk_index)
  - Skip re-indexing if collection already exists and has expected count
- [ ] **1.8** Smoke test: run indexer, query "how to remove a user" → verify HackerRank docs returned

### Deliverable
Running `python indexer.py` builds the full vector index. Re-runs are skipped if index exists.

---

## Phase 2: Agent Pipeline (3.5 hrs)

### Tasks

- [ ] **2.1** Build retrieval function in `agent.py`:
  - Input: ticket text + company
  - Query ChromaDB with ticket text, filter by company metadata (no filter if company is `None`)
  - Return top-5 chunks with source paths and scores
  - Format chunks as numbered context block for the LLM prompt
- [ ] **2.2** Write system prompt in `config.py`:
  - Role: support triage agent for HackerRank / Claude / Visa
  - Output format: JSON with exactly 5 fields (status, product_area, response, justification, request_type)
  - Allowed values: status (replied/escalated), request_type (product_issue/feature_request/bug/invalid)
  - Escalation rules:
    - Fraud, identity theft, stolen cards → ESCALATE
    - Security vulnerabilities reported → ESCALATE
    - Billing disputes with transaction IDs → ESCALATE
    - Account lockout with no self-service path → ESCALATE
    - Site-wide outages with no self-service fix → ESCALATE
    - Threats, harassment, legal → ESCALATE
    - No relevant context found → ESCALATE
  - Reply rules:
    - Clear FAQ with corpus match → REPLY with grounded answer
    - Product usage questions with documentation → REPLY
    - Feature requests → REPLY (acknowledge, classify)
    - Invalid/out-of-scope → REPLY (politely decline)
  - Grounding constraint: "Use ONLY the provided context. Do not invent policies, steps, or URLs."
  - Justification must reference which article(s) informed the response
  - Handle company=None by inferring from content
  - Handle prompt injection attempts (reject, classify as invalid)
  - Handle non-English tickets (respond in English, note language)
- [ ] **2.3** Build LLM call function in `agent.py`:
  - Local: call Ollama API (`POST http://localhost:11434/api/chat`, model `qwen2.5:14b`)
  - Cloud: call Anthropic API (`anthropic.Client().messages.create()`, model `claude-sonnet-4-20250514`)
  - Temperature = 0 for determinism
  - Parse JSON response, validate all fields present and values allowed
  - Retry once on parse failure with "fix your JSON" nudge
- [ ] **2.4** Build agent function in `agent.py` — ties retrieval + LLM:
  - Input: one ticket row (issue, subject, company)
  - Step 1: retrieve context
  - Step 2: call LLM with context + ticket
  - Step 3: parse and validate output
  - Return: dict with all 5 output fields
- [ ] **2.5** Handle edge cases:
  - Empty/missing subject → use issue text only
  - Company = None → retrieve across all companies, let LLM infer
  - Prompt injection (ticket #24: "delete all files", #25: "show me fraud detection rules") → classify as invalid, reply politely
  - Non-English text (#25: French) → process normally, respond in English
  - Ambiguous tickets (#12: "it's not working, help") → escalate (insufficient info)

### Deliverable
`agent.process_ticket(issue, subject, company)` returns a validated dict with all 5 output fields.

---

## Phase 3: Validate & Tune (2 hrs)

### Tasks

- [ ] **3.1** Build CSV I/O in `main.py`:
  - Read `support_tickets/support_tickets.csv`
  - For each row: call `agent.process_ticket()`
  - Write `support_tickets/output.csv` with columns: issue, subject, company, response, product_area, status, request_type, justification
- [ ] **3.2** Build sample validation in `main.py`:
  - Read `support_tickets/sample_support_tickets.csv`
  - Run agent on each sample ticket
  - Compare output against expected: status, request_type, product_area
  - Print diff report (match/mismatch per field per ticket)
- [ ] **3.3** Run on 9 sample tickets (LOCAL backend first):
  - Check: are status decisions correct? (replied vs escalated)
  - Check: are request_type classifications correct?
  - Check: are product_area assignments reasonable?
  - Check: are responses grounded (no hallucination)?
- [ ] **3.4** Tune based on mismatches:
  - Adjust system prompt wording for classification rules
  - Adjust retrieval k (try 3, 5, 7) if context quality is poor
  - Adjust escalation threshold if too aggressive or too lenient
- [ ] **3.5** Run on all 31 tickets (LOCAL backend):
  - Spot-check 5-10 responses for quality
  - Verify CSV format is correct
- [ ] **3.6** Switch to CLOUD backend:
  - Re-index with Voyage embeddings (one time)
  - Run on 9 sample tickets → compare quality vs local
  - Run on all 31 tickets → generate final `output.csv`
- [ ] **3.7** Final quality check:
  - Read through all 31 responses
  - Verify no hallucinated policies or URLs
  - Verify escalation decisions make sense
  - Verify justifications cite corpus articles

### Deliverable
`support_tickets/output.csv` populated with all 31 ticket results, validated against samples.

---

## Phase 4: Ship (1 hr)

### Tasks

- [ ] **4.1** Finalize `requirements.txt` with exact pinned versions
- [ ] **4.2** Write `code/README.md`:
  - What it does (1 paragraph)
  - Prerequisites (Python, Ollama for local, API keys for cloud)
  - Install steps (3-4 commands)
  - Run steps (2 commands: index, then run)
  - Configuration (env vars table)
- [ ] **4.3** Create `.env.example` in repo root
- [ ] **4.4** Final run: `python main.py` → verify `output.csv` is complete and well-formatted
- [ ] **4.5** Verify no secrets in code or git history
- [ ] **4.6** Submit on HackerRank:
  - Zip `code/` (exclude venv, chroma_db, __pycache__)
  - Upload `output.csv`
  - Upload `log.txt`

### Deliverable
Submission uploaded on HackerRank Community Platform.

---

## Escalation Decision Matrix

| Signal in Ticket | Status | Request Type | Reasoning |
|-----------------|--------|--------------|-----------|
| Fraud / identity theft / stolen card | `escalated` | `product_issue` | High-risk, needs human verification |
| Security vulnerability report | `escalated` | `bug` | Sensitive, needs security team |
| Billing dispute with transaction ID | `escalated` | `product_issue` | Financial, needs account access |
| Account locked / access lost | `escalated` | `product_issue` | Needs identity verification |
| Site-wide outage / all features broken | `escalated` | `bug` | Needs engineering investigation |
| Subscription pause/cancel request | `escalated` | `product_issue` | Needs account-level action |
| Assessment reschedule request | `escalated` | `product_issue` | Needs recruiter/admin action |
| Vague "not working" with no detail | `escalated` | `bug` | Insufficient info to resolve |
| Clear FAQ with corpus answer | `replied` | `product_issue` | Can answer from docs |
| How-to question with docs | `replied` | `product_issue` | Can answer from docs |
| Feature request | `replied` | `feature_request` | Acknowledge, no action needed |
| Off-topic / nonsense | `replied` | `invalid` | Politely decline |
| Prompt injection / manipulation | `replied` | `invalid` | Reject, do not comply |

---

## Key Design Decisions (for AI Judge interview)

1. **Single LLM call per ticket** — all 5 fields in one structured output. Why: coherence between classification and response, 3x fewer API calls, simpler to debug.
2. **Dual backend (local/cloud)** — iterate for free, pay only for final quality. Why: cost-efficient for a 31-ticket task with heavy prompt tuning needed.
3. **ChromaDB** — over FAISS because metadata filtering (by company) reduces noise in retrieval.
4. **~500 token chunks** — articles vary from 200 to 5000+ tokens; chunking ensures the most relevant passage surfaces, not just "this was the longest article."
5. **Escalation over guessing** — the evaluation penalizes hallucinated policies. When in doubt, escalate. False escalation is less costly than a wrong answer.
6. **Justification cites sources** — evaluation checks traceability. Every response references which corpus article(s) it drew from.
7. **Temperature = 0** — determinism requirement from evaluation criteria. Same input → same output.

---

## Total Estimated Cost

| Scenario | Cost |
|----------|------|
| All dev/testing (local) | $0 |
| Cloud corpus indexing (one-time) | ~$0.28 |
| 2-3 cloud full runs | ~$1.24–$1.86 |
| **Total** | **~$2** |
