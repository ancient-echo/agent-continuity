"""Portable, dependency-free core for local agent continuity.

Never reads agent chat/session databases, never runs model calls or executes code.
All outputs are local. Subprocesses use fixed git argv with no shell.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

STATE_DIR = ".agent-continuity"
STATE_FILE = "state.json"
MAX_FINGERPRINT_BYTES = 4_000_000
MAX_SEARCH_BYTES = 256_000
IGNORED_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "node_modules", "dist",
    "build", "__pycache__", ".next", "coverage", ".agent-continuity",
}
BLOCKED_NAMES = {".env", ".npmrc", ".pypirc", "id_rsa", "id_ed25519", "credentials.json", "auth.json"}
BLOCKED_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".sqlite", ".db", ".lock")
FIELDS = ("decisions", "constraints", "completed", "verified", "next_steps", "open_questions")


def _git(project: Path, *args: str) -> tuple[bool, bytes]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(project), *args], stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, timeout=8, check=False,
        )
        return proc.returncode == 0, proc.stdout
    except (OSError, subprocess.TimeoutExpired):
        return False, b""


def _candidate_file(project: Path, relative: str) -> Path | None:
    """Reject unsafe search paths, symlinks and sensitive filenames by default."""
    p = Path(relative)
    if p.is_absolute() or ".." in p.parts or not p.parts:
        return None
    if any(part in IGNORED_DIRS for part in p.parts[:-1]):
        return None
    name = p.name.lower()
    if name in BLOCKED_NAMES or name.startswith(".env.") or name.endswith(BLOCKED_SUFFIXES):
        return None
    path = project / p
    if path.is_symlink() or not path.is_file():
        return None
    return path


def file_candidates(project: Path, max_files: int = 5000) -> tuple[list[str], bool]:
    ok, output = _git(project, "ls-files", "-c", "-o", "--exclude-standard", "-z")
    if ok:
        raw = [os.fsdecode(x) for x in output.split(b"\0") if x]
    else:
        raw = []
        for base, dirs, files in os.walk(project, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in IGNORED_DIRS and not (Path(base) / d).is_symlink())
            for name in sorted(files):
                raw.append(str((Path(base) / name).relative_to(project)))
                if len(raw) > max_files * 2:
                    break
            if len(raw) > max_files * 2:
                break
    results = []
    truncated = False
    for value in sorted(set(raw)):
        if _candidate_file(project, value) is None:
            continue
        if len(results) >= max_files:
            truncated = True
            break
        results.append(value)
    return results, truncated


def workspace_search(project: Path, query: str, limit: int = 20, max_files: int = 5000) -> dict:
    """One bounded CLI invocation, returning filename and line-number hits.

    No snippets by default: avoid leaking credential-like values into agent context.
    Only text files <=256kB scanned; never traverses symlinked files or folders.
    """
    if not query.strip():
        raise ValueError("Search query must not be empty")
    if not 1 <= limit <= 200 or not 1 <= max_files <= 100000:
        raise ValueError("limit must be 1..200 and max_files must be 1..100000")
    candidates, truncated = file_candidates(project, max_files=max_files)
    needle = query.casefold()
    matches = []
    skipped_large = 0
    for relative in candidates:
        if len(matches) >= limit:
            break
        path = _candidate_file(project, relative)
        if path is None:
            continue
        if needle in relative.casefold():
            matches.append({"path": relative, "line": None, "kind": "filename"})
            if len(matches) >= limit:
                break
        try:
            size = path.stat().st_size
            if size > MAX_SEARCH_BYTES:
                skipped_large += 1
                continue
            data = path.read_bytes()
            if b"\0" in data[:4096]:
                continue
            content = data.decode("utf-8", errors="replace")
        except (OSError, UnicodeError):
            continue
        for n, line in enumerate(content.splitlines(), 1):
            if needle in line.casefold():
                matches.append({"path": relative, "line": n, "kind": "content"})
                if len(matches) >= limit:
                    break
    return {
        "query": query, "results": matches, "max_results_reached": len(matches) >= limit,
        "file_scan_truncated": truncated, "skipped_large_files": skipped_large,
    }


def snapshot(project: Path) -> dict:
    """Fuzzy Git workspace fingerprint. Explicitly not a guarantee of full equality."""
    success, head = _git(project, "rev-parse", "HEAD")
    if not success:
        return {"git_available": False, "head": None, "dirty_signature": None,
                "verification": "unavailable (not a Git worktree or git missing)"}
    ok, status = _git(project, "status", "--porcelain=v1", "--untracked-files=normal", "-z")
    if not ok:
        return {"git_available": True, "head": head.decode().strip(),
                "dirty_signature": None, "verification": "Git status unavailable"}
    hasher = hashlib.sha256(status)
    # Track modifications to dirty tracked files, including when the status list
    # stays unchanged. Bound diff bytes so we do not scan huge repositories.
    ok1, unstaged = _git(project, "diff", "--binary", "--no-ext-diff")
    ok2, staged = _git(project, "diff", "--cached", "--binary", "--no-ext-diff")
    if not (ok1 and ok2) or len(unstaged) + len(staged) > MAX_FINGERPRINT_BYTES:
        verification = "partial: diff unavailable or over size cap"
    else:
        hasher.update(unstaged)
        hasher.update(staged)
        verification = "best-effort: Git HEAD/status/diffs, not all file contents"
    # Include metadata of untracked files, without reading their contents. This
    # detects many edits but not edits preserving file size and mtime.
    items = status.split(b"\0")
    for item in items:
        if item.startswith(b"?? "):
            rel = os.fsdecode(item[3:])
            path = _candidate_file(project, rel)
            if path:
                try:
                    st = path.stat()
                    hasher.update(f"{rel}\0{st.st_size}\0{st.st_mtime_ns}".encode("utf-8", errors="replace"))
                except OSError:
                    pass
    return {"git_available": True, "head": head.decode().strip(),
            "dirty_signature": hasher.hexdigest(), "verification": verification}


def _state_path(project: Path) -> Path:
    return project / STATE_DIR / STATE_FILE


def read_state(project: Path) -> dict | None:
    path = _state_path(project)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Unsupported or malformed state schema")
    return data


def _ensure_git_excludes_local_state(project: Path) -> None:
    """Keep private checkpoints out of Git without touching project .gitignore."""
    ok, raw = _git(project, "rev-parse", "--path-format=absolute", "--git-path", "info/exclude")
    if not ok:
        return
    try:
        exclude_path = Path(os.fsdecode(raw).strip())
        exclude_path.parent.mkdir(parents=True, exist_ok=True)
        previous = exclude_path.read_text(encoding="utf-8") if exclude_path.exists() else ""
        marker = "/.agent-continuity/"
        if marker not in previous.splitlines():
            with exclude_path.open("a", encoding="utf-8") as f:
                if previous and not previous.endswith("\n"):
                    f.write("\n")
                f.write("# Agent Continuity: local private task checkpoint\n" + marker + "\n")
    except OSError:
        # If exclusion is blocked, resume will detect untracked state drift.
        pass


def checkpoint(project: Path, goal: str | None = None, reset: bool = False, resolve_next: list[str] | None = None, **items: list[str]) -> dict:
    """Append non-duplicate user/agent-authored facts; re-checkpoint Git state."""
    current = None if reset else read_state(project)
    if current is None:
        if not goal or not goal.strip():
            raise ValueError("First checkpoint requires --goal")
        current = {"schema_version": 1, "goal": goal.strip(), **{field: [] for field in FIELDS}}
    elif goal and goal.strip():
        current["goal"] = goal.strip()
    for field in FIELDS:
        values = items.get(field, []) or []
        if not isinstance(current.get(field), list):
            raise ValueError(f"Invalid state: {field} must be a list")
        for raw in values:
            val = raw.strip()
            if val and val not in current[field]:
                current[field].append(val)
    for value in resolve_next or []:
        if value not in current["next_steps"]:
            raise ValueError(f"Next step not found (exact match required): {value}")
        current["next_steps"].remove(value)
        done_entry = "Finished next step: " + value
        if done_entry not in current["completed"]:
            current["completed"].append(done_entry)
    current["recorded_at"] = datetime.now(timezone.utc).isoformat()
    _ensure_git_excludes_local_state(project)
    current["snapshot"] = snapshot(project)
    dest = _state_path(project)
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Local state is private by default. Avoid stdout exposure of note bodies.
    fd, tmp = tempfile.mkstemp(prefix=".state-", suffix=".tmp", dir=dest.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, dest)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    (dest.parent / ".gitignore").write_text("*\n!.gitignore\n", encoding="utf-8")
    return current


def resume(project: Path) -> dict:
    state = read_state(project)
    if not state:
        raise ValueError("No checkpoint found; run checkpoint --goal ... first")
    before = state.get("snapshot") or {}
    now = snapshot(project)
    warnings = []
    if before.get("git_available") != now.get("git_available"):
        warnings.append("Git availability changed; re-check current repository state.")
    elif not now["git_available"]:
        warnings.append("Git not available: cannot verify code changes since checkpoint.")
    else:
        if before.get("head") != now.get("head"):
            warnings.append("Git HEAD changed since checkpoint; verify prior assumptions.")
        if not before.get("dirty_signature") or not now.get("dirty_signature"):
            warnings.append("Workspace diff comparison unavailable; re-check relevant files.")
        elif before["dirty_signature"] != now["dirty_signature"]:
            warnings.append("Workspace changes detected since checkpoint; re-check affected files.")
        if "partial" in now.get("verification", "") or "partial" in before.get("verification", ""):
            warnings.append("Git fingerprint is partial; treat matching fingerprints as inconclusive.")
    return {"state": state, "current_snapshot": now, "warnings": warnings,
            "status": "review_required" if warnings else "best_effort_match"}


def render_resume(report: dict) -> str:
    state = report["state"]
    lines = ["# Agent Continuity — task checkpoint", "", "Goal: " + state["goal"],
             "Recorded (UTC): " + state.get("recorded_at", "unknown"),
             "Verification: " + report["current_snapshot"].get("verification", "unknown"),
             "Status: " + report["status"], ""]
    for field, title in (("decisions", "Decisions"), ("constraints", "Constraints"),
                         ("completed", "Completed"), ("verified", "Actually verified"),
                         ("next_steps", "Next steps"), ("open_questions", "Open questions")):
        lines.append(f"## {title}")
        values = state.get(field, [])
        lines.extend("- " + x for x in values) if values else lines.append("- (not recorded)")
        lines.append("")
    lines.append("## Revalidation warnings")
    lines.extend("- " + w for w in report["warnings"]) if report["warnings"] else lines.append(
        "- No difference detected by the best-effort fingerprint. This is not proof all files are unchanged."
    )
    lines.append("\nNever infer that a completed step was verified unless listed under Actually verified.")
    return "\n".join(lines)
