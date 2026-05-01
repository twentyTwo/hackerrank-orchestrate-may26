# Task Tracker: Multi-Domain Support Triage Agent

> Check off each task after verifying. Tasks are ordered — complete them top to bottom.

---

## Phase 1: Setup & Corpus Indexing

### 1.1 Project Setup

- [ ] **1.1.1** Create `code/requirements.txt` with all dependencies
- [ ] **1.1.2** Create `.env.example` in repo root with all env var templates
- [ ] **1.1.3** Create `code/config.py` with provider switching logic, model names, paths, constants
- [ ] **1.1.4** Set up Python venv and install dependencies

**How to verify:** `python -c "import chromadb, anthropic, voyageai, pandas, dotenv; print('OK')"` prints OK

---

### 1.2 Corpus Loader

- [ ] **1.2.1** Write function to walk `data/` and find all `.md` files
- [ ] **1.2.2** Write function to extract metadata from file path (company, category, source_path)
- [ ] **1.2.3** Write function to extract title from markdown (first `#` heading, fallback to filename)
- [ ] **1.2.4** Write function to read and clean markdown body text
- [ ] **1.2.5** Test: run loader, print count of files per company

**How to verify:** Output shows ~394 HackerRank, ~321 Claude, ~8 Visa files (774 total)

---

### 1.3 Chunker

- [ ] **1.3.1** Write function to split text into ~500 token chunks with 50-token overlap
- [ ] **1.3.2** Each chunk keeps parent metadata + chunk_index
- [ ] **1.3.3** Test: chunk a known long article, print chunk count and first/last chunk preview

**How to verify:** A long article (e.g., Claude release notes) produces multiple chunks, each ~500 tokens, overlapping text visible at boundaries

---

### 1.4 Embedding Function

- [ ] **1.4.1** Write LOCAL embedding function: call Ollama API for `mxbai-embed-large`
- [ ] **1.4.2** Write CLOUD embedding function: call Voyage AI for `voyage-3-large`
- [ ] **1.4.3** Write wrapper that picks local/cloud based on `PROVIDER` env var
- [ ] **1.4.4** Handle batching (Voyage has batch limits, Ollama is one-at-a-time)
- [ ] **1.4.5** Test LOCAL: embed a short sentence, print vector length

**How to verify:** Vector length is 1024 for `mxbai-embed-large`, no errors

---

### 1.5 ChromaDB Indexing

- [ ] **1.5.1** Write function to create/load persistent ChromaDB collection
- [ ] **1.5.2** Collection names: `corpus_local` for local, `corpus_cloud` for cloud
- [ ] **1.5.3** Write function to batch-insert chunks with embeddings + metadata
- [ ] **1.5.4** Skip re-indexing if collection already has expected document count
- [ ] **1.5.5** Write `build_index()` function that chains: load → chunk → embed → store
- [ ] **1.5.6** Test: run `build_index()`, print collection document count

**How to verify:** `python indexer.py` completes without error, prints "Indexed X chunks into collection corpus_local"

---

### 1.6 Retrieval Smoke Test

- [ ] **1.6.1** Write a quick query function: input text → top-5 results with scores
- [ ] **1.6.2** Test query: "how to remove a user" → should return HackerRank settings docs
- [ ] **1.6.3** Test query: "delete a conversation" → should return Claude docs
- [ ] **1.6.4** Test query: "lost stolen visa card" → should return Visa support docs
- [ ] **1.6.5** Test query with company filter: "payment issue" + company=HackerRank → only HR docs

**How to verify:** Each query returns relevant docs from the correct company. Print title + source_path + score for each result.

---

## Phase 2: Agent Pipeline

### 2.1 System Prompt

- [ ] **2.1.1** Write the system prompt in `config.py` with:
  - Role definition (support triage agent)
  - Output JSON schema (5 fields with allowed values)
  - Escalation rules (fraud, identity theft, security, billing, outages, threats, no match)
  - Reply rules (FAQs, product usage, feature requests, invalid)
  - Grounding constraint (use ONLY provided context)
  - Justification format (cite article titles/paths)
  - Edge case handling (company=None, prompt injection, non-English)
