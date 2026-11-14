# Evaluation design (pre-registered objectives)

We explicitly do not claim improved Antigravity performance without trials.

## Trial setup

- Use a disposable repo with identical clean copies and the same task/model/permissions.
- Baseline copy has no Agent Continuity instructions. Treatment copy runs `agent-continuity init` and uses explicit checkpoints at milestones.
- Run 5+ tasks at different repository sizes, with repeated randomized trials if possible. If the platform lacks deterministic seeds, note this limitation.
- Use a task that crosses a real compaction boundary when measuring recovery; otherwise mark recovery *not tested*.

## Outcomes

1. **Correctness first:** human + automated check of task completion and regressions.
2. **Memory recovery:** count missed constraints or repeated decisions after compaction.
3. **Read efficiency:** number of source-file read tool calls, repeated reads with no intervening edits, bytes/tokens used.
4. **Time and cost:** total duration and platform-reported tokens, where available.
5. **Overhead:** checkpoint update cost, delays and information omitted in checkpoint.

Do not pretend to measure internal IDE tokens if the IDE provides no reliable numbers. Don't publish sensitive prompts or logs. A checkpoint may make a task worse; capture those failures.
