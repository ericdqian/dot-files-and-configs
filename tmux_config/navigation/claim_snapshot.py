"""Carry navigation claims across tmux server restarts.

tmux keeps user options only in server memory, and tmux-resurrect restores the
layout without them. A snapshot records each session's, window's, and pane's
navigation options next to the layout facts resurrect restores exactly: session
name, window index, and pane directories. Restoring reapplies a window's options
only when all of those still match, so a restored claim never lands on a window
that merely resembles the original.
"""
import json

PANE_LAYOUT_FORMAT = ('#{session_id}\t#{session_name}\t#{window_id}\t#{window_index}\t'
                      '#{pane_id}\t#{pane_index}\t#{pane_current_path}')
VISIT_OPTIONS = {'@agent_window_access', '@agent_pane_access'}
WINDOW_OWNERSHIP_OPTIONS = {'@agent_nav_owner', '@agent_nav_branch', '@agent_nav_checkout'}
TARGET_MARKER = 'agent-snapshot-target '
VALUE_MARKER = 'agent-snapshot-value '
SCOPE_FLAGS = {'$': '', '@': '-w', '%': '-p'}
# display-message expands strftime, so a literal %ID would be mangled; print IDs by format.
TARGET_ID_FORMATS = {'$': '#{session_id}', '@': '#{window_id}', '%': '#{pane_id}'}
# tmux rejects oversized command lists, so callers send at most this many targets per request.
COMMAND_BATCH_SIZE = 40


def parse_pane_layout(pane_listing):
    pane_layout = []
    for pane_line in pane_listing.splitlines():
        session_id, session_name, window_id, window_index, pane_id, pane_index, pane_path = pane_line.split('\t')
        pane_layout.append({'session_id': session_id, 'session_name': session_name,
                            'window_id': window_id, 'window_index': window_index,
                            'pane_id': pane_id, 'pane_index': pane_index, 'pane_path': pane_path})
    return pane_layout


def navigation_target_ids(pane_layout):
    return list(dict.fromkeys(target_id for pane in pane_layout
                              for target_id in [pane['session_id'], pane['window_id'], pane['pane_id']]))


def option_names_command(target_ids):
    # Each listing follows a marker naming its target.
    names_command = ['tmux']
    for target_id in target_ids:
        if len(names_command) > 1:
            names_command.append(';')
        names_command.extend(['display-message', '-p', '-t', target_id, TARGET_MARKER + TARGET_ID_FORMATS[target_id[0]], ';',
                              'show-options', *scope_arguments(target_id), '-t', target_id])
    return names_command


def parse_option_names(names_listing):
    # Listings quote values with escapes shlex cannot reverse, so only names are read here.
    option_names_by_target = {}
    current_target = ''
    for option_line in names_listing.splitlines():
        if option_line.startswith(TARGET_MARKER):
            current_target = option_line.removeprefix(TARGET_MARKER)
            option_names_by_target[current_target] = []
            continue
        option_name = option_line.split(' ', 1)[0]
        if current_target and is_navigation_option(option_name):
            option_names_by_target[current_target].append(option_name)
    return option_names_by_target


def is_navigation_option(option_name):
    return option_name.startswith('@agent_nav_') or option_name in VISIT_OPTIONS


def option_values_command(target_option_names):
    values_command = ['tmux']
    for target_id, option_name in target_option_names:
        if len(values_command) > 1:
            values_command.append(';')
        # show-options -v prints the raw value; navigation values are single-line.
        values_command.extend(['display-message', '-p', '-t', target_id, f'{VALUE_MARKER}{TARGET_ID_FORMATS[target_id[0]]} {option_name}', ';',
                               'show-options', *scope_arguments(target_id), '-v', '-t', target_id, option_name])
    return values_command


def parse_option_values(values_listing):
    options_by_target = {}
    value_lines = values_listing.split('\n')
    for line_number, value_line in enumerate(value_lines):
        if value_line.startswith(VALUE_MARKER) and line_number + 1 < len(value_lines):
            target_id, option_name = value_line.removeprefix(VALUE_MARKER).split(' ', 1)
            options_by_target.setdefault(target_id, {})[option_name] = value_lines[line_number + 1]
    return options_by_target


