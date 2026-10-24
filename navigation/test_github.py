import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from navigation import github


class GitHubTests(unittest.TestCase):
    def setUp(self):
        cache_directory = tempfile.TemporaryDirectory()
        self.addCleanup(cache_directory.cleanup)
        cache_environment = patch.dict(os.environ, {'XDG_CACHE_HOME': cache_directory.name})
        cache_environment.start()
        self.addCleanup(cache_environment.stop)

    def test_remote_identity_matches_ssh_and_https(self):
        for remote in ['git@github.com:Owner/Repo.git', 'https://github.com/Owner/Repo.git',
                       'ssh://git@github.com/Owner/Repo.git']:
            self.assertEqual(github.repository_identity(remote), 'github.com/owner/repo')

    def test_pr_resolves_head_repository_including_forks(self):
        with patch.object(github, 'run', return_value=json.dumps({
            'head': {'repo': {'full_name': 'Fork/Repo'}, 'ref': 'feature'}})) as request:
            self.assertEqual(github.resolve_pr('https://github.com/base/repo/pull/123/files'),
                             ('github.com/fork/repo', 'feature'))
        self.assertEqual(request.call_args.args[0], ['gh', 'api', 'repos/base/repo/pulls/123'])

    def test_successful_pr_resolution_is_cached_across_url_variants(self):
        with patch.object(github, 'resolve_pr', return_value=('github.com/owner/repo', 'feature')) as lookup:
            self.assertEqual(github.resolve_and_cache_pr('https://github.com/Owner/Repo/pull/7'),
                             ('github.com/owner/repo', 'feature'))
            self.assertEqual(github.resolve_and_cache_pr('https://github.com/owner/repo/pull/7/files'),
                             ('github.com/owner/repo', 'feature'))
        self.assertEqual(lookup.call_count, 1)

    def test_pr_cache_expires_and_recovers_from_corruption(self):
        with patch.object(github, 'resolve_pr', return_value=('github.com/owner/repo', 'feature')) as lookup:
            with patch.object(github.time, 'time', return_value=1000):
                github.resolve_and_cache_pr('https://github.com/owner/repo/pull/7')
            with patch.object(github.time, 'time', return_value=1301):
                github.resolve_and_cache_pr('https://github.com/owner/repo/pull/7')
            cache_path = next(Path(os.environ['XDG_CACHE_HOME']).rglob('*.json'))
            cache_path.write_text('broken JSON')
            github.resolve_and_cache_pr('https://github.com/owner/repo/pull/7')
        self.assertEqual(lookup.call_count, 3)

    def test_failed_pr_lookups_remain_retryable(self):
        with patch.object(github, 'resolve_pr', side_effect=ValueError('not found')) as lookup:
            for attempt in range(2):
                with self.assertRaisesRegex(ValueError, 'not found'):
                    github.resolve_and_cache_pr('https://github.com/owner/repo/pull/7')
        self.assertEqual(lookup.call_count, 2)
        self.assertEqual(list(Path(os.environ['XDG_CACHE_HOME']).rglob('*.json')), [])


if __name__ == '__main__':
    unittest.main()
