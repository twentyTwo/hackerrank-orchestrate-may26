"""
agent.py — Core agent: retrieve context + single LLM call → structured output.

Public API:
    process_ticket(issue, subject, company) -> dict with 5 fields
"""

import json
import re

from config import (
    PROVIDER,
    SYSTEM_PROMPT,
    LLM_MODEL_LOCAL,
    LLM_MODEL_CLOUD,
    RETRIEVAL_TOP_K,
)
from indexer import retrieve

# ---------------------------------------------------------------------------
# Allowed field values for validation
# ---------------------------------------------------------------------------
VALID_STATUS = {"replied", "escalated"}
VALID_REQUEST_TYPES = {"product_issue", "feature_request", "bug", "invalid"}


# ---------------------------------------------------------------------------
# 1. Context Formatter
# ---------------------------------------------------------------------------

def _format_context(hits: list[dict]) -> str:
    """Format retrieved chunks into a numbered context block for the LLM."""
    if not hits:
        return "No relevant context found in the support corpus."

    parts = []
    for i, hit in enumerate(hits, 1):
        header = f"[{i}] {hit['company']} — {hit['title']}"
        if hit.get("section_heading") and hit["section_heading"] != hit["title"]:
            header += f" ({hit['section_heading']})"
        header += f"\nSource: {hit['source_path']}"
        parts.append(f"{header}\n\n{hit['text']}")

    return "\n\n---\n\n".join(parts)


# ---------------------------------------------------------------------------
# 2. LLM Call (local Ollama or cloud Anthropic)
# ---------------------------------------------------------------------------

def _call_llm_local(system: str, user: str) -> str:
    """Call local Ollama LLM and return raw text response."""
    import ollama
    response = ollama.chat(
        model=LLM_MODEL_LOCAL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        options={"temperature": 0},
    )
    return response["message"]["content"]


