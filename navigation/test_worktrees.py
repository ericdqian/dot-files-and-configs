import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from navigation import picker, worktrees


class WorktreePickerTests(unittest.TestCase):
    def test_url_query_uses_shared_cache_and_exact_branch(self):
        with tempfile.TemporaryDirectory() as snapshot_directory:
            snapshot_path = Path(snapshot_directory, 'candidates.txt')
            snapshot_path.write_text('/feature\tfeature\n/other\tfeature-other')
            with patch.object(worktrees, 'run', return_value='https://github.com/owner/repo'), \
                 patch.object(worktrees.github, 'resolve_and_cache_pr', return_value=('github.com/owner/repo', 'feature')) as lookup, \
                 redirect_stdout(io.StringIO()) as output:
                worktrees.update_worktree_query(snapshot_path, 'https://github.com/owner/repo/pull/84/files')
            self.assertEqual(output.getvalue(), '/feature\tfeature\n')
            lookup.assert_called_once_with('https://github.com/owner/repo/pull/84')

    def test_number_queries_resolve_in_current_repository(self):
        for query in ['84', '#84']:
            with self.subTest(query=query), \
                 patch.object(worktrees, 'run', return_value='https://github.com/owner/repo'), \
                 patch.object(worktrees.github, 'resolve_and_cache_pr', return_value=('github.com/owner/repo', 'feature')) as lookup:
                self.assertEqual(worktrees.resolve_worktree_pr_branch(query, use_cache=True), 'feature')
                lookup.assert_called_once_with('https://github.com/owner/repo/pull/84')

    def test_exact_numeric_branch_does_not_lookup_pr(self):
        with tempfile.TemporaryDirectory() as snapshot_directory:
            snapshot_path = Path(snapshot_directory, 'candidates.txt')
            snapshot_path.write_text('/numeric\t84\n/other\tfeature')
            with patch.object(worktrees.github, 'resolve_and_cache_pr') as lookup, redirect_stdout(io.StringIO()) as output:
                worktrees.update_worktree_query(snapshot_path, '84')
            self.assertEqual(output.getvalue(), '/numeric\t84\n')
            lookup.assert_not_called()

    def test_missing_worktree_is_visible_and_cannot_be_accepted(self):
        with tempfile.TemporaryDirectory() as snapshot_directory:
            snapshot_path = Path(snapshot_directory, 'candidates.txt')
            snapshot_path.write_text('/other\tother')
            with patch.object(worktrees, 'resolve_worktree_pr_branch', return_value='missing'), \
                 redirect_stdout(io.StringIO()) as output:
                worktrees.update_worktree_query(snapshot_path, '#84')
            self.assertIn('No local worktree', output.getvalue())
            self.assertEqual(json.loads(picker.query_result_path(snapshot_path, '#84').read_text()), [])
            self.assertNotEqual(picker.accept_action(snapshot_path, '#84', '!', ['/other'], False), 'accept')

    def test_enter_cannot_accept_stale_pr_results(self):
        with tempfile.TemporaryDirectory() as snapshot_directory:
            snapshot_path = Path(snapshot_directory, 'candidates.txt')
            picker.query_result_path(snapshot_path, '#83').write_text('["/other"]')
            self.assertNotEqual(picker.accept_action(snapshot_path, '#84', '/other', ['/other'], False), 'accept')
            picker.query_result_path(snapshot_path, '#84').write_text('["/feature"]')
            self.assertEqual(picker.accept_action(snapshot_path, '#84', '/feature', ['/feature'], False), 'accept')


if __name__ == '__main__':
    unittest.main()
