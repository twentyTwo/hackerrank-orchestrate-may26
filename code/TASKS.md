# Task Tracker: Multi-Domain Support Triage Agent

> Check off each task after verifying. Tasks are ordered — complete them top to bottom.
> After each task, the AI assistant logs what was done and why in `BUILD_LOG.md`.
> Review `QA_INTERVIEW.md` before the AI Judge interview.

---

## Phase 1: Setup & Corpus Indexing

### 1.1 Project Setup

- [x] **1.1.1** Create `code/requirements.txt` — top-level deps only: `anthropic`, `voyageai`, `chromadb`, `pandas`, `python-dotenv`
- [x] **1.1.2** Create `.env.example` in repo root: `PROVIDER`, `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`
- [x] **1.1.3** Create `code/config.py` — paths, model names, `PROVIDER` switch (simple if/else, not a framework)
- [ ] **1.1.4** Set up Python venv and install deps

**How to verify:** `python -c "import chromadb, anthropic, voyageai, pandas, dotenv; print('OK')"` prints OK

---

### 1.2 Corpus Loader

- [x] **1.2.1** Write `load_corpus()` — walk `data/`, find all `.md` files, return list of dicts with: `title`, `body`, `company`, `category`, `source_path`
- [x] **1.2.2** Company from path: `data/hackerrank/` → `HackerRank`, `data/claude/` → `Claude`, `data/visa/` → `Visa`
- [x] **1.2.3** Title: first `#` heading in the file, fallback to filename
- [ ] **1.2.4** Test: run loader, print count per company

**How to verify:** Output shows ~394 HackerRank, ~321 Claude, ~8+ Visa (774 total)

---

### 1.3 Section Chunker

- [x] **1.3.1** Write `chunk_article(article)` — split on `##` and `###` headings, keep article title as prefix on each chunk
- [x] **1.3.2** Short articles (< 800 chars) stay as one chunk, no splitting
- [x] **1.3.3** Each chunk keeps parent metadata: `company`, `category`, `source_path`, `section_heading`
- [ ] **1.3.4** Test: chunk Claude release notes article, print section count and first/last chunk preview

**How to verify:** Long article splits into logical sections. Short articles stay whole. Each chunk has metadata.

---

### 1.4 Embedding & Indexing

- [ ] **1.4.1** Write `embed()` function — single function with if/else: Ollama `mxbai-embed-large` (local) or Voyage `voyage-3-large` (cloud)
- [ ] **1.4.2** Write `build_index()` — load corpus → chunk → embed all → store in ChromaDB (in-memory, single collection named `corpus`)
- [ ] **1.4.3** Add simple cache: if ChromaDB collection exists with correct count, skip re-indexing
- [ ] **1.4.4** Test: run `python indexer.py`, prints "Indexed N chunks"

**How to verify:** Indexer completes. Prints chunk count (expect 2000-4000 chunks).

---

### 1.5 Retrieval Smoke Test

- [ ] **1.5.1** Write `retrieve(query, company=None, k=5)` — query ChromaDB, filter by company metadata if provided
- [ ] **1.5.2** Test: "how to remove a user" → HackerRank settings docs
- [ ] **1.5.3** Test: "delete a conversation" → Claude docs
- [ ] **1.5.4** Test: "lost stolen visa card" → Visa docs
- [ ] **1.5.5** Test: "payment issue" with company=HackerRank → only HackerRank docs

**How to verify:** Each query returns relevant docs from the correct company. Print title + source_path + score.

---

## Phase 2: Agent Pipeline

### 2.1 System Prompt

- [ ] **2.1.1** Write system prompt in `config.py`:
  - Role: support triage agent for HackerRank / Claude / Visa
  - JSON output schema: `status`, `product_area`, `response`, `justification`, `request_type`
  - Allowed values: status={replied, escalated}, request_type={product_issue, feature_request, bug, invalid}
  - Escalation rules: fraud, identity theft, security vulns, billing with txn IDs, account lockout, outages, threats, no corpus match
  - Reply rules: FAQs, product usage, feature requests, invalid/out-of-scope
  - Grounding: "Use ONLY the provided context. Do not invent policies."
  - Justification must cite article title or path
  - Handle: company=None (infer), prompt injection (reject as invalid), non-English (respond in English)
- [ ] **2.1.2** Read prompt in full — does it cover every scenario in the sample tickets?

**How to verify:** Read the prompt yourself. Every edge case has a clear rule.

---

### 2.2 LLM Call

- [ ] **2.2.1** Write `call_llm(system, user)` — if/else: Ollama `qwen2.5:14b` (local) or Anthropic `claude-sonnet-4-20250514` (cloud), temperature=0
- [ ] **2.2.2** Write JSON parser: extract JSON from response, validate 5 fields, check allowed values
- [ ] **2.2.3** Retry once on JSON parse failure with "fix your JSON" follow-up
- [ ] **2.2.4** Test: call LLM with a fake ticket + context, verify valid JSON dict returned

