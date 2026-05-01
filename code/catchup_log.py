"""
catchup_log.py — Flush ALL session turns to the log file.
Run once: python code/catchup_log.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from log_entry import append_entry, append_session_start

# Session start
append_session_start()

# T1: API key provided
append_entry(
    title="API key provided — agent.py built, all 3 quick tests passing",
    user_prompt="Now I have provided the Anthropic API key.",
    summary=(
        "Fixed .env (PROVIDER=cloud, removed duplicate keys). Updated model from deprecated "
        "claude-sonnet-4-20250514 to claude-sonnet-4-5 in config.py. Created code/agent.py "
        "with call_llm, _parse_response, _format_context, process_ticket. Fixed outage escalation "
        "rule (REPORTING vs asking). All 3 quick tests passed."
    ),
    actions=(
        "* .env: PROVIDER=local -> PROVIDER=cloud, removed duplicate keys\n"
        "* code/config.py: LLM_MODEL_CLOUD = claude-sonnet-4-5\n"
        "* code/config.py: outage escalation rule sharpened\n"
        "* code/agent.py: created"
    ),
)

# T2: Update task list
append_entry(
    title="TASKS.md updated — tasks 2.2/2.3/3.4.1 marked complete",
    user_prompt="Update the task list first.",
    summary=(
        "Marked tasks 2.2.1-2.2.4, 2.3.1-2.3.4, and 3.4.1 complete in TASKS.md to reflect "
        "all agent.py work done and PROVIDER=cloud already set."
    ),
    actions="* code/TASKS.md: marked 2.2.1-2.2.4, 2.3.1-2.3.4, 3.4.1 as [x]",
)

# T3: Submission format question
append_entry(
    title="User confirmed submission format: code zip + output.csv + log.txt",
    user_prompt=(
        "From the challenge page, I found: Submissions — Code zip, Predictions CSV, "
        "Chat transcript: the log.txt. Are you following the chat transcript?"
    ),
    summary=(
        "User shared official submission requirements. Confirmed log.txt at "
        "%USERPROFILE%/hackerrank_orchestrate/log.txt is being maintained. "
        "Noted terminal tool was disabled so some turns were missed; advised re-enabling "
        "or using log_entry.py helper."
    ),
    actions="* Reviewed log file status; identified missed turns",
)

# T4: How to enable terminal tool
append_entry(
    title="How to enable terminal tool in VS Code Copilot Chat",
    user_prompt="How to enable the terminal tool?",
    summary=(
        "Explained that the terminal tool toggle is in the tools icon (wrench) in "
        "the Copilot Chat input bar, requires Agent mode to be active."
    ),
    actions="* No file changes — informational response",
)

# T5: Can you enable the terminal tool
append_entry(
    title="User could not find terminal tool toggle",
    user_prompt="Can you enable the terminal tool?",
    summary="Cannot enable tools from the agent side; explained UI steps to find the toggle.",
    actions="* No file changes — informational response",
)

# T6: No terminal tool — alternative log approach
append_entry(
    title="Created log_entry.py and catchup_log.py as terminal-free logging alternative",
    user_prompt="I cannot find the terminal tools. Is there any other option to do the log as per the requirement of the hackathon?",
    summary=(
        "Created code/log_entry.py with append_entry() and append_session_start() so logs "
        "can be written without the terminal tool. Created code/catchup_log.py to backfill "
        "missed entries. User can also paste commands in VS Code integrated terminal (Ctrl+backtick)."
    ),
    actions=(
        "* code/log_entry.py: created\n"
        "* code/catchup_log.py: created"
    ),
)

# T7: Wrong path for catchup_log.py
append_entry(
    title="Corrected catchup_log.py path — must run from repo root as code/catchup_log.py",
    user_prompt="python catchup_log.py -- [Errno 2] No such file or directory",
    summary="User ran from wrong directory. Corrected to: python code/catchup_log.py.",
    actions="* No file changes — path correction",
)

# T8: Proceed with next task — main.py CSV pipeline
append_entry(
    title="main.py CSV pipeline built — 10/10 on sample validation after prompt tuning",
    user_prompt="Proceed with the next task.",
    summary=(
        "Built code/main.py with read_tickets(), write_output(), run_pipeline(), "
        "print_validation(), and CLI (--sample, --validate, --input flags). "
        "Fixed SAMPLE_EXPECTED array (had 3 wrong values from earlier). "
        "Identified and fixed 2 system prompt gaps: account deletion (Google login) and "
        "outage-report escalation. Achieved 10/10 on sample_support_tickets.csv."
    ),
    actions=(
        "* code/main.py: created\n"
        "* code/config.py: escalation rule for Google-login account deletion fixed\n"
        "* code/config.py: self-service path rule added to REPLY RULES"
    ),
)

# T9: Full 31-ticket run (first pass)
append_entry(
    title="Full 29-ticket run completed — reviewed classifications",
    user_prompt="Run and check the full 31 tickets.",
    summary=(
        "Ran python code/main.py on all 29 tickets (support_tickets.csv had 29 rows). "
        "Identified 2 request_type bugs: ticket #2 (score dispute) typed as invalid instead "
        "of product_issue; ticket #12 (vague) typed as invalid instead of product_issue. "
        "Fixed prompt: invalid type restricted to out-of-scope/pleasantry/injection only; "
        "vague tickets now escalated as product_issue. Re-validated 10/10 still passing."
    ),
    actions=(
        "* code/config.py: request_type=invalid scope clarified\n"
        "* code/config.py: vague ticket escalation type fixed to product_issue\n"
        "* support_tickets/output.csv: 29 rows written"
    ),
)

# T10: Prompt improvement analysis
append_entry(
    title="Prompt improvement analysis — 6 patterns identified across 31 tickets",
    user_prompt="Before full run, do you have any improvement idea on the prompt? Why are some cases failing?",
    summary=(
        "Reviewed all 29 full-run tickets and identified key failure patterns: "
        "impossible-demand tickets (score disputes, merchant bans) needed explicit escalation rule; "
        "refund demands needed explicit escalation; mixed Q+feature_request needed type guidance; "
        "canonical product_area values missing. Presented table of expected fixes per ticket."
    ),
    actions="* Analysis only — no file changes",
)

# T11: Apply prompt fixes
append_entry(
    title="3 prompt improvements applied — escalation, mixed-intent, product_area taxonomy",
    user_prompt="Apply the prompt fixes now first.",
    summary=(
        "Added refund/compensation escalation bullet; added impossible-action escalation bullet; "
        "added mixed-intent request_type rule; added canonical product_area value list for all "
        "3 companies. Re-validated 10/10 still passing."
    ),
    actions="* code/config.py: 3 SYSTEM_PROMPT sections updated",
)

# T12: Higher-reasoning model question
append_entry(
    title="Analysis: upgrading to Claude Opus has marginal accuracy gain vs 5x cost",
    user_prompt="I want to know if I upgrade the cloud model to a higher-reasoning model like CloudSonic, can the test case pass rate improve?",
    summary=(
        "Explained bottleneck is prompt rules and retrieval, not LLM reasoning. "
        "claude-sonnet-4-5 is sufficient for classification. Opus would improve prose quality "
        "but costs 5x more (~$2.50 vs $0.30 for 31 tickets) with marginal accuracy gain (+1-2 tickets). "
        "Recommended fixing prompt first."
    ),
    actions="* No file changes — analysis response",
)

# T13: Query expansion
append_entry(
    title="Query expansion implemented — multi-query retrieval with deduplication",
    user_prompt="Yes, I want to improve the query expansion.",
    summary=(
        "Added _expand_queries(): one LLM call with minimal prompt returns 3 diverse search queries. "
        "Added _retrieve_multi_query(): runs retrieve() per query, deduplicates by chunk id, "
        "keeps highest score, returns top-k. Updated process_ticket() to 5-step pipeline. "
        "Validated 10/10 still passing with expansion enabled."
    ),
    actions=(
        "* code/agent.py: added _QUERY_EXPANSION_PROMPT, _expand_queries(), _retrieve_multi_query()\n"
        "* code/agent.py: updated process_ticket() to use multi-query retrieval"
    ),
)

# T14: Export chat
append_entry(
    title="User asked how to export chat — log.txt is the required transcript",
    user_prompt="Can you export this chat?",
    summary=(
        "Clarified that log.txt at %USERPROFILE%/hackerrank_orchestrate/log.txt is the "
        "required transcript per AGENTS.md §2. Updated catchup_log.py to include all recent "
        "turns. VS Code has no built-in export; manual copy from chat panel is an option."
    ),
    actions="* code/catchup_log.py: updated with recent turns",
)

# T15: Write all the log
append_entry(
    title="catchup_log.py rewritten — all 15 session turns included",
    user_prompt="I want to write all the log",
    summary=(
        "Rewrote catchup_log.py to include every turn from this session (T1-T15) plus a "
        "session start entry. Running python code/catchup_log.py will flush all entries "
        "to the log file in one shot."
    ),
    actions="* code/catchup_log.py: full rewrite with all 15 turns",
)

print("All session turns written to log.")


# Turn: "Update the task list first"
append_entry(
    title="TASKS.md updated — Phase 2 tasks 2.2/2.3 marked complete",
    user_prompt="Update the task list first.",
    summary=(
        "Marked tasks 2.2.1-2.2.4 and 2.3.1-2.3.4 complete in TASKS.md to reflect "
        "the agent.py work done in the previous turn. Also marked 3.4.1 complete since "
        "PROVIDER=cloud was already set."
    ),
    actions="* code/TASKS.md: marked 2.2.1-2.2.4, 2.3.1-2.3.4, 3.4.1 as [x]",
)

# Turn: submission format question
append_entry(
    title="User asked about submission format (code zip + output.csv + log.txt)",
    user_prompt=(
        "From the challenge page, I found: Submissions ... Code zip ... "
        "Predictions CSV ... Chat transcript: the log.txt from the path in "
        "Chat transcript logging. Are you following the chat transcript?"
    ),
    summary=(
        "User shared the official submission requirements: code zip, output.csv, and log.txt. "
        "Confirmed that log entries ARE being written to %USERPROFILE%/hackerrank_orchestrate/log.txt "
        "via PowerShell Add-Content commands. Noted that terminal tool was disabled so some turns "
        "were missed; advised re-enabling terminal tool or using the new log_entry.py helper."
    ),
    actions="* Reviewed log file status; identified missed turns",
)

# Turn: how to enable terminal tool
append_entry(
    title="User asked how to enable terminal tool in VS Code Copilot",
    user_prompt="How to enable the terminal tool?",
    summary=(
        "Explained that the terminal tool toggle is in the tools icon (wrench) in the "
        "Copilot Chat input bar, and requires Agent mode to be active."
    ),
    actions="* No file changes — informational response only",
)

# Turn: couldn't find terminal tool
append_entry(
    title="User cannot find terminal tool — provided log_entry.py alternative",
    user_prompt="I cannot find the terminal tools. Is there any other option to do the log as per the requirement of the hackathon?",
    summary=(
        "Created code/log_entry.py as a standalone Python helper that appends §5.2-format "
        "entries to the log file without needing the terminal tool. Created code/catchup_log.py "
        "to backfill missed entries. User can also paste commands directly into VS Code's "
        "integrated terminal (Ctrl+backtick)."
    ),
    actions=(
        "* code/log_entry.py: created (append_entry, append_session_start helpers)\n"
        "* code/catchup_log.py: created (one-time backfill script)"
    ),
)


# Turn: prompt improvements analysis
append_entry(
    title="Prompt improvement analysis before full run",
    user_prompt="Before full run, do you have any improvement idea on the prompt? Why are some cases failing?",
    summary=(
        "Reviewed all 31 tickets and identified 3 prompt gaps: (1) impossible-action demands "
        "(score disputes, merchant bans) not covered by escalation rules, (2) refund demands "
        "not explicitly escalated, (3) vague tickets incorrectly typed as invalid. "
        "Also noted mixed-intent tickets and missing canonical product_area values."
    ),
    actions="* Analysis only — no file changes in this turn",
)

# Turn: apply prompt fixes
append_entry(
    title="Prompt fixes applied — escalation + request_type + product_area rules",
    user_prompt="Apply the prompt fixes now first.",
    summary=(
        "Applied 3 targeted improvements to SYSTEM_PROMPT in config.py: "
        "(1) added refund-demand and impossible-action escalation bullets, "
        "(2) added mixed-intent ticket handling rule, "
        "(3) added canonical product_area value taxonomy for all 3 companies. "
        "Re-validated 10/10 sample tickets still passing."
    ),
    actions="* code/config.py: 3 SYSTEM_PROMPT sections updated",
)

# Turn: upgrade to higher reasoning model question
append_entry(
    title="User asked about upgrading to higher-reasoning model",
    user_prompt="I want to know if I upgrade the cloud model to a higher-reasoning model like CloudSonic, can the test case pass rate improve?",
    summary=(
        "Explained that the bottleneck is prompt rules and retrieval quality, not LLM reasoning. "
        "claude-sonnet-4-5 is already sufficient for classification tasks. "
        "Claude Opus would improve prose quality but add 5x cost for marginal accuracy gain. "
        "Recommended fixing prompt first, then deciding on Opus for the final run."
    ),
    actions="* No file changes — informational response",
)

# Turn: query expansion improvement
append_entry(
    title="Query expansion implemented in agent.py",
    user_prompt="Yes, I want to improve the query expansion.",
    summary=(
        "Added _expand_queries() which makes one fast LLM call to generate 3 diverse search "
        "queries from the ticket. Added _retrieve_multi_query() which runs retrieve() for each "
        "query, deduplicates by source_path+section_heading, keeps highest score per chunk. "
        "Updated process_ticket() to use multi-query retrieval. Validated 10/10 still passing."
    ),
    actions="* code/agent.py: added _QUERY_EXPANSION_PROMPT, _expand_queries(), _retrieve_multi_query(); updated process_ticket()",
)

# Turn: export chat question
append_entry(
    title="User asked how to export the chat transcript",
    user_prompt="Can you export this chat?",
    summary=(
        "Explained that log.txt at %USERPROFILE%/hackerrank_orchestrate/log.txt IS the required "
        "transcript per AGENTS.md §2. VS Code has no built-in export. Updated catchup_log.py "
        "to flush all missed turns to the log file."
    ),
    actions="* code/catchup_log.py: added catch-up entries for recent turns",
)

print("All catch-up entries written.")
