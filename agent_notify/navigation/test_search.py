import importlib.util
import json
import unittest
from unittest.mock import patch
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('search', Path(__file__).with_name('search.py'))
search = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(search)


class SearchTests(unittest.TestCase):
    def test_remote_identity_matches_ssh_and_https(self):
        for remote in ['git@github.com:Owner/Repo.git', 'https://github.com/Owner/Repo.git',
                       'ssh://git@github.com/Owner/Repo.git']:
            self.assertEqual(search.repository_identity(remote), 'github.com/owner/repo')

    def test_branch_history_has_independent_keys_and_stable_repeats(self):
        stored_options = {}
        def fake_run(command, check=False):
            if command[0] == 'git':
                return 'git@github.com:owner/repo.git' if 'remote' in command else 'first'
            stored_options[command[-2]] = json.loads(command[-1])
            return ''
        with patch.object(search, 'run', side_effect=fake_run):
            for branch in ['first', 'second', 'first']:
                search.record_branch('%42', '/repo', branch)
        self.assertEqual(len(stored_options), 2)
        self.assertEqual({value['branch'] for value in stored_options.values()}, {'first', 'second'})

    def test_tool_workdir_is_recorded_alongside_agent_directory(self):
        self.assertEqual(search.observed_directories({
            'cwd': '/repo', 'tool_input': {'workdir': '../worktree'}}), ['/repo', '/repo/../worktree'])
        self.assertEqual(search.observed_directories({'cwd': '/repo'}), ['/repo'])

    def test_hook_observation_does_not_erase_explicit_pr_url(self):
        stored_options = {}
        def fake_run(command, check=False):
            if command[0] == 'git':
                return 'git@github.com:owner/repo.git' if 'remote' in command else 'feature'
            stored_options[command[-2]] = json.loads(command[-1])
            return ''
        with patch.object(search, 'run', side_effect=fake_run), \
             patch.object(search, 'resolve_pr', return_value=('github.com/owner/repo', 'feature')):
            search.record_branch('%42', '/repo', 'https://github.com/owner/repo/pull/7')
            search.record_branch('%42', '/repo')
        self.assertTrue(any(association.get('url') for association in stored_options.values()))

    def test_pr_resolves_head_repository_including_forks(self):
        with patch.object(search, 'run', return_value=json.dumps({
            'head': {'repo': {'full_name': 'Fork/Repo'}, 'ref': 'feature'}})) as request:
            self.assertEqual(search.resolve_pr('https://github.com/base/repo/pull/123/files'),
                             ('github.com/fork/repo', 'feature'))
        self.assertEqual(request.call_args.args[0], ['gh', 'api', 'repos/base/repo/pulls/123'])

    def test_explicit_pr_link_retains_url(self):
        with patch.object(search, 'resolve_pr', return_value=('github.com/owner/repo', 'feature')), \
             patch.object(search, 'run', return_value='') as commands:
            search.record_branch('%42', '/repo', 'https://github.com/owner/repo/pull/7')
        association = json.loads(commands.call_args.args[0][-1])
        self.assertEqual(association['url'], 'https://github.com/owner/repo/pull/7')

    def test_pr_lookup_offers_all_matching_agents_and_targets_popup_client(self):
        pane_rows = [
            {'pane': '%1', 'label': 'one', 'command': 'claude', 'associations': [
                {'repository': 'github.com/owner/repo', 'branch': 'old'},
                {'repository': 'github.com/owner/repo', 'branch': 'new'}]},
            {'pane': '%2', 'label': 'two', 'command': 'codex', 'associations': [
                {'repository': 'github.com/owner/repo', 'branch': 'old'}]},
            {'pane': '%3', 'label': 'other', 'command': 'codex', 'associations': [
                {'repository': 'github.com/other/repo', 'branch': 'old'}]},
        ]
        with patch.object(search, 'collect_and_record_pane_rows', return_value=pane_rows), \
             patch.object(search, 'choose_row', side_effect=[
                 'https://github.com/owner/repo/pull/7', search.format_row(pane_rows[1])]) as chooser, \
             patch.object(search, 'resolve_pr', return_value=('github.com/owner/repo', 'old')), \
             patch.object(search, 'run', return_value='') as commands:
            search.pick_pane('/dev/ttys123')
        self.assertEqual(chooser.call_args.args[0], pane_rows[:2])
        self.assertEqual(commands.call_args_list[0].args[0],
                         ['tmux', 'switch-client', '-c', '/dev/ttys123', '-t', '%2'])
        self.assertEqual(commands.call_args_list[1].args[0], ['tmux', 'select-pane', '-t', '%2'])

    def test_cancel_does_not_switch_and_missing_pr_is_reported(self):
        with patch.object(search, 'collect_and_record_pane_rows', return_value=[]), \
             patch.object(search, 'choose_row', return_value=''), \
             patch.object(search, 'run') as commands:
            search.pick_pane('client')
            commands.assert_not_called()
        with patch.object(search, 'collect_and_record_pane_rows', return_value=[]), \
             patch.object(search, 'choose_row', return_value='https://github.com/owner/repo/pull/7'), \
             patch.object(search, 'resolve_pr', return_value=('github.com/owner/repo', 'feature')):
            with self.assertRaisesRegex(ValueError, 'No live pane'):
                search.pick_pane('client')


if __name__ == '__main__':
    unittest.main()
