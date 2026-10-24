"""Shared fzf query switching and selection validation for navigation pickers."""
import hashlib
import json
import re
import shlex

from navigation import github


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


def query_result_path(preview_path, query):
    return preview_path.with_name('query-' + hashlib.sha256(query.encode()).hexdigest() + '.json')


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