def _call_llm_cloud(system: str, user: str) -> str:
    """Call Anthropic Claude and return raw text response."""
    import anthropic
    client = anthropic.Anthropic()
    message = client.messages.create(
        model=LLM_MODEL_CLOUD,
        max_tokens=1024,
        temperature=0,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return message.content[0].text


def call_llm(system: str, user: str) -> str:
    """Call the configured LLM backend and return raw text."""
    if PROVIDER == "cloud":
        return _call_llm_cloud(system, user)
    return _call_llm_local(system, user)


# ---------------------------------------------------------------------------
# 3. JSON Parser + Validator
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> dict:
    """
    Extract and validate the JSON object from LLM response text.
    Handles markdown fences and stray text before/after JSON.
    """
    # Strip markdown fences if present
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    text = re.sub(r"```\s*$", "", text).strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find first {...} block
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON from LLM response:\n{text[:500]}")


def _validate(data: dict) -> dict:
    """
    Validate and normalise the 5 required fields.
    Coerces values to lowercase where needed, fills defaults for missing fields.
    """
    status = str(data.get("status", "escalated")).lower().strip()
    if status not in VALID_STATUS:
        status = "escalated"

    request_type = str(data.get("request_type", "product_issue")).lower().strip()
    if request_type not in VALID_REQUEST_TYPES:
        request_type = "product_issue"

    product_area = str(data.get("product_area", "general")).strip()
    response = str(data.get("response", "")).strip()
    justification = str(data.get("justification", "")).strip()

    if not response:
        response = "This ticket has been escalated to our support team for further review."
    if not justification:
        justification = "No justification provided by the model."

    return {
        "status": status,
        "product_area": product_area,
        "response": response,
        "justification": justification,
        "request_type": request_type,
    }


def _parse_response(raw: str) -> dict:
    """Parse LLM response with one retry on failure."""
    try:
        return _validate(_extract_json(raw))
    except ValueError:
        pass

    # Retry: ask model to fix the JSON
    fix_prompt = (
        "Your previous response could not be parsed as JSON. "
        "Return ONLY a valid JSON object with these exact keys: "
        "status, product_area, response, justification, request_type. "
        "No other text."
    )
    retried = call_llm(SYSTEM_PROMPT, fix_prompt)
    try:
        return _validate(_extract_json(retried))
    except ValueError:
        # Hard fallback — return escalation so we never crash the pipeline
        return {
            "status": "escalated",
            "product_area": "unknown",
            "response": "We were unable to process this ticket automatically. It has been escalated to our support team.",
            "justification": "Agent failed to produce a valid structured response after retry.",
            "request_type": "product_issue",
        }


# ---------------------------------------------------------------------------
# 4. Query Expansion
# ---------------------------------------------------------------------------

_QUERY_EXPANSION_PROMPT = (
    "You are a search query generator for a support knowledge base.\n"
    "Given a support ticket, output a JSON array of exactly 3 short search queries "
    "(5-10 words each) that would retrieve the most relevant help articles.\n"
    "Queries should be diverse — rephrase and focus on different aspects of the issue.\n"
    "Return ONLY a JSON array of strings, e.g.: [\"query one\", \"query two\", \"query three\"]"
)


def _expand_queries(issue: str, subject: str, company: str) -> list[str]:
    """
    Ask the LLM to generate 3 focused search queries from the ticket.
    Returns those 3 queries plus the original concatenated query as fallback.
    Never raises — on any failure returns just the original query.
    """
    original = f"{subject} {issue}".strip()
    try:
        user_msg = f"Company: {company or 'Unknown'}\nSubject: {subject}\nIssue: {issue}"
        raw = call_llm(_QUERY_EXPANSION_PROMPT, user_msg)
        # Strip fences
        raw = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
        queries = json.loads(raw)
        if isinstance(queries, list) and queries:
            # Deduplicate while preserving order; always include original
            seen = set()
            result = []
            for q in queries:
                q = str(q).strip()
                if q and q.lower() not in seen:
                    seen.add(q.lower())
                    result.append(q)
            if original.lower() not in seen:
                result.append(original)
            return result
    except Exception:
        pass
    return [original]


def _retrieve_multi_query(
    queries: list[str], company: str | None, k: int
) -> list[dict]:
    """
    Run retrieve() for each query, merge results, deduplicate by chunk id,
    keep the highest score per chunk, return top-k sorted by score descending.
    """
    seen: dict[str, dict] = {}  # chunk_id → hit dict
    for query in queries:
        hits = retrieve(query=query, company=company, k=k)
        for hit in hits:
            cid = hit.get("id") or hit.get("source_path", "") + hit.get("section_heading", "")
            if cid not in seen or hit["score"] > seen[cid]["score"]:
                seen[cid] = hit

    merged = sorted(seen.values(), key=lambda h: h["score"], reverse=True)
    return merged[:k]



def process_ticket(issue: str, subject: str, company: str) -> dict:
    """
    Process a single support ticket end-to-end.

    Steps:
      1. Expand ticket into 3 search queries via LLM
      2. Multi-query retrieve, deduplicate, keep top-k by score
      3. Format chunks into a context block
      4. Build user message from issue + subject
      5. Call LLM with system prompt + context → parse JSON → return dict

    Returns dict with keys: status, product_area, response, justification, request_type
    """
    # Normalise inputs
    issue = (issue or "").strip()
    subject = (subject or "").strip()
    company_clean = (company or "").strip()
    # Treat "None" string as no company
    company_for_retrieval = None if company_clean.lower() in ("none", "", "null") else company_clean

    # Step 1: Expand into multiple search queries
    queries = _expand_queries(issue, subject, company_clean)

    # Step 2: Multi-query retrieve with deduplication
    hits = _retrieve_multi_query(
        queries=queries,
        company=company_for_retrieval,
        k=RETRIEVAL_TOP_K,
    )

    # Step 3: Format context
    context_block = _format_context(hits)

    # Step 4: Build user message
    user_message = f"""SUPPORT TICKET
Company: {company_clean or 'Unknown'}
Subject: {subject or '(no subject)'}
Issue: {issue or '(no issue text)'}

RETRIEVED CONTEXT
{context_block}"""

    # Step 5: Call LLM and parse
    raw = call_llm(SYSTEM_PROMPT, user_message)
    result = _parse_response(raw)
    return result


# ---------------------------------------------------------------------------
# Quick test helper (run directly: python agent.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    test_cases = [
        {
            "label": "Sample #1 — HackerRank tests active",
            "issue": "I notice that people I assigned the test in October of 2025 have not received new tests. How long do the tests stay active in the system.",
            "subject": "Test Active in the system",
            "company": "HackerRank",
            "expected_status": "replied",
            "expected_type": "product_issue",
        },
        {
            "label": "Sample #2 — Site down (escalate)",
            "issue": "site is down & none of the pages are accessible",
            "subject": "",
            "company": "None",
            "expected_status": "escalated",
            "expected_type": "bug",
        },
        {
            "label": "Sample #7 — Iron Man actor (invalid)",
            "issue": "What is the name of the actor in Iron Man?",
            "subject": "Urgent, please help",
            "company": "None",
            "expected_status": "replied",
            "expected_type": "invalid",
        },
    ]

    print(f"Running {len(test_cases)} test cases via {PROVIDER} backend...\n")
    all_passed = True

    for tc in test_cases:
        print(f"--- {tc['label']} ---")
        result = process_ticket(tc["issue"], tc["subject"], tc["company"])

        status_ok = result["status"] == tc["expected_status"]
        type_ok = result["request_type"] == tc["expected_type"]
        passed = status_ok and type_ok

        print(f"  status:       {result['status']} (expected: {tc['expected_status']}) {'✓' if status_ok else '✗'}")
        print(f"  request_type: {result['request_type']} (expected: {tc['expected_type']}) {'✓' if type_ok else '✗'}")
        print(f"  product_area: {result['product_area']}")
        print(f"  response:     {result['response'][:120]}...")
        print(f"  justification:{result['justification'][:120]}...")
        print(f"  PASS={passed}\n")

        if not passed:
            all_passed = False

    print("=" * 50)
    print(f"Result: {'ALL PASSED' if all_passed else 'SOME FAILURES — adjust system prompt'}")
    sys.exit(0 if all_passed else 1)
