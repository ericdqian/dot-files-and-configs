"""Exercise shell navigation against real worktrees without contacting GitHub."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class WorktreeNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary_directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary_directory.cleanup)
        cls.repository_path = Path(cls.temporary_directory.name).resolve() / "repository"
        cls.review_path = Path(cls.temporary_directory.name).resolve() / "review with spaces"
        cls.repository_path.mkdir()
        for git_arguments in (
            ["init", "-b", "main"],
            ["-c", "user.name=Test", "-c", "user.email=test@example.com",
             "commit", "--allow-empty", "-m", "initial"],
            ["worktree", "add", "-b", "review-branch", str(cls.review_path)],
        ):
            subprocess.run(["git", *git_arguments], cwd=cls.repository_path,
                           check=True, capture_output=True)
        config = (Path(__file__).resolve().parents[1] / "general_zsh_config").read_text()
        cls.navigation_functions = config[config.index("cwt() {"):config.index("dwt() {")]

    def run_shell(self, shell_command, **environment):
        return subprocess.run(
            ["zsh", "-f", "-c", self.navigation_functions + '''
gh() {
  if [[ "$1 $2" == 'repo view' ]]; then
    print -r -- https://github.com/example/repository
  elif [[ "$1 $2" == 'pr view' ]]; then
    [[ "$3" == "${EXPECTED_SELECTOR:-42}" ]] || return 90
    [[ -z "$GH_FAILURE" ]] || { print -u2 -- 'lookup failed'; return 1; }
    print -r -- "${PR_BRANCH-review-branch}"
  else
    return 91
  fi
}
fzf() { print -r -- "$*" >&2; head -n 1; }
cursor() { print -r -- "$1"; }
nvim() { pwd; }
''' + shell_command],
            cwd=self.repository_path, text=True, capture_output=True,
            env={**os.environ, **environment},
        )

    def test_pr_numbers(self):
        for selector in ("42", "#42"):
            with self.subTest(selector=selector):
                result = self.run_shell('cwt "$SELECTOR" && pwd', SELECTOR=selector)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), str(self.review_path))

    def test_pr_urls(self):
        canonical_url = "https://github.com/example/repository/pull/42"
        for suffix in ("", "/", "/files", "?tab=files", "#discussion-123"):
            with self.subTest(suffix=suffix):
                result = self.run_shell('cwt "$SELECTOR" && pwd',
                                        SELECTOR=canonical_url + suffix,
                                        EXPECTED_SELECTOR=canonical_url)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), str(self.review_path))

    def test_existing_branch_and_path(self):
        for selector in ("review-branch", "refs/heads/review-branch", str(self.review_path)):
            result = self.run_shell('cwt "$SELECTOR" && pwd', SELECTOR=selector,
                                    GH_FAILURE="1")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(self.review_path))

    def test_other_repository_url(self):
        result = self.run_shell('cwt https://github.com/other/repository/pull/42')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not belong", result.stderr)

    def test_missing_worktree_does_not_select_another(self):
        result = self.run_shell('cwt 42', PR_BRANCH="missing-branch")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no local worktree", result.stderr)
        self.assertNotIn("--prompt", result.stderr)

    def test_lookup_failure(self):
        result = self.run_shell('cwt 42', GH_FAILURE="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("lookup failed", result.stderr)
        self.assertNotIn("--prompt", result.stderr)

    def test_empty_branch(self):
        result = self.run_shell('cwt 42', PR_BRANCH="")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("could not resolve", result.stderr)

    def test_fuzzy_selection(self):
        result = self.run_shell('cwt review && pwd')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--query=review", result.stderr)

    def test_no_query(self):
        result = self.run_shell('cwt && pwd')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(self.repository_path))
        self.assertIn("--query=", result.stderr)

    def test_editor_helpers(self):
        for editor_function in ("ccwt", "cnwt"):
            result = self.run_shell(f"{editor_function} 42")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(self.review_path))


if __name__ == "__main__":
    unittest.main()
