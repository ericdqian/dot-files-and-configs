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
            snapshot_path = Path(snapshot_directory, 'worktrees.json')
            picker.write_snapshot(snapshot_path, {'/feature': {'associations': [{'repository': 'github.com/owner/repo', 'branch': 'feature'}]},
                                                   '/other': {'associations': [{'repository': 'github.com/owner/repo', 'branch': 'feature-other'}]}},
                                  ['/feature\tfeature', '/other\tfeature-other'],
                                  {'repository_url': 'https://github.com/owner/repo'})
            with patch.object(worktrees.github, 'resolve_and_cache_pr', return_value=('github.com/fork/repo', 'feature')) as lookup, \
                 redirect_stdout(io.StringIO()) as output:
                picker.update_query_results(snapshot_path, 'https://github.com/owner/repo/pull/84/files')
            self.assertIn('/feature\t', output.getvalue())
            self.assertNotIn('/other\t', output.getvalue())
            lookup.assert_called_once_with('https://github.com/owner/repo/pull/84')

    def test_number_queries_resolve_in_current_repository(self):
        for query in ['84', '#84']:
            with self.subTest(query=query), \
                 patch.object(worktrees, 'run', return_value='https://github.com/owner/repo'), \
                 patch.object(worktrees.github, 'resolve_pr', return_value=('github.com/owner/repo', 'feature')) as lookup:
                self.assertEqual(worktrees.resolve_worktree_pr_branch(query), 'feature')
                lookup.assert_called_once_with('https://github.com/owner/repo/pull/84')

    def test_exact_numeric_branch_does_not_lookup_pr(self):
        with tempfile.TemporaryDirectory() as snapshot_directory:
            snapshot_path = Path(snapshot_directory, 'worktrees.json')
            picker.write_snapshot(snapshot_path, {'/numeric': {'exact_queries': ['84'], 'associations': []}, '/other': {'associations': []}},
                                  ['/numeric\t84', '/other\tfeature'], {'pr_numbers': True})
            with patch.object(worktrees.github, 'resolve_and_cache_pr') as lookup, redirect_stdout(io.StringIO()) as output:
                picker.update_query_results(snapshot_path, '84')
            self.assertEqual(output.getvalue(), '/numeric\t84\n')
            lookup.assert_not_called()

    def test_missing_worktree_is_visible_and_cannot_be_accepted(self):
        with tempfile.TemporaryDirectory() as snapshot_directory:
            snapshot_path = Path(snapshot_directory, 'worktrees.json')
            picker.write_snapshot(snapshot_path, {'/other': {'associations': []}}, ['/other\tother'],
                                  {'pr_numbers': True, 'repository_url': 'https://github.com/owner/repo',
                                   'missing_destination': 'No local worktree for branch {branch}.'})
            with patch.object(worktrees.github, 'resolve_and_cache_pr', return_value=('github.com/owner/repo', 'missing')), \
                 redirect_stdout(io.StringIO()) as output:
                picker.update_query_results(snapshot_path, '#84')
            self.assertIn('No local worktree', output.getvalue())
            self.assertEqual(json.loads(picker.query_result_path(snapshot_path, '#84').read_text()), [])
            self.assertNotEqual(picker.accept_action(snapshot_path, '#84', '!', ['/other'], False), 'accept')

    def test_porcelain_records_preserve_spaces_and_detached_worktrees(self):
        candidate_lines = worktrees.worktree_candidates(
            'worktree /feature checkout\0HEAD abc123\0branch refs/heads/feature\0\0'
            'worktree /detached checkout\0HEAD def456\0detached\0\0')
        self.assertEqual(candidate_lines, ['/feature checkout\tfeature', '/detached checkout\t'])

    def test_enter_cannot_accept_stale_pr_results(self):
        with tempfile.TemporaryDirectory() as snapshot_directory:
            snapshot_path = Path(snapshot_directory, 'worktrees.json')
            picker.query_result_path(snapshot_path, '#83').write_text('["/other"]')
            self.assertNotEqual(picker.accept_action(snapshot_path, '#84', '/other', ['/other'], False), 'accept')
            picker.query_result_path(snapshot_path, '#84').write_text('["/feature"]')
            self.assertEqual(picker.accept_action(snapshot_path, '#84', '/feature', ['/feature'], False), 'accept')


if __name__ == '__main__':
    unittest.main()