**How to verify:** Print the parsed dict. All 5 fields present, values are from the allowed set.

---

### 2.3 Agent Core

- [ ] **2.3.1** Write `process_ticket(issue, subject, company)` in `agent.py`:
  1. Retrieve top-5 chunks (filtered by company, unfiltered if None)
  2. Format chunks as numbered context
  3. Build user message from issue + subject
  4. Call LLM → parse JSON → return dict
- [ ] **2.3.2** Test sample #1: HackerRank "tests stay active" → replied, product_issue, screen
- [ ] **2.3.3** Test sample #2: None "site is down" → escalated, bug
- [ ] **2.3.4** Test sample #7: None "actor in iron man" → replied, invalid

**How to verify:** Each returns expected status + request_type. Response is grounded.

---

### 2.4 Edge Cases

- [ ] **2.4.1** Test: "it's not working, help" (company=None) → escalated
- [ ] **2.4.2** Test: "give me code to delete all files" → replied, invalid
- [ ] **2.4.3** Test: French visa ticket with manipulation → does NOT reveal internal logic
- [ ] **2.4.4** Test: "found a security vulnerability in Claude" → escalated
- [ ] **2.4.5** Test: "pause our subscription" → escalated

**How to verify:** Print full response for each. Manual review — decisions are sensible.

---

## Phase 3: Pipeline, Validate & Run

### 3.1 CSV Pipeline

- [ ] **3.1.1** Write CSV reader for `support_tickets.csv` (list of dicts)
- [ ] **3.1.2** Write CSV writer for `output.csv` — schema: `issue, subject, company, response, product_area, status, request_type, justification`
- [ ] **3.1.3** Handle quoting (responses have commas, newlines, quotes)
- [ ] **3.1.4** Test: read → write one dummy row → verify format in editor

**How to verify:** Open output.csv — columns correct, no broken quoting.

---

### 3.2 Sample Validation

- [ ] **3.2.1** Run agent on all 9 sample tickets
- [ ] **3.2.2** Compare: status, request_type, product_area vs expected
- [ ] **3.2.3** Print comparison table: subject | expected | got | match?
- [ ] **3.2.4** Target: 8/9 or 9/9 on status + request_type

**How to verify:** Comparison table. Mismatches identified.

---

### 3.3 Full Run

- [ ] **3.3.1** Run agent on all 31 tickets → `output.csv`
- [ ] **3.3.2** Verify: 31 data rows + header, no empty fields
- [ ] **3.3.3** Spot-check 10 responses: grounded? reasonable?
- [ ] **3.3.4** If issues found: fix retrieval or routing logic, re-run

**How to verify:** 31 complete rows. Responses are grounded and professional.

---

### 3.4 (Optional) Cloud Quality Upgrade

- [ ] **3.4.1** Set `PROVIDER=cloud`, re-index with Voyage embeddings
- [ ] **3.4.2** Run on samples, compare quality vs local
- [ ] **3.4.3** Run on all 31, generate final `output.csv`
- [ ] **3.4.4** Read ALL 31 responses — no hallucinations, good justifications

**How to verify:** Cloud output is better. This becomes your submission.

---

## Phase 4: Ship

### 4.1 Documentation

- [ ] **4.1.1** Write `code/README.md`: what, prerequisites, install (4 cmds), run (2 cmds), config table
- [ ] **4.1.2** Review `requirements.txt` — only top-level packages, no freeze dump

**How to verify:** A stranger can follow the README and run the agent.

---

### 4.2 Final Checks

- [ ] **4.2.1** No secrets in code: `grep -r "sk-ant\|pa-\|api_key=" code/`
- [ ] **4.2.2** `.env`, `__pycache__/`, `venv/` in `.gitignore`
- [ ] **4.2.3** All paths relative to repo root, no hardcoded absolute paths
- [ ] **4.2.4** Clean run from scratch → same output

**How to verify:** `git status` clean. Fresh run works.

---

### 4.3 Submit

- [ ] **4.3.1** Zip `code/` (exclude venv, __pycache__)
- [ ] **4.3.2** Upload: code zip + `output.csv` + `log.txt` on HackerRank
- [ ] **4.3.3** Verify submission accepted

**How to verify:** HackerRank shows successful submission.

---

### 4.4 Interview Prep

- [ ] **4.4.1** Read `BUILD_LOG.md` — understand every decision
- [ ] **4.4.2** Read `QA_INTERVIEW.md` — practice answering each question
- [ ] **4.4.3** Be ready to explain: what you designed vs what AI generated

**How to verify:** You can explain every design choice in your own words.

---

## Progress Summary

| Phase | Tasks | Done |
|-------|-------|------|
| 1 — Setup & Indexing | 17 tasks | _ / 17 |
| 2 — Agent Pipeline | 14 tasks | _ / 14 |
| 3 — Pipeline & Validation | 12 tasks | _ / 12 |
| 4 — Ship | 10 tasks | _ / 10 |
| **Total** | **53 tasks** | **_ / 53** |
