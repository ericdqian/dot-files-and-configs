import importlib.util
import json
import unittest
import tempfile
import io
from contextlib import redirect_stdout
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
            if command[-2] != '@agent_nav_directory':
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
            if command[-2] != '@agent_nav_directory':
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

    def test_pick_targets_the_selected_pane_and_popup_client(self):
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
             patch.object(search, 'choose_row', return_value=search.format_row(pane_rows[1])), \
             patch.object(search, 'find_destination', return_value=('/dev/ttys123', None)), \
             patch.object(search, 'run', return_value='') as commands:
            search.pick_pane('/dev/ttys123')
        self.assertEqual(commands.call_args_list[0].args[0],
                         ['tmux', 'switch-client', '-c', '/dev/ttys123', '-t', '%2'])
        self.assertEqual(commands.call_args_list[1].args[0], ['tmux', 'select-pane', '-t', '%2'])

    def test_feedback_sessions_are_filtered_without_hiding_development_windows(self):
        pane_listing = '\n'.join([
            '%1\tclaude-pr-2351-security\tzsh\t0.0\t/review\t/review\tclaude',
            '%2\tcodex-pr-2351-correctness\tcodex\t0.0\t/review\t/review\tcodex',
            '%3\tcore\tPR review export\t184.0\t/repo\t/repo\tcodex',
        ])
        with patch.object(search, 'run', side_effect=[pane_listing, 'agent-pane %3']):
            pane_rows = search.collect_and_record_pane_rows()
        self.assertEqual([row['pane'] for row in pane_rows], ['%3'])
        self.assertEqual(pane_rows[0]['title'], 'PR review export')
        self.assertEqual(pane_rows[0]['location'], 'core:184.0')
        self.assertFalse(search.is_feedback_session('coding-agents'))

    def test_compact_rows_retain_searchable_history_and_preview_full_details(self):
        pane_row = {'pane': '%42', 'label': 'core:12.0 Example window', 'title': 'Example window',
                    'location': 'core:12.0', 'command': '2.1.302', 'directory': '/repo', 'associations': [
                        {'repository': 'github.com/owner/repo', 'branch': 'old'},
                        {'repository': 'github.com/owner/repo', 'branch': 'new',
                         'url': 'https://github.com/owner/repo/pull/7'}]}
        formatted_row = search.format_row(pane_row)
        self.assertEqual(formatted_row.count('owner/repo'), 1)
        self.assertIn('old, new', formatted_row)
        self.assertIn('claude', formatted_row)
        self.assertNotIn('https://', formatted_row)
        self.assertIn('/repo', search.format_details(pane_row))
        self.assertIn('https://github.com/owner/repo/pull/7', search.format_details(pane_row))

    def test_pr_query_resolves_results_before_enter_and_restores_text_search(self):
        with tempfile.TemporaryDirectory() as directory:
            preview_path = Path(directory, 'panes.json')
            preview_path.write_text(json.dumps({'%1': {'pane': '%1', 'associations': [
                {'repository': 'github.com/owner/repo', 'branch': 'feature'}]}}))
            Path(directory, 'candidates.txt').write_text('%1\tAuthor pane\n%2\tOther pane')
            with patch.object(search, 'resolve_pr', return_value=('github.com/owner/repo', 'feature')), \
                 redirect_stdout(io.StringIO()) as output:
                search.update_query_results(preview_path, 'https://github.com/owner/repo/pull/7')
            self.assertIn('%1\tAuthor pane', output.getvalue())
            self.assertIn('PR #7', output.getvalue())
            with redirect_stdout(io.StringIO()) as output:
                search.update_query_results(preview_path, 'Other pane')
            self.assertIn('%2\tOther pane', output.getvalue())

    def test_pr_query_reports_missing_history_and_api_errors_in_picker(self):
        with tempfile.TemporaryDirectory() as directory:
            preview_path = Path(directory, 'panes.json')
            preview_path.write_text('{}')
            Path(directory, 'candidates.txt').write_text('')
            with patch.object(search, 'resolve_pr', return_value=('github.com/owner/repo', 'absent')), \
                 redirect_stdout(io.StringIO()) as output:
                search.update_query_results(preview_path, 'https://github.com/owner/repo/pull/7')
            self.assertIn('No tmux pane has recorded absent', output.getvalue())
            with patch.object(search, 'resolve_pr', side_effect=ValueError('not found [404]')), \
                 redirect_stdout(io.StringIO()) as output:
                search.update_query_results(preview_path, 'https://github.com/owner/repo/pull/7')
            self.assertIn('PR lookup failed:', output.getvalue())

    def test_wezterm_destination_uses_existing_client_and_prefers_current_when_possible(self):
        panes = [{'tty_name': '/dev/one', 'pane_id': 0, 'tab_id': 1},
                 {'tty_name': '/dev/two', 'pane_id': 2, 'tab_id': 3}]
        clients = [['/dev/one', 'dotfiles'], ['/dev/two', 'core']]
        self.assertEqual(search.select_destination('core', clients, panes, '/dev/one'),
                         ('/dev/two', panes[1]))
        self.assertEqual(search.select_destination('dotfiles', clients, panes, '/dev/one'),
                         ('/dev/one', panes[0]))
        self.assertEqual(search.select_destination('detached', clients, panes, '/dev/one'),
                         ('/dev/one', panes[0]))

    def test_navigation_focuses_the_destination_wezterm_tab_and_split(self):
        with patch.object(search, 'find_destination', return_value=(
                '/dev/destination', {'pane_id': 0, 'tab_id': 7})), \
             patch.object(search, 'run') as commands:
            search.navigate_to_pane('%42', '/dev/origin')
        self.assertEqual([call.args[0] for call in commands.call_args_list], [
            ['tmux', 'switch-client', '-c', '/dev/destination', '-t', '%42'],
            ['tmux', 'select-pane', '-t', '%42'],
            ['wezterm', 'cli', 'activate-tab', '--tab-id', '7'],
            ['wezterm', 'cli', 'activate-pane', '--pane-id', '0'],
        ])

    def test_enter_rejects_stale_rows_while_query_results_are_updating(self):
        with tempfile.TemporaryDirectory() as directory:
            preview_path = Path(directory, 'panes.json')
            with redirect_stdout(io.StringIO()) as output:
                search.print_accept_action(preview_path, 'feature', '%1')
            self.assertNotEqual(output.getvalue().strip(), 'accept')
            search.query_result_path(preview_path, 'feature').write_text('["%2"]')
            with redirect_stdout(io.StringIO()) as output:
                search.print_accept_action(preview_path, 'feature', '%1')
            self.assertNotEqual(output.getvalue().strip(), 'accept')
            with redirect_stdout(io.StringIO()) as output:
                search.print_accept_action(preview_path, 'feature', '%2')
            self.assertEqual(output.getvalue().strip(), 'accept')

    def test_cancel_does_not_switch(self):
        with patch.object(search, 'collect_and_record_pane_rows', return_value=[]), \
             patch.object(search, 'choose_row', return_value=''), \
             patch.object(search, 'run') as commands:
            search.pick_pane('client')
            commands.assert_not_called()


if __name__ == '__main__':
    unittest.main()
