"""
main.py — CSV pipeline entry point.

Usage:
    python code/main.py                        # run on support_tickets.csv → output.csv
    python code/main.py --sample               # run on sample_support_tickets.csv only
    python code/main.py --validate             # run sample + print accuracy table
    python code/main.py --input path/to/f.csv  # custom input file

Output: support_tickets/output.csv
"""

import argparse
import csv
import sys
import time
from pathlib import Path

from config import INPUT_CSV, SAMPLE_CSV, OUTPUT_CSV
from agent import process_ticket

OUTPUT_COLUMNS = ["issue", "subject", "company", "response", "product_area",
                  "status", "request_type", "justification"]

# Expected values from sample file (for --validate)
SAMPLE_EXPECTED = [
    {"status": "replied",   "request_type": "product_issue", "product_area": None},  # 1
    {"status": "escalated", "request_type": "bug",           "product_area": None},  # 2
    {"status": "replied",   "request_type": "product_issue", "product_area": None},  # 3
    {"status": "replied",   "request_type": "product_issue", "product_area": None},  # 4
    {"status": "replied",   "request_type": "product_issue", "product_area": None},  # 5
    {"status": "replied",   "request_type": "product_issue", "product_area": None},  # 6
    {"status": "replied",   "request_type": "invalid",       "product_area": None},  # 7
    {"status": "replied",   "request_type": "product_issue", "product_area": None},  # 8
    {"status": "replied",   "request_type": "product_issue", "product_area": None},  # 9
    {"status": "replied",   "request_type": "invalid",       "product_area": None},  # 10
]


# ---------------------------------------------------------------------------
# CSV I/O
# ---------------------------------------------------------------------------

def read_tickets(path: Path) -> list[dict]:
    """Read input CSV, return list of dicts with keys: issue, subject, company."""
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "issue":   row.get("Issue", row.get("issue", "")).strip(),
                "subject": row.get("Subject", row.get("subject", "")).strip(),
                "company": row.get("Company", row.get("company", "")).strip(),
            })
    return rows


def write_output(rows: list[dict], path: Path) -> None:
    """Write output CSV with all 8 columns."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {len(rows)} rows → {path}")


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

def run_pipeline(tickets: list[dict], label: str = "") -> list[dict]:
    """Process every ticket through the agent, return output rows."""
    results = []
    total = len(tickets)
    for i, ticket in enumerate(tickets, 1):
        prefix = f"[{i}/{total}]"
        subj = ticket["subject"] or "(no subject)"
        co = ticket["company"] or "unknown"
        print(f"{prefix} {co} — {subj[:60]}", end=" ... ", flush=True)

        try:
            result = process_ticket(
                issue=ticket["issue"],
                subject=ticket["subject"],
                company=ticket["company"],
            )
            row = {
                "issue":        ticket["issue"],
                "subject":      ticket["subject"],
                "company":      ticket["company"],
                "response":     result["response"],
                "product_area": result["product_area"],
                "status":       result["status"],
                "request_type": result["request_type"],
                "justification": result["justification"],
            }
            print(f"{result['status']} / {result['request_type']}")
        except Exception as exc:
            print(f"ERROR: {exc}")
            row = {
                "issue":        ticket["issue"],
                "subject":      ticket["subject"],
                "company":      ticket["company"],
                "response":     "An error occurred processing this ticket. It has been escalated.",
                "product_area": "unknown",
                "status":       "escalated",
                "request_type": "product_issue",
                "justification": f"Pipeline error: {exc}",
            }

        results.append(row)
        # Small delay to avoid rate-limiting on rapid consecutive calls
        if i < total:
            time.sleep(0.5)

    return results


# ---------------------------------------------------------------------------
# Validation table
# ---------------------------------------------------------------------------

def print_validation(results: list[dict]) -> None:
    """Compare first N results against SAMPLE_EXPECTED, print accuracy table."""
    n = min(len(results), len(SAMPLE_EXPECTED))
    status_hits = 0
    type_hits = 0

    header = f"{'#':<3} {'Subject':<35} {'Exp Status':<12} {'Got Status':<12} {'Exp Type':<18} {'Got Type':<18} Match"
    print("\n" + "=" * len(header))
    print(header)
    print("=" * len(header))

    for i in range(n):
        r = results[i]
        e = SAMPLE_EXPECTED[i]
        s_match = r["status"] == e["status"]
        t_match = r["request_type"] == e["request_type"]
        both = s_match and t_match
        status_hits += s_match
        type_hits += t_match
        flag = "✓" if both else ("~" if (s_match or t_match) else "✗")
        subj = r["subject"][:33]
        print(f"{i+1:<3} {subj:<35} {e['status']:<12} {r['status']:<12} "
              f"{e['request_type']:<18} {r['request_type']:<18} {flag}")

    print("=" * len(header))
    print(f"Status accuracy:       {status_hits}/{n} ({100*status_hits//n}%)")
    print(f"Request type accuracy: {type_hits}/{n} ({100*type_hits//n}%)")
    print(f"Both correct:          {sum(1 for i in range(n) if results[i]['status']==SAMPLE_EXPECTED[i]['status'] and results[i]['request_type']==SAMPLE_EXPECTED[i]['request_type'])}/{n}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Support triage agent pipeline")
    parser.add_argument("--sample",   action="store_true", help="Run on sample CSV only")
    parser.add_argument("--validate", action="store_true", help="Run sample + print accuracy table")
    parser.add_argument("--input",    type=str,            help="Custom input CSV path")
    args = parser.parse_args()

    if args.input:
        input_path = Path(args.input)
    elif args.sample or args.validate:
        input_path = SAMPLE_CSV
    else:
        input_path = INPUT_CSV

    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    tickets = read_tickets(input_path)
    print(f"Loaded {len(tickets)} tickets from {input_path.name}")

    results = run_pipeline(tickets)
    write_output(results, OUTPUT_CSV)

    if args.validate:
        print_validation(results)


if __name__ == "__main__":
    main()