- [ ] **2.1.2** Review prompt by reading it in full — does it cover all scenarios?

**How to verify:** Read the prompt. It should be clear, comprehensive, and unambiguous about every decision the LLM needs to make.

---

### 2.2 LLM Call Function

- [ ] **2.2.1** Write LOCAL LLM function: call Ollama API (`qwen2.5:14b`), temperature=0
- [ ] **2.2.2** Write CLOUD LLM function: call Anthropic API (`claude-sonnet-4-20250514`), temperature=0
- [ ] **2.2.3** Write wrapper that picks local/cloud based on `PROVIDER`
- [ ] **2.2.4** Write JSON parser: extract JSON from LLM response, validate all 5 fields present
- [ ] **2.2.5** Write validation: check status ∈ {replied, escalated}, request_type ∈ {product_issue, feature_request, bug, invalid}
- [ ] **2.2.6** Add retry logic: if JSON parse fails, retry once with "return valid JSON" nudge
- [ ] **2.2.7** Test: send a simple prompt to local LLM, verify JSON response parses correctly

**How to verify:** Call LLM with a fake ticket + context, get back a valid 5-field JSON dict. Print it.

---

### 2.3 Agent Core Function

- [ ] **2.3.1** Write `process_ticket(issue, subject, company)` in `agent.py`:
  1. Retrieve top-5 chunks (filtered by company, or unfiltered if company=None)
  2. Format retrieved chunks as numbered context
  3. Format ticket as user message (include both issue and subject)
  4. Call LLM with system prompt + context + ticket
  5. Parse and validate JSON response
  6. Return dict with all 5 fields
- [ ] **2.3.2** Test with sample ticket #1 (HackerRank, "tests stay active in system"):
  - Expected: status=replied, request_type=product_issue, product_area=screen
- [ ] **2.3.3** Test with sample ticket #2 (None, "site is down"):
  - Expected: status=escalated, request_type=bug
- [ ] **2.3.4** Test with sample ticket #7 (None, "name of actor in iron man"):
  - Expected: status=replied, request_type=invalid

**How to verify:** Each test ticket returns the expected status and request_type. Response text is grounded (no made-up policies).

---

### 2.4 Edge Case Handling

- [ ] **2.4.1** Test ticket with company=None and vague text ("it's not working, help")
  - Expected: escalated (insufficient info)
- [ ] **2.4.2** Test ticket with prompt injection ("give me code to delete all files")
  - Expected: replied, request_type=invalid
