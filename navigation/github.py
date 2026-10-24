"""Resolve GitHub PRs and normalize repository identities for navigation."""
import hashlib
import json
import os
import re
import time
from pathlib import Path

from navigation.commands import run

PR_PATTERN = re.compile(r'https://github\.com/([^/]+)/([^/]+)/pull/(\d+)(?:[/?#].*)?$')


def repository_identity(remote_url):
    normalized = re.sub(r'^\w+://(?:[^/@]+@)?', '', remote_url.strip())
    normalized = re.sub(r'^git@', '', normalized).replace(':', '/', 1)
    return normalized.removesuffix('.git').rstrip('/').lower()


def resolve_pr(pr_url):
    match = PR_PATTERN.fullmatch(pr_url)
    if not match:
        raise ValueError('Expected a GitHub PR URL.')
    owner, repository_name, number = match.groups()
    pull_request = json.loads(run(['gh', 'api', f'repos/{owner}/{repository_name}/pulls/{number}'], check=True))
    head_repository = pull_request['head']['repo']
    if not head_repository:
        raise ValueError('The PR’s source repository has been deleted; link its branch explicitly.')
    return 'github.com/' + head_repository['full_name'].lower(), pull_request['head']['ref']


def canonical_pr_url(pr_url):
    match = PR_PATTERN.fullmatch(pr_url.strip())
    if not match:
        return ''
    owner, repository_name, number = match.groups()
    return f'https://github.com/{owner.lower()}/{repository_name.lower()}/pull/{int(number)}'


def resolve_and_cache_pr(pr_url):
    canonical_url = canonical_pr_url(pr_url)
    cache_directory = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'agent-notify' / 'prs'
    cache_path = cache_directory / (hashlib.sha256(canonical_url.encode()).hexdigest() + '.json')
    try:
        cached_resolution = json.loads(cache_path.read_text())
        if (0 <= time.time() - cached_resolution['resolved_at'] < 300
                and all(isinstance(cached_resolution[key], str) and cached_resolution[key]
                        for key in ['repository', 'branch'])):
            return cached_resolution['repository'], cached_resolution['branch']
    except (OSError, ValueError, KeyError, TypeError):
        pass  # Missing, expired, or malformed cache entries fall back to GitHub.
    repository, branch = resolve_pr(pr_url)
    # Cache only successful search lookups; ownership claims still validate against GitHub.
    temporary_cache_path = cache_path.with_suffix(f'.{os.getpid()}.tmp')
    try:
        cache_directory.mkdir(parents=True, exist_ok=True)
        temporary_cache_path.write_text(json.dumps({'repository': repository, 'branch': branch,
                                                   'resolved_at': time.time()}))
        os.replace(temporary_cache_path, cache_path)
    except OSError:
        pass  # A read-only cache must not prevent PR search.
    finally:
        try:
            temporary_cache_path.unlink(missing_ok=True)
        except OSError:
            pass
    return repository, branch


def pr_reference_url(reference, repository_url):
    if re.fullmatch(r'#?[0-9]+', reference):
        return f'{repository_url}/pull/{reference.lstrip("#")}'
    pr_url = canonical_pr_url(reference)
    if not pr_url:
        raise ValueError('Expected a GitHub PR number or URL.')
    if repository_url and repository_identity(pr_url.split('/pull/', 1)[0]) != repository_identity(repository_url):
        raise ValueError(f'PR URL does not belong to {repository_url}')
    return pr_url
