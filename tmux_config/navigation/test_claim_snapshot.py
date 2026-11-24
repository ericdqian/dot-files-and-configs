import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('search', Path(__file__).with_name('search.py'))
search = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(search)
claim_snapshot = search.claim_snapshot

OWNER = {'repository': 'github.com/owner/repo', 'branch': 'feature', 'checkout': '/worktrees/feature',
         'source': 'claim', 'url': 'https://github.com/owner/repo/pull/7', 'description': 'Feature "$work" #1'}


def pane(session_name, window_index, pane_index, pane_path, session_id='$1', window_id=None, pane_id=None):
    return {'session_id': session_id, 'session_name': session_name,
            'window_id': window_id or f'@{window_index}', 'window_index': str(window_index),
            'pane_id': pane_id or f'%{window_index}{pane_index}', 'pane_index': str(pane_index), 'pane_path': pane_path}


class ClaimSnapshotPlanTests(unittest.TestCase):
    def test_snapshot_keeps_only_windows_and_panes_with_navigation_options(self):
        pane_layout = [pane('core', 3, 0, '/worktrees/feature'), pane('core', 3, 1, '/tmp'),
                       pane('core', 5, 0, '/home')]
        options_by_target = {'$1': {'@agent_nav_repository': 'github.com/owner/repo'},
                             '@3': {'@agent_nav_owner': json.dumps(OWNER)},
                             '%31': {'@agent_pane_access': '42'}, '@5': {}}
        snapshot = claim_snapshot.build_snapshot(pane_layout, options_by_target)
        self.assertEqual(snapshot['sessions'], {'core': {'@agent_nav_repository': 'github.com/owner/repo'}})
        self.assertEqual(snapshot['windows'], [{
            'session': 'core', 'index': '3', 'pane_paths': ['/worktrees/feature', '/tmp'],
            'options': {'@agent_nav_owner': json.dumps(OWNER)}, 'pane_options': {'1': {'@agent_pane_access': '42'}}}])

    def test_restore_targets_only_the_window_with_the_same_index_and_pane_paths(self):
        snapshot = {'sessions': {}, 'windows': [
            {'session': 'core', 'index': '3', 'pane_paths': ['/worktrees/feature'],
             'options': {'@agent_nav_branch': 'feature'}, 'pane_options': {}},
            {'session': 'core', 'index': '4', 'pane_paths': ['/worktrees/other'],
             'options': {'@agent_nav_branch': 'other'}, 'pane_options': {}},
            {'session': 'gone', 'index': '0', 'pane_paths': ['/x'],
             'options': {'@agent_nav_branch': 'lost'}, 'pane_options': {}}]}
        live_layout = [pane('core', 3, 0, '/worktrees/feature', window_id='@30'),
                       pane('core', 4, 0, '/somewhere-else', window_id='@40')]
        option_assignments = claim_snapshot.plan_restore(snapshot, live_layout, {})
        self.assertEqual(option_assignments, [('@30', '@agent_nav_branch', 'feature')])
        self.assertEqual(claim_snapshot.set_options_command(option_assignments),
                         ['tmux', 'set-option', '-w', '-t', '@30', '@agent_nav_branch', 'feature'])

    def test_restore_never_overwrites_live_ownership_or_duplicates_an_owned_branch(self):
        saved_window = {'session': 'core', 'index': '3', 'pane_paths': ['/worktrees/feature'],
                        'options': {'@agent_nav_owner': json.dumps(OWNER), '@agent_nav_branch': 'feature',
                                    '@agent_window_access': '10'}, 'pane_options': {}}
        live_layout = [pane('core', 3, 0, '/worktrees/feature', window_id='@30'),
                       pane('core', 9, 0, '/worktrees/feature', window_id='@90')]
        newer_owner = json.dumps({**OWNER, 'url': 'https://github.com/owner/repo/pull/8'})
        self.assertEqual(claim_snapshot.plan_restore({'windows': [saved_window]}, live_layout,
                                                     {'@30': {'@agent_nav_owner': newer_owner}}),
                         [('@30', '@agent_window_access', '10')])
        self.assertEqual(claim_snapshot.plan_restore({'windows': [saved_window]}, live_layout,
                                                     {'@90': {'@agent_nav_owner': json.dumps(OWNER)}}), [])

    def test_option_names_ignore_unrelated_options_and_values_keep_raw_text(self):
        names_listing = '\n'.join([
            claim_snapshot.TARGET_MARKER + '@3', 'automatic-rename off', '@agent_state done',
            '@agent_nav_branch eq/feat/x', claim_snapshot.TARGET_MARKER + '%7', '@agent_pane_access 99'])
        option_names_by_target = claim_snapshot.parse_option_names(names_listing)
        self.assertEqual(option_names_by_target, {'@3': ['@agent_nav_branch'], '%7': ['@agent_pane_access']})
        self.assertEqual(claim_snapshot.option_values_command([('%7', '@agent_pane_access')])[-5:],
                         ['-p', '-v', '-t', '%7', '@agent_pane_access'])
        values_listing = '\n'.join([claim_snapshot.VALUE_MARKER + '@3 @agent_nav_branch', 'say "$x" \\ #1',
                                     claim_snapshot.VALUE_MARKER + '%7 @agent_pane_access', '99'])
        self.assertEqual(claim_snapshot.parse_option_values(values_listing),
                         {'@3': {'@agent_nav_branch': 'say "$x" \\ #1'}, '%7': {'@agent_pane_access': '99'}})


