"""Shared fzf query switching and selection validation for navigation pickers."""
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

from navigation import github
from navigation.commands import run


def run_picker(snapshot_path, query, arguments):
    cli_path = Path(__file__).with_name('cli.py')
    query_command = shlex.join([sys.executable, str(cli_path), 'query', '--data', str(snapshot_path), '--']) + ' "$FZF_QUERY"'
    accept_command = shlex.join([sys.executable, str(cli_path), 'accept', '--data', str(snapshot_path)]) + ' --selected {1} -- {q}'
    destination_rows = json.loads(snapshot_path.read_text())
    options = json.loads(snapshot_path.with_name('options.json').read_text())
    exact_queries = sorted({association['branch'] for row in destination_rows.values()
                            for association in row.get('associations', []) if association.get('source') in {'claim', 'link'}})
    change_command = query_change_command(query_command, snapshot_path.with_name('candidates.txt'),
                                          exact_queries, options.get('pr_numbers', False))
    load_command = query_change_command(query_command, snapshot_path.with_name('candidates.txt'),
                                        exact_queries, options.get('pr_numbers', False), on_load=True)
    # The same reload and Enter validation protect both terminal and worktree selections.
    return subprocess.run([*arguments, '--query=' + query,
                           '--bind=enter:transform(' + accept_command + ')',
                           '--bind=start:transform(' + change_command + ')',
                           '--bind=change:transform(' + change_command + ')',
                           '--bind=load:transform(' + load_command + ')'],
                          input=snapshot_path.with_name('candidates.txt').read_text(), text=True,
                          stdout=subprocess.PIPE, env={**os.environ, 'FZF_DEFAULT_OPTS': '', 'FZF_DEFAULT_OPTS_FILE': ''})


def query_change_command(query_command, candidates_path, exact_queries=(), pr_numbers=False, on_load=False):
    reload_action = shlex.quote('disable-search+reload(' + query_command + ')')
    restore_command = shlex.join(['cat', str(candidates_path)])
    restore_action = shlex.quote('enable-search+reload(' + restore_command + ')')
    mode_path = shlex.quote(str(candidates_path.with_name('external-query')))
    status_path = shlex.quote(str(candidates_path.with_name('status.txt')))
    branch_case = ('case "$normalized_query" in ' + '|'.join(shlex.quote(branch) for branch in exact_queries)
                   + ') external_query=yes ;; esac; ') if exact_queries else ''
    number_case = (r'pr_number="${normalized_query#\#}"; '
                   'case "$pr_number" in ""|*[!0-9]*) ;; *) external_query=yes ;; esac; ') if pr_numbers else ''
    if on_load:
        mode_actions = ('if [ -z "$external_query" ] && [ -f ' + mode_path
                        + ' ]; then rm -f ' + mode_path + '; fi')
    else:
        # Keep the marker until fzf loads the restored list; rapid typing can cancel a reload.
        mode_actions = ('if [ "$external_query" = yes ]; then : > ' + mode_path
                        + "; printf '%s\\n' " + reload_action
                        + '; elif [ -f ' + mode_path + ' ]; then '
                        + "printf '%s' 'No matching destinations. Edit your search or paste a GitHub PR URL.' > " + status_path
                        + "; printf '%s\\n' " + restore_action + '; fi')
    # A shell builtin dispatch keeps Python, GitHub, and a second fzf out of ordinary typing.
    # The marker is private to this picker and tracks when its candidate list needs restoring.
    return ('normalized_query="${FZF_QUERY#"${FZF_QUERY%%[![:space:]]*}"}"; '
            'normalized_query="${normalized_query%"${normalized_query##*[![:space:]]}"}"; '
            'external_query=; ' + branch_case
            + 'case "$normalized_query" in https://github.com/*/*/pull/*) '
              'pr_number="${normalized_query##*/pull/}"; pr_number="${pr_number%%[/?#]*}"; '
              'case "$pr_number" in ""|*[!0-9]*) ;; *) external_query=yes ;; esac ;; esac; '
            + number_case + mode_actions)


def write_snapshot(preview_path, destination_rows, candidate_lines, options=None):
    # Reset candidates and query validation together when the repository scope changes.
    preview_path.with_name('options.json').write_text(json.dumps(options or {}))
    preview_path.write_text(json.dumps(destination_rows))
    preview_path.with_name('candidates.txt').write_text('\n'.join(candidate_lines))
    preview_path.with_name('status.txt').write_text('No matching destinations. Edit your search or repository filter.')
    preview_path.with_name('external-query').unlink(missing_ok=True)
    for previous_query_path in preview_path.parent.glob('query-*.json'):
        previous_query_path.unlink()
    query_result_path(preview_path, '').write_text(json.dumps(list(destination_rows)))


