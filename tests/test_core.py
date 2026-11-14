"""Behavior-focused tests. No LLM calls, cloud service, or external dependencies."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from agent_continuity.cli import bootstrap, main
from agent_continuity.core import checkpoint, read_state, render_resume, resume, workspace_search


def run_git(path, *args):
    subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True)


class LocalWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_bootstrap_creates_rules_and_skill(self):
        result = bootstrap(self.root)
        self.assertTrue((self.root / ".agents" / "AGENTS.md").exists())
        self.assertTrue((self.root / ".agents" / "skills" / "agent-continuity" / "SKILL.md").exists())
        self.assertEqual(len(result), 2)

    def test_bootstrap_does_not_overwrite_existing(self):
        rules = self.root / ".agents" / "AGENTS.md"
        rules.parent.mkdir(parents=True)
        rules.write_text("USER INSTRUCTIONS", encoding="utf-8")
        bootstrap(self.root)
        self.assertEqual(rules.read_text(encoding="utf-8"), "USER INSTRUCTIONS")

    def test_first_checkpoint_requires_goal(self):
        with self.assertRaisesRegex(ValueError, "requires --goal"):
            checkpoint(self.root, decisions=["Use module A"])

    def test_checkpoint_append_deduplicates(self):
        checkpoint(self.root, goal="Fix parser", decisions=["Keep API"], constraints=["No dependencies"])
        checkpoint(self.root, decisions=["Keep API", "Use parse_v2"], verified=["test_parser passed"])
        state = read_state(self.root)
        self.assertEqual(state["goal"], "Fix parser")
        self.assertEqual(state["decisions"], ["Keep API", "Use parse_v2"])
        self.assertEqual(state["verified"], ["test_parser passed"])
        self.assertTrue((self.root / ".agent-continuity" / ".gitignore").exists())
        self.assertIn("test_parser passed", render_resume(resume(self.root)))

    def test_resolve_step_moves_it_to_completed(self):
        checkpoint(self.root, goal="Fix parser", next_steps=["Add tests"])
        checkpoint(self.root, resolve_next=["Add tests"])
        state = read_state(self.root)
        self.assertEqual(state["next_steps"], [])
        self.assertEqual(state["completed"], ["Finished next step: Add tests"])
        with self.assertRaisesRegex(ValueError, "Next step not found"):
            checkpoint(self.root, resolve_next=["Missing"])

    def test_reset_intentionally_drops_old_decisions(self):
        checkpoint(self.root, goal="Task one", decisions=["Old"])
        checkpoint(self.root, goal="Task two", reset=True, decisions=["New"])
        self.assertEqual(read_state(self.root)["decisions"], ["New"])

    def test_non_git_resume_marks_unverifiable(self):
        checkpoint(self.root, goal="Work")
        status = resume(self.root)
        self.assertEqual(status["status"], "review_required")
        self.assertTrue(any("Git not available" in item for item in status["warnings"]))

    def test_git_changed_file_detected(self):
        run_git(self.root, "init", "-q")
        run_git(self.root, "config", "user.name", "Tester")
        run_git(self.root, "config", "user.email", "tester@example.test")
        file = self.root / "core.py"
        file.write_text("VALUE = 1\n", encoding="utf-8")
        run_git(self.root, "add", "core.py")
        run_git(self.root, "commit", "-qm", "base")
        checkpoint(self.root, goal="Keep API", constraints=["No breaking changes"])
        self.assertEqual(resume(self.root)["status"], "best_effort_match")
        file.write_text("VALUE = 2\n", encoding="utf-8")
        self.assertEqual(resume(self.root)["status"], "review_required")
        self.assertTrue(any("Workspace changes detected" in x for x in resume(self.root)["warnings"]))

    def test_git_head_change_detected(self):
        run_git(self.root, "init", "-q")
        run_git(self.root, "config", "user.name", "Tester")
        run_git(self.root, "config", "user.email", "tester@example.test")
        (self.root / "README.md").write_text("a", encoding="utf-8")
        run_git(self.root, "add", "README.md")
        run_git(self.root, "commit", "-qm", "start")
        checkpoint(self.root, goal="Work")
        (self.root / "README.md").write_text("b", encoding="utf-8")
        run_git(self.root, "add", "README.md")
        run_git(self.root, "commit", "-qm", "second")
        self.assertTrue(any("HEAD changed" in x for x in resume(self.root)["warnings"]))

    def test_locate_returns_line_numbers_without_contents(self):
        (self.root / "src").mkdir()
        (self.root / "src" / "login.py").write_text("password = 'not-for-stdout'\ndef retry_request(): pass\n", encoding="utf-8")
        hits = workspace_search(self.root, "retry_request")
        self.assertEqual(hits["results"], [{"path": "src/login.py", "line": 2, "kind": "content"}])
        self.assertNotIn("not-for-stdout", str(hits))

    def test_locate_skips_secrets_and_symlinks(self):
        (self.root / ".env").write_text("SEARCHTOKEN=secret", encoding="utf-8")
        (self.root / "keys.pem").write_text("SEARCHTOKEN=secret", encoding="utf-8")
        (self.root / "safe.txt").write_text("SEARCHTOKEN visible", encoding="utf-8")
        try:
            (self.root / "link.txt").symlink_to(self.root / "safe.txt")
        except (OSError, NotImplementedError):
            pass
        report = workspace_search(self.root, "SEARCHTOKEN")
        self.assertEqual(report["results"], [{"path": "safe.txt", "line": 1, "kind": "content"}])

    def test_locate_limit_and_empty(self):
        (self.root / "src.py").write_text("hello\nhello\nhello\n", encoding="utf-8")
        self.assertTrue(workspace_search(self.root, "hello", limit=2)["max_results_reached"])
        with self.assertRaises(ValueError):
            workspace_search(self.root, "")

    def test_cli_exit_code_on_missing_checkpoint(self):
        self.assertEqual(main(["resume", "--project", str(self.root)]), 2)

    def test_skip_large_files(self):
        (self.root / "large.py").write_bytes(b"abc" * 100000)
        report = workspace_search(self.root, "abc")
        self.assertEqual(report["skipped_large_files"], 1)


if __name__ == "__main__":
    unittest.main()
