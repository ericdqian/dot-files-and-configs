import importlib.util
import json
import unittest
import tempfile
import io
import subprocess
import os
from contextlib import redirect_stdout
from unittest.mock import patch
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('search', Path(__file__).with_name('search.py'))
search = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(search)


class SearchTests(unittest.TestCase):
    def setUp(self):
        cache_directory = tempfile.TemporaryDirectory()
        self.addCleanup(cache_directory.cleanup)
        cache_environment = patch.dict(os.environ, {'XDG_CACHE_HOME': cache_directory.name})
        cache_environment.start()
        self.addCleanup(cache_environment.stop)

    def test_window_rows_use_active_pane_and_combine_sibling_prs(self):
        pane_rows = [
            {'pane': '%1', 'window': '@1', 'location': 'core:1.0', 'window_access': 100,
             'associations': [{'repository': 'github.com/owner/repo', 'branch': 'feature',
                               'source': 'claim', 'url': 'https://github.com/owner/repo/pull/80'}]},
            {'pane': '%2', 'window': '@1', 'location': 'core:1.1', 'active': True, 'window_access': 100,
             'associations': [{'repository': 'github.com/owner/repo', 'branch': 'other', 'source': 'claim'}]},
            {'pane': '%3', 'window': '@2', 'location': 'core:2.0', 'window_access': 200,
             'associations': []},
        ]
        original_rows = json.loads(json.dumps(pane_rows))
        window_rows = search.group_window_rows(pane_rows)
        self.assertEqual([row['pane'] for row in window_rows], ['%3', '%2'])
        self.assertEqual(window_rows[1]['location'], 'core:1')
        self.assertEqual([association['branch'] for association in search.navigation_associations(window_rows[1])],
                         ['feature', 'other'])
        self.assertEqual(window_rows[1]['associations'][0]['url'], 'https://github.com/owner/repo/pull/80')
        self.assertEqual(pane_rows, original_rows)

    def test_window_history_preserves_per_pane_claim_precedence(self):
        pane_rows = [
            {'pane': '%1', 'window': '@1', 'associations': [
                {'repository': 'github.com/owner/repo', 'branch': 'claimed', 'source': 'claim'},
                {'repository': 'github.com/owner/repo', 'branch': 'incidental', 'source': 'observed'}]},
            {'pane': '%2', 'window': '@1', 'associations': [
                {'repository': 'github.com/owner/repo', 'branch': 'sibling', 'source': 'observed'}]},
        ]
        window_row = search.group_window_rows(pane_rows)[0]
        self.assertEqual([association['branch'] for association in search.navigation_associations(window_row)],
                         ['claimed', 'sibling'])

    def test_window_owner_hides_other_branches_even_when_a_sibling_pane_is_active(self):
        window_owner = {'repository': 'github.com/owner/repo', 'branch': 'feature', 'source': 'claim'}
        pane_rows = [
            {'pane': '%1', 'window': '@1', 'window_owner': window_owner, 'associations': []},
            {'pane': '%2', 'window': '@1', 'active': True,
             'associations': [{'repository': 'github.com/owner/repo', 'branch': 'incidental'}]},
        ]
        window_row = search.group_window_rows(pane_rows)[0]
        self.assertEqual(window_row['pane'], '%2')
        self.assertEqual(search.navigation_associations(window_row), [window_owner])

    def test_collection_reads_window_ownership_and_skips_checkout_observations(self):
        window_owner = {'repository': 'github.com/owner/repo', 'branch': 'feature', 'source': 'claim'}
        pane_listing = '%1\tcore\tFeature\t0.0\t/other\t/repo\tzsh\t@1\t0\t0\t1'
        with patch.object(search, 'run', side_effect=[pane_listing, 'agent-pane %1\nagent-owner ' + json.dumps(window_owner)]), \
             patch.object(search, 'record_branch') as observations:
            pane_rows = search.collect_and_record_pane_rows()
        self.assertEqual(search.navigation_associations(pane_rows[0]), [window_owner])
        observations.assert_not_called()

    def test_claim_rejects_another_branch_or_checkout_in_the_same_window(self):
        window_owner = {'repository': 'github.com/owner/repo', 'branch': 'feature', 'checkout': '/feature'}
        for conflicting_owner in [{**window_owner, 'branch': 'other'}, {**window_owner, 'checkout': '/other'}]:
            with patch.object(search, 'run', side_effect=['@1', json.dumps(window_owner)]) as commands:
                with self.assertRaisesRegex(ValueError, 'already owns feature'):
                    search.claim_window('%1', conflicting_owner)
            self.assertEqual(commands.call_count, 2)

    def test_claim_rejects_a_duplicate_window_for_the_same_repository_and_branch(self):
        window_owner = {'repository': 'github.com/owner/repo', 'branch': 'feature', 'checkout': '/feature'}
        with patch.object(search, 'run', side_effect=['@1', '']), \
             patch.object(search, 'claimed_windows', return_value=[{'window': '@2', 'pane': '%2', 'owner': window_owner}]):
            with self.assertRaisesRegex(ValueError, 'already belongs to window @2'):
                search.claim_window('%1', window_owner)

    def test_window_listing_handles_a_final_unclaimed_window(self):
        window_owner = {'repository': 'github.com/owner/repo', 'branch': 'feature', 'checkout': '/feature'}
        with patch.object(search, 'run', return_value='@1\t%1\t' + json.dumps(window_owner) + '\n@2\t%2'):
            self.assertEqual(search.claimed_windows(), [{'window': '@1', 'pane': '%1', 'owner': window_owner}])

    def test_claim_refresh_preserves_pr_and_description_from_a_sibling_pane(self):
        window_owner = {'repository': 'github.com/fork/repo', 'branch': 'feature', 'checkout': '/feature',
                        'url': 'https://github.com/owner/repo/pull/7', 'description': 'Feature purpose'}
        with patch.object(search, 'run', side_effect=['@1', json.dumps(window_owner), '']) as commands, \
             patch.object(search, 'claimed_windows', return_value=[]):
            search.claim_window('%2', {'repository': 'github.com/owner/repo', 'branch': 'feature', 'checkout': '/feature'})
        recorded_owner = json.loads(commands.call_args.args[0][-1])
        self.assertEqual(recorded_owner, window_owner)

    def test_claim_rejects_a_second_pr_in_the_same_window(self):
        window_owner = {'repository': 'github.com/owner/repo', 'branch': 'feature', 'checkout': '/feature',
                        'url': 'https://github.com/owner/repo/pull/7'}
        with patch.object(search, 'run', side_effect=['@1', json.dumps(window_owner)]), \
             patch.object(search, 'claimed_windows', return_value=[]):
            with self.assertRaisesRegex(ValueError, 'different PR'):
                search.claim_window('%1', {**window_owner, 'url': 'https://github.com/owner/repo/pull/8'})

    def test_start_opens_window_in_source_session_using_existing_checkout(self):
        with patch.object(search, 'create_agent_worktree', return_value=Path('/existing')), \
             patch.object(search, 'claimed_windows', return_value=[]), \
             patch.object(search, 'record_branch') as claims, \
             patch.object(search, 'run', side_effect=['$7', 'git@github.com:owner/repo.git', '%99']) as commands, \
             redirect_stdout(io.StringIO()) as output:
            search.start_branch_window('%42', 'feature', '/proposed', 'main', 'Feature purpose', 'session-id')
        self.assertEqual(commands.call_args.args[0], ['tmux', 'new-window', '-d', '-P', '-F', '#{pane_id}',
                                                     '-t', '$7:', '-n', 'Feature purpose', '-c', '/existing'])
        claims.assert_called_once_with('%99', '/existing', source='claim', session_id='session-id', window_name='Feature purpose')
        self.assertIn('Pane: %99', output.getvalue())

    def test_start_reuses_owned_window_instead_of_creating_a_duplicate(self):
        window_owner = {'repository': 'github.com/owner/repo', 'branch': 'feature', 'checkout': '/existing'}
        with patch.object(search, 'create_agent_worktree', return_value=Path('/existing')), \
             patch.object(search, 'claimed_windows', return_value=[{'window': '@9', 'pane': '%99', 'owner': window_owner}]), \
             patch.object(search, 'record_branch') as claims, \
             patch.object(search, 'run', side_effect=['$7', 'git@github.com:owner/repo.git']) as commands, \
             redirect_stdout(io.StringIO()):
            search.start_branch_window('%42', 'feature', '/proposed', 'main')
        self.assertEqual(commands.call_count, 2)
        self.assertEqual(claims.call_args.args[:2], ('%99', '/existing'))

    def test_recent_windows_stay_grouped_with_recent_panes_first(self):
        pane_rows = [
            {'pane': '%1', 'window': '@1', 'window_access': 100, 'pane_access': 80},
            {'pane': '%3', 'window': '@2', 'window_access': 200, 'pane_access': 200},
            {'pane': '%2', 'window': '@1', 'window_access': 100, 'pane_access': 100},
            {'pane': '%4', 'window': '@2', 'window_access': 200, 'pane_access': 150},
        ]
        original_rows = json.loads(json.dumps(pane_rows))
        self.assertEqual([row['pane'] for row in search.sort_pane_rows_by_access(pane_rows)],
                         ['%3', '%4', '%2', '%1'])
        self.assertEqual(pane_rows, original_rows)

    def test_unvisited_windows_keep_stable_order_after_visited_windows(self):
        pane_rows = [
            {'pane': '%1', 'window': '@1'},
            {'pane': '%2', 'window': '@2'},
            {'pane': '%3', 'window': '@1'},
            {'pane': '%4', 'window': '@3', 'pane_access': 10},
        ]
        self.assertEqual([row['pane'] for row in search.sort_pane_rows_by_access(pane_rows)],
                         ['%4', '%1', '%3', '%2'])

    def test_record_access_targets_both_pane_and_its_window(self):
        with patch.object(search.time, 'time_ns', return_value=123456789), \
             patch.object(search, 'run') as commands:
            search.record_pane_access('%42')
        commands.assert_called_once_with([
            'tmux', 'set-option', '-p', '-t', '%42', '@agent_pane_access', '123456789', ';',
            'set-option', '-w', '-t', '%42', '@agent_window_access', '123456789'], check=True)
        with patch.object(search, 'run') as commands:
            with self.assertRaises(ValueError):
                search.record_pane_access('')
            commands.assert_not_called()

    def test_repository_choice_filters_exact_identity_and_can_be_cleared(self):
        pane_rows = [
            {'pane': '%1', 'label': 'other', 'command': 'codex', 'associations': [
                {'repository': 'github.com/owner/alpha', 'branch': 'feature'}]},
            {'pane': '%2', 'label': 'alpha', 'command': 'codex', 'associations': [
                {'repository': 'github.com/owner/beta', 'branch': 'alpha'}]},
        ]
        self.assertEqual(search.filter_repository_rows(pane_rows, 'github.com/owner/alpha'), [pane_rows[0]])
        self.assertEqual(search.filter_repository_rows(pane_rows, 'missing'), [])
        self.assertEqual(search.filter_repository_rows(pane_rows, ''), pane_rows)
        candidates = '\n'.join(search.format_row(row) for row in pane_rows)
        native_matches = search.run(['fzf', '--ansi', '--delimiter=\t', '--with-nth=2..', '--nth=5',
                                     '--filter', 'alpha'], input_text=candidates)
        self.assertEqual(native_matches.split('\t', 1)[0], '%1')

    def test_repository_dropdown_deduplicates_panes_and_excludes_incidental_observations(self):
        pane_rows = [
            {'pane': '%1', 'associations': [
                {'repository': 'github.com/owner/core', 'source': 'claim'},
                {'repository': 'github.com/owner/core', 'source': 'link'},
                {'repository': 'github.com/owner/observed', 'source': 'observed'}]},
            {'pane': '%2', 'associations': [{'repository': 'github.com/owner/core-api', 'source': 'claim'}]},
            {'pane': '%3', 'associations': [{'repository': 'github.com/owner/core', 'source': 'claim'}]},
        ]
        self.assertEqual(search.repository_options(pane_rows), [
            '*\tAll repositories\t(3 windows)',
            'github.com/owner/core\towner/core\t(2 windows)',
            'github.com/owner/core-api\towner/core-api\t(1 window)',
        ])
        self.assertEqual(search.filter_repository_rows(pane_rows, 'github.com/owner/core'),
                         [pane_rows[0], pane_rows[2]])

    def test_repository_dropdown_search_does_not_match_pane_counts(self):
        candidates = 'github.com/owner/other\towner/other\t(1 window)\ngithub.com/owner/repo\towner/repo\t(2 windows)'
        matches = search.run(['fzf', '--delimiter=\t', '--with-nth=2..', '--nth=1', '--filter', 'owner/repo'],
                             input_text=candidates)
        self.assertEqual(matches.split('\t', 1)[0], 'github.com/owner/repo')
        self.assertEqual(len(matches.splitlines()), 1)

    def test_repository_dropdown_uses_final_query_when_enter_beats_matching(self):
        pane_rows = [
            {'pane': '%1', 'label': 'Right', 'command': 'codex', 'associations': [
                {'repository': 'github.com/owner/repo', 'branch': 'first'}]},
            {'pane': '%2', 'label': 'Wrong', 'command': 'codex', 'associations': [
                {'repository': 'github.com/owner/other', 'branch': 'second'}]},
        ]
        picker_results = [subprocess.CompletedProcess([], 0, '\nctrl-d\n'),
                          subprocess.CompletedProcess([], 0, 'owner/repo\ngithub.com/owner/other\towner/other\n'),
                          subprocess.CompletedProcess([], 130, '')]
        with patch.object(search.subprocess, 'run', side_effect=picker_results) as pickers, \
             patch.object(search, 'run', return_value='github.com/owner/repo\towner/repo\t(1 window)'):
            search.choose_row(pane_rows)
        scoped_candidates = pickers.call_args_list[2].kwargs['input']
        self.assertIn('%1\t', scoped_candidates)
        self.assertNotIn('%2\t', scoped_candidates)

    def test_repository_editor_can_open_when_the_search_has_no_results(self):
        picker_results = [subprocess.CompletedProcess([], 1, '\nctrl-d\n'),
                          subprocess.CompletedProcess([], 0, '\n*\tAll repositories  (0 panes)\n'),
                          subprocess.CompletedProcess([], 130, '')]
        with patch.object(search.subprocess, 'run', side_effect=picker_results) as pickers, \
             patch.object(search, 'run', return_value=''):
            self.assertEqual(search.choose_row([]), '')
        self.assertIn('--prompt=Repository > ', pickers.call_args_list[1].args[0])
        self.assertEqual(pickers.call_count, 3)

    def test_ctrl_o_opens_recorded_prs_in_chrome_and_keeps_picker_open(self):
        pr_url = 'https://github.com/owner/repo/pull/80'
        pane_rows = [{'pane': '%1', 'label': 'Feature', 'command': 'codex', 'associations': [
            {'repository': 'github.com/owner/repo', 'branch': 'feature', 'source': 'claim', 'url': pr_url},
            {'repository': 'github.com/owner/repo', 'branch': 'other', 'source': 'link', 'url': pr_url},
            {'repository': 'github.com/owner/repo', 'branch': 'old', 'source': 'observed',
             'url': 'https://github.com/owner/repo/pull/1'}]}]
        picker_results = [subprocess.CompletedProcess([], 0, 'Feature\nctrl-o\n%1\tFeature\n'),
                          subprocess.CompletedProcess([], 130, '')]
        with patch.object(search.picker, 'run_picker', side_effect=picker_results) as pickers, \
             patch.object(search, 'run') as commands:
            self.assertEqual(search.choose_row(pane_rows), '')
        commands.assert_called_once_with(['open', '-a', 'Google Chrome', pr_url], check=True)
        self.assertEqual(pickers.call_args_list[1].args[1], 'Feature')

    def test_ctrl_o_without_a_pr_or_selection_shows_a_message(self):
        pane_rows = [{'pane': '%1', 'label': 'Shell', 'command': 'zsh', 'associations': []}]
        for selection_output in ['\nctrl-o\n%1\tShell\n', '\nctrl-o\n']:
            with self.subTest(selection_output=selection_output), \
                 patch.object(search.picker, 'run_picker', side_effect=[
                     subprocess.CompletedProcess([], 1, selection_output),
                     subprocess.CompletedProcess([], 130, '')]) as pickers, \
                 patch.object(search, 'run') as commands:
                self.assertEqual(search.choose_row(pane_rows), '')
                commands.assert_not_called()
                self.assertIn('No recorded PR for this selection.', pickers.call_args_list[1].args[2][-1])

    def test_pr_url_shortcut_requires_the_selected_row_to_match_the_resolved_query(self):
        pane_row = {'pane': '%1', 'associations': []}
        query = 'https://github.com/owner/repo/pull/80/files'
        with tempfile.TemporaryDirectory() as directory:
            preview_path = Path(directory, 'panes.json')
            self.assertEqual(search.selected_pr_urls(pane_row, query, preview_path), [])
            search.query_result_path(preview_path, query).write_text('["%2"]')
            self.assertEqual(search.selected_pr_urls(pane_row, query, preview_path), [])
            search.query_result_path(preview_path, query).write_text('["%1"]')
            self.assertEqual(search.selected_pr_urls(pane_row, query, preview_path),
                             ['https://github.com/owner/repo/pull/80'])

    def test_snapshot_scope_change_discards_previous_query_validations(self):
        with tempfile.TemporaryDirectory() as directory:
            preview_path = Path(directory, 'panes.json')
            search.query_result_path(preview_path, 'feature').write_text('["%2"]')
            preview_path.with_name('external-query').touch()
            pane_rows = [{'pane': '%1', 'label': 'Example', 'command': 'codex', 'associations': []}]
            search.write_picker_snapshot(preview_path, pane_rows, (30, 18, 24))
            self.assertFalse(search.query_result_path(preview_path, 'feature').exists())
            self.assertFalse(preview_path.with_name('external-query').exists())
            self.assertEqual(list(json.loads(preview_path.read_text())), ['%1'])
            self.assertEqual(json.loads(search.query_result_path(preview_path, '').read_text()), ['%1'])

    def test_branch_history_has_independent_keys_and_stable_repeats(self):
        stored_options = {}
        def fake_run(command, check=False):
            if command[0] == 'git':
                return 'git@github.com:owner/repo.git' if 'remote' in command else 'first'
            if command[1] == 'show-options':
                return json.dumps(stored_options[command[-1]]) if command[-1] in stored_options else ''
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
            if command[1] == 'show-options':
                return json.dumps(stored_options[command[-1]]) if command[-1] in stored_options else ''
            if command[-2] != '@agent_nav_directory':
                stored_options[command[-2]] = json.loads(command[-1])
            return ''
        with patch.object(search, 'run', side_effect=fake_run), \
             patch.object(search.github, 'resolve_pr', return_value=('github.com/owner/repo', 'feature')):
            search.record_branch('%42', '/repo', 'https://github.com/owner/repo/pull/7')
            search.record_branch('%42', '/repo')
        self.assertTrue(any(association.get('url') for association in stored_options.values()))

    def test_explicit_pr_link_retains_url(self):
        with patch.object(search.github, 'resolve_pr', return_value=('github.com/owner/repo', 'feature')), \
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
            '%1\tclaude-pr-2351-security\tzsh\t0.0\t/review\t/review\tclaude\t@1\t0\t0\t1',
            '%2\tcodex-pr-2351-correctness\tcodex\t0.0\t/review\t/review\tcodex\t@2\t0\t0\t1',
            '%3\tcore\tPR review export\t184.0\t/repo\t/repo\tcodex\t@3\t100\t90\t1',
        ])
        with patch.object(search, 'run', side_effect=[pane_listing, 'agent-pane %3']):
            pane_rows = search.collect_and_record_pane_rows()
        self.assertEqual([row['pane'] for row in pane_rows], ['%3'])
        self.assertEqual(pane_rows[0]['title'], 'PR review export')
        self.assertEqual(pane_rows[0]['location'], 'core:184.0')
        self.assertEqual(pane_rows[0]['window_access'], 100)
        self.assertEqual(pane_rows[0]['pane_access'], 90)
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
        self.assertIn('#7', formatted_row)
        self.assertNotIn('https://', formatted_row)
        self.assertIn('/repo', search.format_details(pane_row))
        self.assertIn('https://github.com/owner/repo/pull/7', search.format_details(pane_row))

    def test_pr_query_resolves_results_before_enter_and_restores_text_search(self):
        with tempfile.TemporaryDirectory() as directory:
            preview_path = Path(directory, 'panes.json')
            preview_path.write_text(json.dumps({'%1': {'pane': '%1', 'associations': [
                {'repository': 'github.com/owner/repo', 'branch': 'feature'}]}}))
            Path(directory, 'candidates.txt').write_text('%1\tAuthor pane\n%2\tOther pane')
            with patch.object(search.github, 'resolve_pr', return_value=('github.com/owner/repo', 'feature')), \
                 redirect_stdout(io.StringIO()) as output:
                search.update_query_results(preview_path, 'https://github.com/owner/repo/pull/7')
            self.assertIn('%1\t', output.getvalue())
            self.assertIn('Author pane', output.getvalue())
            self.assertIn('PR #7', output.getvalue())
            with redirect_stdout(io.StringIO()) as output:
                search.update_query_results(preview_path, 'Other pane')
            self.assertIn('%2\tOther pane', output.getvalue())

    def test_recorded_pr_url_search_is_local_and_prefers_claims(self):
        associations = [
            {'pane': '%1', 'associations': [{'repository': 'github.com/owner/repo', 'branch': 'feature',
                'source': 'observed', 'url': 'https://github.com/owner/repo/pull/7'}]},
            {'pane': '%2', 'associations': [{'repository': 'github.com/owner/repo', 'branch': 'feature',
                'source': 'claim', 'url': 'https://github.com/Owner/Repo/pull/7'}]},
            {'pane': '%3', 'associations': [{'repository': 'github.com/owner/repo', 'branch': 'feature',
                'source': 'claim'}]},
        ]
        with tempfile.TemporaryDirectory() as directory:
            preview_path = Path(directory, 'panes.json')
            preview_path.write_text(json.dumps({row['pane']: row for row in associations}))
            Path(directory, 'candidates.txt').write_text('%1\tObserved feature\n%2\tClaimed feature\n%3\tAnother claim')
            with patch.object(search.github, 'resolve_pr', side_effect=AssertionError('Unexpected GitHub lookup')), \
                 redirect_stdout(io.StringIO()) as output:
                search.update_query_results(preview_path, 'https://github.com/OWNER/repo/pull/7/files#review')
            self.assertIn('%2\t', output.getvalue())
            self.assertNotIn('%1\t', output.getvalue())
            self.assertIn('PR #7', output.getvalue())
            self.assertIn('%3\t', output.getvalue())

    def test_pr_query_reports_missing_history_and_api_errors_in_picker(self):
        with tempfile.TemporaryDirectory() as directory:
            preview_path = Path(directory, 'panes.json')
            preview_path.write_text('{}')
            Path(directory, 'candidates.txt').write_text('')
            with patch.object(search.github, 'resolve_pr', return_value=('github.com/owner/repo', 'absent')), \
                 redirect_stdout(io.StringIO()) as output:
                search.update_query_results(preview_path, 'https://github.com/owner/repo/pull/7')
            self.assertIn('No matching destination for branch absent', output.getvalue())
            with patch.object(search.github, 'resolve_pr', side_effect=ValueError('not found [404]')), \
                 redirect_stdout(io.StringIO()) as output:
                search.update_query_results(preview_path, 'https://github.com/owner/repo/pull/8')
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
                         (None, panes[0]))

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

    def test_unattached_session_opens_a_new_wezterm_tab_without_switching_origin(self):
        def fake_run(command, **kwargs):
            if command[1] == 'display-message':
                return '$7\t/tmp/isolated-tmux.sock'
            if command[:3] == ['wezterm', 'cli', 'spawn']:
                return '42'
            if command[:3] == ['wezterm', 'cli', 'list']:
                return '[{"pane_id":42,"tab_id":8,"window_id":2}]'
            return ''
        with patch.object(search, 'find_destination', return_value=(None, {'window_id': 2})), \
             patch.dict(search.os.environ, {'SHELL': '/test/bin/login-shell'}), \
             patch.object(search.shutil, 'which', side_effect=lambda executable: executable if executable.startswith('/') else '/test/bin/' + executable), \
             patch.object(search, 'run', side_effect=fake_run) as commands:
            search.navigate_to_pane('%9', '/dev/origin')
        executed_commands = [call.args[0] for call in commands.call_args_list]
        self.assertFalse(any(command[1] == 'switch-client' for command in executed_commands))
        self.assertIn(['wezterm', 'cli', 'spawn', '--window-id', '2', '--', '/test/bin/env', '-u', 'TMUX',
                       '-u', 'TMUX_PANE', '/bin/sh', '-c', '"$@"; exec "$0" -il', '/test/bin/login-shell',
                       '/test/bin/tmux', '-S', '/tmp/isolated-tmux.sock',
                       'attach-session', '-t', '$7'], executed_commands)
        self.assertEqual(executed_commands[-1], ['wezterm', 'cli', 'activate-pane', '--pane-id', '42'])

    def test_live_search_dispatch_only_reloads_for_prs_claims_and_mode_changes(self):
        pane_rows = [{'associations': [{'branch': 'feature', 'source': 'claim'}]}]
        with tempfile.TemporaryDirectory() as directory:
            preview_path = Path(directory, 'panes.json')
            change_command = search.picker.query_change_command('echo query', preview_path.with_name('candidates.txt'), exact_queries=['feature'])
            def changed_query(query):
                return subprocess.check_output(['/bin/sh', '-c', change_command], text=True,
                                               env={**os.environ, 'FZF_QUERY': query}).strip()
            for query in ['f', 'fea', 'window name', 'https://github.com/owner/repo/pull/']:
                self.assertEqual(changed_query(query), '')
            self.assertTrue(changed_query('feature').startswith('disable-search+reload('))
            self.assertTrue(changed_query('features').startswith('enable-search+reload(cat '))
            self.assertTrue(changed_query('features again').startswith('enable-search+reload(cat '))
            subprocess.check_output(['/bin/sh', '-c', search.picker.query_change_command('echo query', preview_path.with_name('candidates.txt'), exact_queries=['feature'], on_load=True)],
                                    env={**os.environ, 'FZF_QUERY': 'features again'})
            self.assertEqual(changed_query('features again'), '')
            self.assertTrue(changed_query('https://github.com/owner/repo/pull/7').startswith('disable-search+reload('))
            self.assertTrue(changed_query('').startswith('enable-search+reload(cat '))
            subprocess.check_output(['/bin/sh', '-c', search.picker.query_change_command('echo query', preview_path.with_name('candidates.txt'), exact_queries=['feature'], on_load=True)],
                                    env={**os.environ, 'FZF_QUERY': ''})
            self.assertEqual(changed_query(''), '')

    def test_live_search_accepts_snapshot_panes_without_external_query_results(self):
        with tempfile.TemporaryDirectory() as directory:
            preview_path = Path(directory, 'panes.json')
            preview_path.write_text(json.dumps({'%1': {'associations': []}}))
            with redirect_stdout(io.StringIO()) as output:
                search.print_accept_action(preview_path, 'feature', '%1')
            self.assertEqual(output.getvalue().strip(), 'accept')
            with redirect_stdout(io.StringIO()) as output:
                search.print_accept_action(preview_path, 'feature', '!')
            self.assertNotEqual(output.getvalue().strip(), 'accept')

    def test_enter_rejects_stale_rows_while_query_results_are_updating(self):
        with tempfile.TemporaryDirectory() as directory:
            preview_path = Path(directory, 'panes.json')
            preview_path.write_text(json.dumps({'%1': {'associations': []}, '%2': {'associations': []}}))
            with redirect_stdout(io.StringIO()) as output:
                search.print_accept_action(preview_path, 'https://github.com/owner/repo/pull/7', '%1')
            self.assertNotEqual(output.getvalue().strip(), 'accept')
            search.query_result_path(preview_path, 'https://github.com/owner/repo/pull/7').write_text('["%2"]')
            with redirect_stdout(io.StringIO()) as output:
                search.print_accept_action(preview_path, 'https://github.com/owner/repo/pull/7', '%1')
            self.assertNotEqual(output.getvalue().strip(), 'accept')
            with redirect_stdout(io.StringIO()) as output:
                search.print_accept_action(preview_path, 'https://github.com/owner/repo/pull/7', '%2')
            self.assertEqual(output.getvalue().strip(), 'accept')

    def test_popup_closes_and_redraws_before_navigation(self):
        calls = []
        def fake_run(command, **kwargs):
            calls.append(command[1])
            if command[1] == 'display-popup':
                import shlex
                popup_command = shlex.split(command[-1])
                Path(popup_command[popup_command.index('--data') + 1]).write_text('%42')
            return ''
        with patch.object(search, 'run', side_effect=fake_run), \
             patch.object(search, 'navigate_to_pane', side_effect=lambda *arguments: calls.append('navigate')):
            search.open_picker('/dev/origin')
        self.assertEqual(calls, ['display-popup', 'refresh-client', 'navigate'])

    def test_popup_picker_only_writes_selection_without_switching(self):
        with tempfile.TemporaryDirectory() as directory:
            selection_path = Path(directory, 'selection.txt')
            with patch.object(search, 'collect_and_record_pane_rows', return_value=[]), \
                 patch.object(search, 'choose_row', return_value='%42\tSelected pane'), \
                 patch.object(search, 'navigate_to_pane') as navigate:
                search.pick_pane('/dev/origin', selection_path)
            self.assertEqual(selection_path.read_text(), '%42')
            navigate.assert_not_called()

    def test_explicit_pr_and_branch_claims_exclude_shared_checkout_observations(self):
        pane_rows = {
            '%1': {'pane': '%1', 'associations': [{'repository': 'github.com/owner/repo',
                'branch': 'feature', 'source': 'observed', 'checkout': '/shared'}]},
            '%2': {'pane': '%2', 'associations': [{'repository': 'github.com/owner/repo',
                'branch': 'feature', 'source': 'claim', 'checkout': '/worktrees/feature'}]},
        }
        with tempfile.TemporaryDirectory() as directory:
            preview_path = Path(directory, 'panes.json')
            preview_path.write_text(json.dumps(pane_rows))
            Path(directory, 'candidates.txt').write_text('%1\tObserved feature\n%2\tClaimed feature')
            for query in ['feature', 'https://github.com/owner/repo/pull/7']:
                with patch.object(search.github, 'resolve_pr', return_value=('github.com/owner/repo', 'feature')), \
                     redirect_stdout(io.StringIO()) as output:
                    search.update_query_results(preview_path, query)
                self.assertIn('%2\t', output.getvalue())
                self.assertIn('Claimed feature', output.getvalue())
                self.assertNotIn('%1\t', output.getvalue())

    def test_claimed_pane_does_not_inherit_another_agents_shared_checkout_branch(self):
        explicit_claim = {'repository': 'github.com/owner/repo', 'branch': 'my-work',
                          'source': 'claim', 'checkout': '/worktrees/my-work'}
        pane_row = {'associations': [explicit_claim,
            {'repository': 'github.com/owner/repo', 'branch': 'someone-elses-work', 'source': 'observed'}]}
        self.assertEqual(search.navigation_associations(pane_row), [explicit_claim])

    def test_claim_rejects_a_branch_not_checked_out_in_the_target_worktree(self):
        def fake_run(command, **kwargs):
            if command[0] == 'git':
                if 'remote' in command:
                    return 'https://github.com/owner/repo.git'
                if 'branch' in command:
                    return 'main'
                return '/shared'
            return ''
        with patch.object(search, 'run', side_effect=fake_run):
            with self.assertRaisesRegex(ValueError, 'checkout is on main, not feature'):
                search.record_branch('%42', '/shared', 'feature', source='claim')

    def test_pr_claim_validates_repository_and_allows_base_checkout_for_fork_pr(self):
        def run_in_repository(repository):
            def fake_run(command, **kwargs):
                if command[0] == 'git':
                    if 'remote' in command:
                        return f'https://{repository}.git'
                    if 'branch' in command:
                        return 'feature'
                    return '/worktrees/feature'
                return ''
            return fake_run
        with patch.object(search.github, 'resolve_pr', return_value=('github.com/fork/repo', 'feature')):
            with patch.object(search, 'run', side_effect=run_in_repository('github.com/unrelated/repo')):
                with self.assertRaisesRegex(ValueError, 'different repository'):
                    search.record_branch('%42', '/worktrees/feature', 'https://github.com/base/repo/pull/7', source='claim')
            with patch.object(search, 'run', side_effect=run_in_repository('github.com/base/repo')) as commands:
                search.record_branch('%42', '/worktrees/feature', 'https://github.com/base/repo/pull/7', source='claim')
                self.assertEqual(json.loads(commands.call_args.args[0][-1])['repository'], 'github.com/fork/repo')

    def test_start_creates_isolated_worktree_without_changing_shared_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            repository_path = Path(directory, 'repo')
            repository_path.mkdir()
            search.run(['git', 'init', '-b', 'main', str(repository_path)], check=True)
            search.run(['git', '-C', str(repository_path), '-c', 'user.name=Test', '-c', 'user.email=test@example.com',
                        '-c', 'core.hooksPath=/dev/null', 'commit', '--allow-empty', '-m', 'Initial'], check=True)
            checkout_path = Path(directory, 'feature-worktree')
            original_run = search.run
            def run_in_repository(command, **kwargs):
                if command[0] == 'tmux':
                    return '%42'
                return original_run(['git', '-C', str(repository_path), *command[1:]], **kwargs)
            with patch.object(search, 'run', side_effect=run_in_repository):
                created_path = search.create_agent_worktree('%42', 'eq/feat/example', str(checkout_path), 'HEAD')
            self.assertEqual(created_path, checkout_path.resolve())
            self.assertEqual(search.run(['git', '-C', str(repository_path), 'branch', '--show-current']), 'main')
            self.assertEqual(search.run(['git', '-C', str(checkout_path), 'branch', '--show-current']), 'eq/feat/example')
            with patch.object(search, 'run', side_effect=run_in_repository):
                reused_path = search.create_agent_worktree('%42', 'eq/feat/example', str(Path(directory, 'unused')), 'HEAD')
            self.assertEqual(reused_path, created_path)
            self.assertFalse(Path(directory, 'unused').exists())

    def test_cancel_does_not_switch(self):
        with patch.object(search, 'collect_and_record_pane_rows', return_value=[]), \
             patch.object(search, 'choose_row', return_value=''), \
             patch.object(search, 'run') as commands:
            search.pick_pane('client')
            commands.assert_not_called()


if __name__ == '__main__':
    unittest.main()