def update_query_results(preview_path, query):
    candidate_lines = preview_path.with_name('candidates.txt').read_text().splitlines()
    destination_rows = json.loads(preview_path.read_text())
    options_path = preview_path.with_name('options.json')
    options = json.loads(options_path.read_text()) if options_path.exists() else {}
    normalized_query = query.strip()
    exact_ids = {destination_id for destination_id, row in destination_rows.items()
                 if normalized_query and normalized_query in row.get('exact_queries', [])}
    original_query = query
    try:
        if is_pr_query(query, pr_numbers=options.get('pr_numbers', False)) and not exact_ids:
            query = github.pr_reference_url(normalized_query, options.get('repository_url', ''))
        if github.PR_PATTERN.fullmatch(query.strip()) and not exact_ids:
            canonical_url = github.canonical_pr_url(query)
            matching_associations = [(destination_id, association) for destination_id, row in destination_rows.items()
                                     for association in row.get('associations', [])
                                     if github.canonical_pr_url(association.get('url', '')) == canonical_url]
            status = 'No matching destination for this PR.'
            if matching_associations:
                recorded_branches = {(association['repository'], association['branch'])
                                     for destination_id, association in matching_associations}
                matching_associations = [(destination_id, association) for destination_id, row in destination_rows.items()
                                         for association in row.get('associations', [])
                                         if (association['repository'], association['branch']) in recorded_branches]
            else:
                repository, branch = github.resolve_and_cache_pr(query.strip())
                matching_associations = [(destination_id, association) for destination_id, row in destination_rows.items()
                                         for association in row.get('associations', [])
                                         if association['repository'] in {repository, github.repository_identity(options.get('repository_url', ''))}
                                         and association['branch'] == branch]
                status = options.get('missing_destination', 'No matching destination for branch {branch}.').format(branch=branch)
            matching_ids = {destination_id for destination_id, association in matching_associations}
            claimed_ids = {destination_id for destination_id, association in matching_associations
                             if association.get('source') in {'claim', 'link'}}
            if claimed_ids:
                matching_ids = claimed_ids
            pr_number = github.PR_PATTERN.fullmatch(query.strip()).group(3)
            result_lines = [line.replace('\t', f'\t\033[35mPR #{pr_number}\033[0m  ', 1) for line in candidate_lines
                            if line.split('\t', 1)[0] in matching_ids]
        else:
            claimed_ids = exact_ids or {destination_id for destination_id, row in destination_rows.items() if any(
                association.get('source') in {'claim', 'link'} and association['branch'] == query.strip()
                for association in row.get('associations', []))}
            if claimed_ids:
                candidate_lines = [line for line in candidate_lines if line.split('\t', 1)[0] in claimed_ids]
            # Reuse fzf’s ranking while keeping original ANSI rows for presentation.
            filtered_lines = run(['fzf', *options.get('filter_arguments', ['--ansi', '--delimiter=\t', '--with-nth=2..', '--tiebreak=index']), '--filter', query],
                                 input_text='\n'.join(candidate_lines)).splitlines()
            candidate_lines_by_destination_id = {line.split('\t', 1)[0]: line for line in candidate_lines}
            result_lines = [candidate_lines_by_destination_id[line.split('\t', 1)[0]] for line in filtered_lines]
            status = 'No matching destination. Edit your search or paste a GitHub PR URL.'
    except (ValueError, OSError, KeyError, subprocess.TimeoutExpired) as error:
        result_lines = []
        status = f'PR lookup failed: {error}. Edit the URL to retry, or search a branch name.'
    # The non-selectable status row and preview explain empty results inside the picker.
    preview_path.with_name('status.txt').write_text(status)
    result_path = query_result_path(preview_path, original_query)
    temporary_result_path = result_path.with_suffix(f'.{os.getpid()}.tmp')
    temporary_result_path.write_text(json.dumps([line.split('\t', 1)[0] for line in result_lines]))
    os.replace(temporary_result_path, result_path)
    print('\n'.join(result_lines) if result_lines else '!\t' + status.replace('\n', ' '))


def print_accept_action(preview_path, query, selected_id):
    destination_rows = json.loads(preview_path.read_text())
    options_path = preview_path.with_name('options.json')
    options = json.loads(options_path.read_text()) if options_path.exists() else {}
    exact_query = any(association.get('source') in {'claim', 'link'} and association['branch'] == query.strip()
                      for row in destination_rows.values() for association in row.get('associations', []))
    live_search = not is_pr_query(query, pr_numbers=options.get('pr_numbers', False)) and not exact_query
    print(accept_action(preview_path, query, selected_id, destination_rows, live_search))


def is_pr_query(query, pr_numbers=False):
    normalized_query = query.strip()
    return bool(github.PR_PATTERN.fullmatch(normalized_query) or
                (pr_numbers and re.fullmatch(r'#?[0-9]+', normalized_query)))


def accept_action(snapshot_path, query, selected_id, candidate_ids, live_search):
    result_path = query_result_path(snapshot_path, query)
    if ((live_search and selected_id in candidate_ids) or
            (result_path.exists() and selected_id in json.loads(result_path.read_text()))):
        return 'accept'
    return 'change-header(Search updating or no destination. Wait for results, then press Enter.)'


def query_result_path(preview_path, query):
    return preview_path.with_name('query-' + hashlib.sha256(query.encode()).hexdigest() + '.json')
