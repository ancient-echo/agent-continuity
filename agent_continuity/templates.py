"""Small checked-in equivalent installer templates, without overwriting user rules."""

RULES = """# Agent Continuity (workspace-scoped)

- Do not read the whole workspace by default. Start with a narrow filename or symbol search.
- Prefer a single bounded `agent-continuity locate '<symbol>'` terminal call to repeated file opens when available.
- At important milestones, record the current goal, decisions, constraints, completed actions, *actually verified* results, and next steps with `agent-continuity checkpoint`.
- If context was compacted, or you are unsure of task continuity, use `agent-continuity resume` first. Treat recorded notes as fallible, verify Git state and the relevant code.
- Do not claim that past tool calls or tests succeeded without evidence. If the checkpoint is missing, ask only for truly necessary context.
- Keep secrets and private content out of checkpoints. The checkpoint is a local file, not a substitute for your project's source of truth.
- Follow higher-priority safety rules, user requirements and mandatory tests.
"""

SKILL = """---
name: agent-continuity
description: Recover coding task state after context compaction, preserve decisions, and search workspaces without reading all files. Use in Antigravity or another compatible coding agent when the agent loses context, starts a large task, or needs to locate relevant code quickly.
---

# Agent Continuity

Use the `agent-continuity` CLI from the workspace terminal (Python 3.10+).

1. On resuming after compaction: run `agent-continuity resume --project .`, read its goal, constraints, decisions, verified results and next steps. Do not mistake unverified notes for facts.
2. If a warning says Git HEAD or workspace changed, inspect the relevant changed files before continuing.
3. When starting a task, search with `agent-continuity locate '<specific file, symbol or term>' --project .` instead of opening every source file. Read only the hits needed for the user request. If the term is unknown, inspect a narrow directory inventory or ask a clarifying question only if essential.
4. After a meaningful milestone, append facts using `agent-continuity checkpoint --project . --decision '...' --verified '...' --next '...'`. Initial checkpoint must include `--goal '...'`.
5. Separate completed work from actually verified tests. Re-run a test only when needed, not out of ritual.

Limitations: This skill does NOT intercept Antigravity's automatic compaction or control the IDE's internal tool scheduler. Checkpoints work only when actually written. No raw chat transcripts or hidden state are captured.
"""