@unittest.skipUnless(shutil.which('tmux'), 'tmux is required')
class ClaimSnapshotTmuxTests(unittest.TestCase):
    """Save from a real tmux server, rebuild the layout as resurrect would, then restore."""

    def setUp(self):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.directory = Path(temporary_directory.name)
        # An isolated socket directory keeps the test away from the user's server.
        environment = patch.dict(os.environ, {'TMUX_TMPDIR': str(self.directory)})
        environment.start()
        self.addCleanup(environment.stop)
        os.environ.pop('TMUX', None)
        os.environ.pop('TMUX_PANE', None)
        self.addCleanup(lambda: subprocess.run(['tmux', 'kill-server'], capture_output=True))
        for checkout_name in ['feature', 'shell', 'moved']:
            (self.directory / checkout_name).mkdir()

    def tmux(self, *arguments):
        return subprocess.check_output(['tmux', '-f', '/dev/null', *arguments], text=True).strip()

    def build_layout(self, moved_window_directory):
        feature_directory = str((self.directory / 'feature').resolve())
        self.tmux('new-session', '-d', '-s', 'core', '-c', feature_directory)
        self.tmux('new-window', '-d', '-t', 'core:5', '-c', str((self.directory / 'shell').resolve()))
        self.tmux('split-window', '-d', '-t', 'core:5', '-c', feature_directory)
        self.tmux('new-window', '-d', '-t', 'core:8', '-c', str((self.directory / moved_window_directory).resolve()))

    def test_claims_survive_a_server_restart_only_on_matching_windows(self):
        self.build_layout('feature')
        owner_json = json.dumps(OWNER)
        link_json = json.dumps({'repository': 'github.com/owner/repo', 'branch': 'old', 'source': 'link'})
        self.tmux('set-option', '-t', 'core', '@agent_nav_repository', 'github.com/owner/repo')
        self.tmux('set-option', '-w', '-t', 'core:5', '@agent_nav_owner', owner_json)
        self.tmux('set-option', '-w', '-t', 'core:5', '@agent_nav_branch', 'feature')
        self.tmux('set-option', '-w', '-t', 'core:5', '@agent_state', 'done')
        self.tmux('set-option', '-p', '-t', 'core:5.1', '@agent_nav_abc', link_json)
        self.tmux('set-option', '-w', '-t', 'core:8', '@agent_nav_branch', 'elsewhere')
        snapshot_path = self.directory / 'state' / 'claims.json'
        search.save_claim_snapshot(snapshot_path)

        self.tmux('kill-server')
        self.build_layout('moved')  # Window 8 comes back in a different directory.
        search.restore_claim_snapshot(snapshot_path)

        self.assertEqual(self.tmux('show-options', '-v', '-t', 'core', '@agent_nav_repository'), 'github.com/owner/repo')
        self.assertEqual(json.loads(self.tmux('show-options', '-wv', '-t', 'core:5', '@agent_nav_owner')), OWNER)
        self.assertEqual(self.tmux('display-message', '-p', '-t', 'core:5', '#{@agent_nav_branch}'), 'feature')
        self.assertEqual(self.tmux('display-message', '-p', '-t', 'core:5', '#{@agent_state}'), '')
        self.assertEqual(json.loads(self.tmux('show-options', '-pv', '-t', 'core:5.1', '@agent_nav_abc')),
                         json.loads(link_json))
        self.assertEqual(self.tmux('display-message', '-p', '-t', 'core:8', '#{@agent_nav_branch}'), '')

    def test_large_layouts_are_read_and_restored_in_batches(self):
        self.build_layout('feature')
        shell_directory = str((self.directory / 'shell').resolve())
        for window_index in range(10, 10 + claim_snapshot.COMMAND_BATCH_SIZE * 2):
            self.tmux('new-window', '-d', '-t', f'core:{window_index}', '-c', shell_directory)
            self.tmux('set-option', '-w', '-t', f'core:{window_index}', '@agent_window_access', str(window_index))
        snapshot_path = self.directory / 'claims.json'
        search.save_claim_snapshot(snapshot_path)
        self.tmux('kill-server')
        self.build_layout('feature')
        for window_index in range(10, 10 + claim_snapshot.COMMAND_BATCH_SIZE * 2):
            self.tmux('new-window', '-d', '-t', f'core:{window_index}', '-c', shell_directory)
        search.restore_claim_snapshot(snapshot_path)
        last_window = 9 + claim_snapshot.COMMAND_BATCH_SIZE * 2
        self.assertEqual(self.tmux('display-message', '-p', '-t', f'core:{last_window}', '#{@agent_window_access}'),
                         str(last_window))

    def test_restore_without_a_snapshot_changes_nothing(self):
        self.build_layout('feature')
        search.restore_claim_snapshot(self.directory / 'missing.json')
        self.assertEqual(self.tmux('display-message', '-p', '-t', 'core:5', '#{@agent_nav_branch}'), '')


if __name__ == '__main__':
    unittest.main()
