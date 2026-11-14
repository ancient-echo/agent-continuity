# Contributing

We want reproducible evidence that agent continuity tools reduce repeated exploration **without sacrificing correctness**.

- Open an Issue with a minimal **non-sensitive** reproduction, platform details, observed versus expected result, and what agent actually did.
- Test with `python -m unittest discover -s tests -v`.
- Keep pull requests narrowly scoped. Never weaken user's requested verification, authorization, or security.
- Do not post raw prompts, private logs, API keys, private repository contents, or checkpoint files containing sensitive context.
- Please report negative results too. This project is not affiliated with Google or OpenAI.

## Questions we're testing

1. Do checkpoints lead to fewer lost requirements after automatic context compaction?
2. Does one bounded search reduce redundant source-file reads and agent tool calls?
3. Do these changes improve wall-clock time and token usage while preserving task quality?

A successful local unit test is **not** evidence that an AI agent's actual behavior improved. Real-agent A/B trials are required.
