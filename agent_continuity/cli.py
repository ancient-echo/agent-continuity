"""Command-line entrypoint for workspace checkpointing and targeted search."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import FIELDS, checkpoint, render_resume, resume, workspace_search
from .templates import RULES, SKILL


def _project(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_dir():
        raise ValueError(f"Not a directory: {path}")
    return path


def bootstrap(project: Path) -> list[str]:
    files = {
        project / ".agents" / "AGENTS.md": RULES,
        project / ".agents" / "skills" / "agent-continuity" / "SKILL.md": SKILL,
    }
    created = []
    for path, content in files.items():
        # Existing project rules are sacred; never replace them silently.
        if path.exists():
            created.append(f"PRESERVED {path.relative_to(project)} (exists; merge manually if needed)")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        created.append(f"CREATED   {path.relative_to(project)}")
    return created


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-continuity", description="Local task checkpoints and bounded workspace search for AI coding agents")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init", help="Add compatible rules and Skill to a project; never overwrite existing files")
    p.add_argument("--project", default=".")

    p = sub.add_parser("checkpoint", help="Create/update a local checkpoint; append facts by default")
    p.add_argument("--project", default=".")
    p.add_argument("--goal", help="Task goal (required for first checkpoint)")
    p.add_argument("--reset", action="store_true", help="Intentionally replace the entire checkpoint")
    p.add_argument("--resolve-next", action="append", default=[], help="Mark an existing next step completed (exact text)")
    for arg in ("decision", "constraint", "done", "verified", "next", "question"):
        p.add_argument("--" + arg, action="append", default=[], help=f"Repeatable {arg} entry")

    p = sub.add_parser("resume", help="Print prior task notes with Git drift warnings")
    p.add_argument("--project", default=".")
    p.add_argument("--json", action="store_true", help="Output machine-readable state and warnings")

    p = sub.add_parser("locate", help="Batch-search filenames and lines; emit only paths and line numbers")
    p.add_argument("query", help="Substring to find in path or text")
    p.add_argument("--project", default=".")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--max-files", type=int, default=5000)
    p.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        project = _project(args.project)
        if args.command == "init":
            print("\n".join(bootstrap(project)))
        elif args.command == "checkpoint":
            fields = {"decisions": args.decision, "constraints": args.constraint,
                      "completed": args.done, "verified": args.verified,
                      "next_steps": args.next, "open_questions": args.question}
            state = checkpoint(project, goal=args.goal, reset=args.reset, resolve_next=args.resolve_next, **fields)
            print(f"Checkpoint saved locally: .agent-continuity/state.json; "
                  f"goal={state['goal']!r}, entries={sum(len(state[k]) for k in FIELDS)}")
        elif args.command == "resume":
            report = resume(project)
            if args.json:
                print(json.dumps(report, ensure_ascii=False, indent=2))
            else:
                print(render_resume(report))
        elif args.command == "locate":
            report = workspace_search(project, args.query, limit=args.limit, max_files=args.max_files)
            if args.json:
                print(json.dumps(report, ensure_ascii=False, indent=2))
            else:
                for hit in report["results"]:
                    number = ":" + str(hit["line"]) if hit["line"] is not None else ""
                    print(f"{hit['path']}{number} [{hit['kind']}]")
                if not report["results"]:
                    print("No matches in the bounded scan.")
                if report["file_scan_truncated"] or report["max_results_reached"]:
                    print("NOTE: Search was truncated by configured limit(s).", file=sys.stderr)
                if report["skipped_large_files"]:
                    print(f"NOTE: Skipped {report['skipped_large_files']} large files.", file=sys.stderr)
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"agent-continuity: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
