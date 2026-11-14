# Agent Continuity (workspace-scoped)

- Do not read the whole workspace by default. Start with a narrow filename or symbol search.
- Prefer a single bounded `agent-continuity locate '<symbol>'` terminal call to repeated file opens when available.
- At important milestones, record the current goal, decisions, constraints, completed actions, *actually verified* results, and next steps with `agent-continuity checkpoint`.
- If context was compacted, or you are unsure of task continuity, use `agent-continuity resume` first. Treat recorded notes as fallible, verify Git state and the relevant code.
- Do not claim that past tool calls or tests succeeded without evidence. If the checkpoint is missing, ask only for truly necessary context.
- Keep secrets and private content out of checkpoints. The checkpoint is a local file, not a substitute for your project's source of truth.
- Follow higher-priority safety rules, user requirements and mandatory tests.