def scope_arguments(target_id):
    scope_flag = SCOPE_FLAGS[target_id[0]]
    return [scope_flag] if scope_flag else []


def build_snapshot(pane_layout, options_by_target):
    session_options = {}
    windows_by_id = {}
    for pane in pane_layout:
        saved_session_options = options_by_target.get(pane['session_id'], {})
        if saved_session_options:
            session_options[pane['session_name']] = saved_session_options
        saved_window = windows_by_id.setdefault(pane['window_id'], {
            'session': pane['session_name'], 'index': pane['window_index'],
            'pane_paths': [], 'options': options_by_target.get(pane['window_id'], {}), 'pane_options': {}})
        saved_window['pane_paths'].append(pane['pane_path'])
        saved_pane_options = options_by_target.get(pane['pane_id'], {})
        if saved_pane_options:
            saved_window['pane_options'][pane['pane_index']] = saved_pane_options
    saved_windows = [saved_window for saved_window in windows_by_id.values()
                     if saved_window['options'] or saved_window['pane_options']]
    return {'version': 1, 'sessions': session_options, 'windows': saved_windows}


def plan_restore(snapshot, live_pane_layout, live_options_by_target):
    """Return (target, option, value) assignments that reapply saved options without overwriting live ones."""
    live_session_ids = {}
    live_windows = {}
    for pane in live_pane_layout:
        live_session_ids[pane['session_name']] = pane['session_id']
        live_window = live_windows.setdefault((pane['session_name'], pane['window_index']),
                                              {'id': pane['window_id'], 'pane_paths': [], 'pane_ids': {}})
        live_window['pane_paths'].append(pane['pane_path'])
        live_window['pane_ids'][pane['pane_index']] = pane['pane_id']
    owned_branches = {owned_branch(options) for options in live_options_by_target.values()} - {None}
    option_assignments = []
    for session_name, saved_session_options in snapshot.get('sessions', {}).items():
        if session_name in live_session_ids:
            option_assignments += missing_assignments(live_session_ids[session_name], saved_session_options,
                                                      live_options_by_target)
    for saved_window in snapshot.get('windows', []):
        live_window = live_windows.get((saved_window['session'], saved_window['index']))
        if not live_window or live_window['pane_paths'] != saved_window['pane_paths']:
            continue  # A different layout means this is not the saved window.
        saved_branch = owned_branch(saved_window['options'])
        live_window_options = live_options_by_target.get(live_window['id'], {})
        if saved_branch and saved_branch in owned_branches and owned_branch(live_window_options) != saved_branch:
            continue  # Another window already owns this branch; one window per branch.
        if saved_branch:
            owned_branches.add(saved_branch)
        option_assignments += missing_assignments(live_window['id'], saved_window['options'],
                                                  live_options_by_target)
        for pane_index, saved_pane_options in saved_window['pane_options'].items():
            if pane_index in live_window['pane_ids']:
                option_assignments += missing_assignments(live_window['pane_ids'][pane_index], saved_pane_options,
                                                          live_options_by_target)
    return option_assignments


def owned_branch(options):
    owner_json = options.get('@agent_nav_owner')
    if not owner_json:
        return None
    owner = json.loads(owner_json)
    return owner['repository'], owner['branch']


def missing_assignments(target_id, saved_options, live_options_by_target):
    live_options = live_options_by_target.get(target_id, {})
    # A live owner is newer than any snapshot, so its whole ownership record stays intact.
    live_owner = '@agent_nav_owner' in live_options
    return [(target_id, option_name, option_value)
            for option_name, option_value in saved_options.items()
            if option_name not in live_options
            and not (live_owner and option_name in WINDOW_OWNERSHIP_OPTIONS)]


def set_options_command(option_assignments):
    set_command = ['tmux']
    for target_id, option_name, option_value in option_assignments:
        if len(set_command) > 1:
            set_command.append(';')
        set_command.extend(['set-option', *scope_arguments(target_id), '-t', target_id, option_name, option_value])
    return set_command
