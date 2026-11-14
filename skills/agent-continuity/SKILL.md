---
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