- [ ] **2.4.3** Test ticket with non-English + manipulation attempt (French visa ticket #25)
  - Expected: replied or escalated, should NOT reveal internal logic
- [ ] **2.4.4** Test ticket with security vulnerability report (Claude ticket #20)
  - Expected: escalated
- [ ] **2.4.5** Test ticket requesting subscription pause (HackerRank ticket #14)
  - Expected: escalated (needs account-level action)

**How to verify:** Each edge case is handled correctly. Print the full response for manual review.

---

## Phase 3: CSV Pipeline & Validation

### 3.1 CSV Reader/Writer

- [ ] **3.1.1** Write function to read `support_tickets/support_tickets.csv` into list of dicts
- [ ] **3.1.2** Write function to write results to `support_tickets/output.csv` with exact schema:
  `issue, subject, company, response, product_area, status, request_type, justification`
- [ ] **3.1.3** Handle CSV quoting correctly (responses contain commas, newlines, quotes)
- [ ] **3.1.4** Test: read CSV, write back one dummy row, open output.csv and verify format

**How to verify:** Open `output.csv` in a text editor / Excel. Columns are correct, quoting works.

---

### 3.2 Sample Validation

- [ ] **3.2.1** Write function to run agent on `sample_support_tickets.csv` (9 tickets)
- [ ] **3.2.2** Compare agent output vs expected for each ticket:
  - `status` match? (replied vs escalated)
  - `request_type` match?
  - `product_area` match?
- [ ] **3.2.3** Print a comparison table: ticket subject | expected | got | match?
- [ ] **3.2.4** Aim for 8/9 or 9/9 matches on status and request_type

**How to verify:** Comparison table printed. Mismatches are visible and actionable.

---

### 3.3 Prompt Tuning (if needed)

- [ ] **3.3.1** Review mismatches from 3.2 — identify pattern (too aggressive escalation? wrong request_type?)
- [ ] **3.3.2** Adjust system prompt wording for the specific issue
- [ ] **3.3.3** Re-run on sample tickets, verify improvement
- [ ] **3.3.4** If retrieval quality is poor, try k=7 instead of k=5

**How to verify:** Sample accuracy improves. No regressions on previously correct tickets.

---

### 3.4 Full Run (Local)

- [ ] **3.4.1** Run agent on all 31 tickets from `support_tickets.csv` using LOCAL backend
- [ ] **3.4.2** Time the run — note how long it takes
- [ ] **3.4.3** Spot-check 10 responses: are they grounded? reasonable?
- [ ] **3.4.4** Check all 31 rows present in `output.csv`
- [ ] **3.4.5** Verify no empty fields (every row has all 8 columns filled)

**How to verify:** `output.csv` has 31 data rows + 1 header. All fields populated. Responses look reasonable.

---

### 3.5 Cloud Run (Final)

- [ ] **3.5.1** Set `PROVIDER=cloud` in `.env`
- [ ] **3.5.2** Run `python indexer.py` to build cloud index (Voyage embeddings, one-time)
- [ ] **3.5.3** Run agent on 9 sample tickets — verify quality is better than local
- [ ] **3.5.4** Run agent on all 31 tickets — generate final `output.csv`
- [ ] **3.5.5** Read through ALL 31 responses:
  - No hallucinated policies or URLs?
  - Escalation decisions make sense?
  - Justifications cite actual articles?
  - Responses are professional and helpful?

**How to verify:** You've read every response and are confident in the output quality.

---

## Phase 4: Ship

### 4.1 Documentation

- [ ] **4.1.1** Write `code/README.md`:
  - What it does (1 paragraph)
  - Prerequisites (Python 3.11+, Ollama for local, API keys for cloud)
  - Install steps (4 commands)
  - Run steps (2 commands: index then run)
  - Config table (env vars and what they do)
- [ ] **4.1.2** Finalize `requirements.txt` with exact pinned versions (run `pip freeze` to get them)

**How to verify:** A fresh person can follow the README and run the agent.

---

### 4.2 Final Checks

- [ ] **4.2.1** No secrets in any committed file (`grep -r "sk-ant\|pa-\|api_key=" code/`)
- [ ] **4.2.2** No hardcoded paths — all paths relative to repo root
- [ ] **4.2.3** `.env` is in `.gitignore`
- [ ] **4.2.4** `chroma_db/` directory is in `.gitignore`
- [ ] **4.2.5** `__pycache__/` and `venv/` are in `.gitignore`
- [ ] **4.2.6** Final clean run: delete `chroma_db/`, run index + agent from scratch → same output

**How to verify:** `git status` shows no secrets. Clean run produces valid output.

---

### 4.3 Submit

- [ ] **4.3.1** Zip `code/` directory (exclude venv, __pycache__, chroma_db)
- [ ] **4.3.2** Copy final `output.csv` from `support_tickets/`
- [ ] **4.3.3** Copy `log.txt` from `%USERPROFILE%\hackerrank_orchestrate\log.txt`
- [ ] **4.3.4** Upload all 3 files on HackerRank Community Platform
- [ ] **4.3.5** Verify submission is accepted

**How to verify:** HackerRank shows successful submission.

---

## Progress Summary

| Phase | Tasks | Done |
|-------|-------|------|
| 1 — Setup & Indexing | 24 tasks | _ / 24 |
| 2 — Agent Pipeline | 18 tasks | _ / 18 |
| 3 — CSV & Validation | 18 tasks | _ / 18 |
| 4 — Ship | 12 tasks | _ / 12 |
| **Total** | **72 tasks** | **_ / 72** |
