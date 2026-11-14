# Agent Continuity

**Recover coding-task context after compaction, and stop exploring the same workspace repeatedly.**

A small, independent, local-first toolkit originally motivated by **Google Antigravity** IDE/CLI behavior, compatible with other coding agents that can use workspace rules, Agent Skills, and terminal commands.

> **v0.1 experimental prototype, not an official Google product.** We have **not** proven real-world reductions in token use, file-reading calls, lost memory, or wall-clock time. Please report both failures and successes.

## The problem

Two recurring agent-workflow pain points:
- Context compaction can discard important decisions, constraints, or progress; agents waste time rediscovering them.
- Agents may read many files sequentially rather than locate a relevant symbol with one targeted search.

Agent Continuity tackles both with explicit **local task checkpoints** and **bounded workspace search**. It does not patch Antigravity's internal harness or interrupt automatic compaction.

## Quick start

Requirements: **Python 3.10+**, optional Git. No runtime dependencies, API key, or telemetry server.

```bash
git clone https://github.com/ancient-echo/agent-continuity.git
cd agent-continuity
python -m pip install .

# Add the Skill and workspace rules to YOUR project (not the cloned tool repo):
agent-continuity init --project /path/to/your-project

# Record the task after important decisions/milestones:
agent-continuity checkpoint --project /path/to/your-project \
  --goal "Fix login timeout without changing the API" \
  --constraint "Keep existing authentication semantics" \
  --decision "Use the existing retry utility" \
  --done "Identified the request path" \
  --verified "Existing authentication test passed" \
  --next "Implement bounded retries"

# After agent context compaction / new session:
agent-continuity resume --project /path/to/your-project

# Locate code in one bounded terminal command:
agent-continuity locate "retry_request" --project /path/to/your-project
```

Alternative without installing: from the cloned repository, use `python -m agent_continuity` with the same subcommands. On **Windows PowerShell**, enter a command on one line instead of using the Unix `\` continuation shown above.

### Antigravity integration

The raw [Skill file](skills/agent-continuity/SKILL.md) and [workspace rules](examples/AGENTS.md) are also available for manual installation.

`init` creates (only if absent):

- `.agents/AGENTS.md` — short workspace rules to avoid whole-workspace reads and encourage checkpoints.
- `.agents/skills/agent-continuity/SKILL.md` — an optional skill for resuming and targeted search.

**Existing files are preserved**, never overwritten. If your project already has `.agents/AGENTS.md`, merge the supplied recommendations manually. Existing `AGENTS.md` or `GEMINI.md` remains in place. Restart/reload Antigravity customizations after adding a Skill if necessary.

Google's official Antigravity docs confirm workspace `AGENTS.md` / `GEMINI.md` and `.agents/skills/<name>/SKILL.md` support:
- https://antigravity.google/docs/rules/
- https://antigravity.google/docs/skills

On a new Antigravity session, try asking: "Use the agent-continuity skill to resume this task; check changes before proceeding." Depending on the surface, you can also invoke a skill by name in the UI.

### Commands

| Command | Behavior |
|---|---|
| `init` | Add workspace rules and Skill without replacing existing ones |
| `checkpoint` | Create/update one local task checkpoint; append items by default |
| `resume` | Print recorded goal, decisions, constraints, verified results and Git drift warnings |
| `locate QUERY` | Batch-search non-sensitive text filenames and line numbers, capped by file/result limits |

`checkpoint` is **explicit**: the agent must actually run it for a record to exist. An automatic context compaction event does not trigger this CLI. Use `--reset` deliberately to start a different task. `--next` values append. Mark a step complete with `agent-continuity checkpoint --resolve-next "Exact next step text"` (this moves it to Completed); use `--reset --goal "..."` only when starting a new task.

### Correctness and privacy

- Checkpoints are in `.agent-continuity/state.json`, locally excluded from Git through `.git/info/exclude` when available (and a local `.gitignore`); avoid putting credentials or sensitive personal data in checkpoint text. Check your own Git staging rules before committing.
- `locate` skips common secret files (`.env`, `*.pem`, keys), huge files, symlinks, binaries and ignored folders. It prints **paths and line numbers** by default, not matching source text. It is not a security scanner; do not use untrusted input paths or assume all secrets are recognized.
- Git comparison is **best effort**: it checks HEAD, tracked diffs and status metadata. It may miss edits outside the Git worktree or some untracked-file changes. A matching status is **not proof** that the state is current.
- The CLI has no network calls, doesn't read hidden agent session databases, doesn't run a model, and doesn't control Antigravity internal scheduling.
- It does not suppress mandatory tests or override agent/system instructions.

## Testing

```bash
python -m unittest discover -s tests -v
```

See [evaluation plan](docs/EVALUATION.md) and [contribution guide](CONTRIBUTING.md). We welcome reproducible failures and negative results; don't share unredacted logs or private project files.

## Roadmap

1. Real-world tests of correctness, post-compaction retention, file-read calls and time.
2. Structured checkpoints with richer step status and conflicts, beyond the initial `--resolve-next` support.
3. Optional safe contextual search ranking and incremental index for large repositories.
4. Better verification of dirty/untracked working tree state.
5. Platform-specific integration only where documented APIs make it possible.

**License:** MIT. Independent community project, not affiliated with or endorsed by Google or OpenAI.
