"""Exercise the real popup and fzf in an isolated tmux server (no GitHub calls)."""
import fcntl
import json
import os
import pty
import re
import shlex
import select
import struct
import subprocess
import tempfile
import termios
import time
from pathlib import Path

search_script = str(Path(__file__).with_name('search.py').resolve())
repository_root = Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix='agent-search-') as directory:
    socket = directory + '/tmux.sock'
    # Prevent isolated tests from controlling the real WezTerm GUI.
    gh_directory = directory + '/bin'
    os.mkdir(gh_directory)
    wezterm_stub = Path(gh_directory, 'wezterm')
    wezterm_stub.write_text('#!/bin/sh\nexit 1\n')
    wezterm_stub.chmod(0o755)
    chrome_arguments_path = Path(directory, 'chrome-arguments.txt')
    open_stub = Path(gh_directory, 'open')
    open_stub.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > ' + shlex.quote(str(chrome_arguments_path)) + '\n')
    open_stub.chmod(0o755)
    test_environment = {**os.environ, 'PATH': gh_directory + ':' + os.environ['PATH'],
                        'XDG_CACHE_HOME': directory + '/cache'}
    repository = directory + '/repository'
    os.mkdir(repository)
    def command(*arguments, **kwargs):
        return subprocess.check_output(arguments, text=True, env=test_environment, **kwargs).strip()
    def tmux(*arguments):
        return command('tmux', '-f', '/dev/null', '-S', socket, *arguments)
    command('git', 'init', '-b', 'first', repository)
    command('git', '-C', repository, 'remote', 'add', 'origin', 'git@github.com:owner/repo.git')
    tmux('new-session', '-d', '-s', 'first-session', '-c', repository, '-x', '100', '-y', '40')
    pane_one = tmux('display-message', '-p', '#{pane_id}')
    environment = {**test_environment, 'TMUX': f'{socket},0,0', 'TMUX_PANE': pane_one}
    def record():
        subprocess.run(['python3', search_script, 'record'], input=json.dumps({'cwd': repository}),
                       text=True, env=environment, check=True)
    try:
        record()
        command('git', '-C', repository, 'symbolic-ref', 'HEAD', 'refs/heads/second')
        record()
        record()
        options = tmux('show-options', '-p', '-t', pane_one)
        assert options.count('@agent_nav_') == 3, options  # Two branches plus inspected-directory marker.
        tmux('split-window', '-d', '-t', pane_one, '-c', repository)
        window_rows = json.loads(subprocess.check_output([
            'python3', '-c',
            'import sys,json; sys.path.insert(0,sys.argv[1]); import search; '
            'print(json.dumps(search.group_window_rows(search.collect_and_record_pane_rows())))',
            str(Path(search_script).parent)], text=True, env=environment))
        assert len(window_rows) == 1, window_rows
        assert window_rows[0]['pane'] == pane_one, window_rows
        assert '.' not in window_rows[0]['location'], window_rows
        tmux('new-session', '-d', '-s', 'other-session')
        tmux('new-session', '-d', '-s', 'claude-pr-123-security', '-c', repository)
        binding = next(line for line in (repository_root / 'tmux_config/.tmux.conf').read_text().splitlines() if line.startswith('bind-key o '))
        binding_file = Path(directory, 'binding.conf')
        access_hooks = [line for line in (repository_root / 'tmux_config/.tmux.conf').read_text().splitlines()
                        if line.startswith('set-hook ') and 'record-access' in line]
        binding_file.write_text('\n'.join([binding, 'set-option -g focus-events on', *access_hooks]).replace(
            '~/.tmux/navigation/search.py', search_script) + '\n')
        tmux('source-file', str(binding_file))
        client_pid, terminal = pty.fork()
        if client_pid == 0:
            os.environ['TERM'] = 'xterm-256color'
            os.execvp('tmux', ['tmux', '-S', socket, 'attach-session', '-t', 'other-session'])
        fcntl.ioctl(terminal, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 100, 0, 0))
        def read_until(expected, timeout=8):
            output = b''
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if select.select([terminal], [], [], .1)[0]:
                    output += os.read(terminal, 65536)
                    if expected in output:
                        return output
            raise AssertionError((expected, re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]', b'', output).decode(errors='replace')[-5000:]))
        read_until(b'other-ses')
        active_pane = tmux('display-message', '-p', '#{pane_id}')
        access_deadline = time.monotonic() + 5
        while time.monotonic() < access_deadline:
            pane_access = tmux('display-message', '-p', '-t', active_pane, '#{@agent_pane_access}')
            if pane_access.isdigit():
                break
            time.sleep(.05)
        assert pane_access.isdigit(), 'Focus hook did not record the active pane'
        assert tmux('show-options', '-w', '-v', '-t', active_pane, '@agent_window_access') == pane_access
        os.write(terminal, b'\x02o')
        output = read_until(b'Window / branch / PR')
        preview_output = read_until(b'Recorded branches / PRs') if b'Recorded branches / PRs' not in output else output
        assert b'claude-pr-123-security' not in output + preview_output
        assert tmux('display-message', '-p', '#{client_width}x#{client_height}') == '100x40'
        os.write(terminal, b'second\r')
        observed_output = b''
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if tmux('display-message', '-p', '#{session_name}:#{pane_id}') == f'first-session:{pane_one}':
                break
            if select.select([terminal], [], [], .1)[0]:
                observed_output += os.read(terminal, 65536)
            os.write(terminal, b'\r')
        else:
            raise AssertionError(('Picker did not switch', tmux('list-clients', '-F', '#{client_name}:#{session_name}:#{pane_id}'), observed_output[-5000:]))
        # A PR URL has no fuzzy match; Enter must still submit it for resolution.
        gh_script = Path(gh_directory, 'gh')
        gh_script.write_text('#!/bin/sh\ncase "$2" in */999) branch=absent ;; */124) branch=feature-claimed ;; *) branch=first ;; esac\nprintf \'{"head":{"repo":{"full_name":"owner/repo"},"ref":"%s"}}\' "$branch"\n')
        gh_script.chmod(0o755)
        tmux('set-environment', '-g', 'PATH', gh_directory + ':' + os.environ['PATH'])
        tmux('switch-client', '-t', 'other-session')
        while select.select([terminal], [], [], .5)[0]:
            os.read(terminal, 65536)
        os.write(terminal, b'\x02o')
        read_until(b'Window / branch / PR')
        os.write(terminal, b'https://github.com/owner/repo/pull/123')
        read_until(b'PR #123')
        os.write(terminal, b'\x0f')  # Ctrl+O opens Chrome without navigating tmux.
        read_until(b'Opened 1 PR(s) in Chrome.')
        assert chrome_arguments_path.read_text().splitlines() == [
            '-a', 'Google Chrome', 'https://github.com/owner/repo/pull/123']
        assert tmux('display-message', '-p', '#{session_name}') == 'other-session'
        read_until(b'PR #123')
        os.write(terminal, b'\r')
        observed_output = b''
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if tmux('display-message', '-p', '#{session_name}:#{pane_id}') == f'first-session:{pane_one}':
                break
            if select.select([terminal], [], [], .1)[0]:
                observed_output += os.read(terminal, 65536)
            os.write(terminal, b'\r')
        else:
            raise AssertionError(('PR URL failed', observed_output[-3500:]))
        # Missing history stays in the picker, and clearing the URL restores normal search.
        tmux('switch-client', '-t', 'other-session')
        while select.select([terminal], [], [], .5)[0]:
            os.read(terminal, 65536)
        os.write(terminal, b'\x02o')
        read_until(b'Window / branch / PR')
        os.write(terminal, b'https://github.com/owner/repo/pull/999')
        read_until(b'No tmux pane has recorded absent')
        os.write(terminal, b'\x15second')
        read_until(b'Recorded branches / PRs')
        os.write(terminal, b'\r')
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if tmux('display-message', '-p', '#{session_name}:#{pane_id}') == f'first-session:{pane_one}':
                break
            if select.select([terminal], [], [], .1)[0]:
                os.read(terminal, 65536)
        else:
            raise AssertionError('Text search did not recover after a missing PR association')
        # Probe the underlying terminal directly: popup input must never reach its command.
        shell_input_path = Path(directory, 'shell-input.txt')
        tmux('new-session', '-d', '-s', 'input-probe', '/bin/sh', '-c',
             'stty -echo; exec cat > ' + shlex.quote(str(shell_input_path)))
        tmux('switch-client', '-t', 'input-probe')
        while select.select([terminal], [], [], .3)[0]:
            os.read(terminal, 65536)
        os.write(terminal, b'\x02o')
        read_until(b'Window / branch / PR')
        os.write(terminal, b'text-that-must-stay-in-popup')
        read_until(b'text-that-must-stay-in-popup')
        os.write(terminal, b'\x03')  # Cancel without Escape/Alt sequence timing.
        while select.select([terminal], [], [], .3)[0]:
            os.read(terminal, 65536)
        assert shell_input_path.read_bytes() == b'', 'Canceled picker leaked input to the original shell'
        os.write(terminal, b'\x02o')
        read_until(b'Window / branch / PR')
        os.write(terminal, b'https://github.com/owner/repo/pull/123')
        read_until(b'PR #123')
        os.write(terminal, b'\r')
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if tmux('display-message', '-p', '#{session_name}:#{pane_id}') == f'first-session:{pane_one}':
                break
            if select.select([terminal], [], [], .1)[0]:
                os.read(terminal, 65536)
        else:
            raise AssertionError('Picker did not navigate away from shell input probe')
        assert shell_input_path.read_bytes() == b'', 'Picker selection leaked input to the original shell'
        # Create and claim an actual separate worktree, then attach its PR to that claim.
        command('git', '-C', repository, '-c', 'user.name=Test', '-c', 'user.email=test@example.com',
                '-c', 'core.hooksPath=/dev/null', 'commit', '--allow-empty', '-m', 'Initial')
        tmux('new-session', '-d', '-s', 'claimed-session', '-c', repository)
        source_pane_id = tmux('display-message', '-p', '-t', 'claimed-session', '#{pane_id}')
        claimed_checkout = str(Path(directory, 'claimed-worktree'))
        start_result = subprocess.run(['python3', search_script, 'start', 'feature-claimed', '--checkout', claimed_checkout,
                                       '--name', 'Claimed feature', '--pane', source_pane_id],
                                      cwd=repository, env=environment, capture_output=True, text=True)
        assert start_result.returncode == 0, start_result.stderr
        claimed_pane_id = next(line.removeprefix('Pane: ') for line in start_result.stdout.splitlines() if line.startswith('Pane: '))
        assert claimed_pane_id != source_pane_id, start_result.stdout
        assert tmux('display-message', '-p', '-t', claimed_pane_id, '#{session_id}') == tmux(
            'display-message', '-p', '-t', source_pane_id, '#{session_id}')
        assert tmux('display-message', '-p', '-t', claimed_pane_id, '#{window_name}') == 'Claimed feature'
        assert tmux('display-message', '-p', '-t', source_pane_id, '#{@agent_nav_owner}') == ''
        # Starting again reuses both the existing worktree and its one owning window.
        repeated_start = subprocess.run(['python3', search_script, 'start', 'feature-claimed',
                                         '--checkout', str(Path(directory, 'unused-worktree')), '--pane', source_pane_id],
                                        cwd=repository, env=environment, check=True, capture_output=True, text=True)
        assert f'Pane: {claimed_pane_id}' in repeated_start.stdout, repeated_start.stdout
        assert not Path(directory, 'unused-worktree').exists()
        claim_environment = {**environment, 'PATH': test_environment['PATH']}
        subprocess.run(['python3', search_script, 'claim', 'https://github.com/owner/repo/pull/124',
                        '--checkout', claimed_checkout, '--pane', claimed_pane_id],
                       env=claim_environment, check=True, capture_output=True)
        self_claim = json.loads(tmux('show-options', '-wqv', '-t', claimed_pane_id, '@agent_nav_owner'))
        assert self_claim['branch'] == 'feature-claimed'
        assert self_claim['checkout'] == str(Path(claimed_checkout).resolve())
        assert self_claim['url'] == 'https://github.com/owner/repo/pull/124'
        assert self_claim['description'] == 'Claimed feature'
        # A sibling shell starts in the owned worktree even after the source pane changes cwd.
        tmux('send-keys', '-t', claimed_pane_id, 'cd /tmp', 'Enter')
        directory_deadline = time.monotonic() + 5
        while time.monotonic() < directory_deadline:
            if Path(tmux('display-message', '-p', '-t', claimed_pane_id, '#{pane_current_path}')).resolve() == Path('/tmp').resolve():
                break
            time.sleep(.05)
        else:
            raise AssertionError('Source shell did not change directory before the split test')
        split_bindings = [line for line in (repository_root / 'tmux_config/.tmux.conf').read_text().splitlines()
                          if line.startswith(('bind-key s split-window', 'bind-key v split-window',
                                              'bind-key % split-window', 'bind-key \'"\' split-window'))]
        split_config = Path(directory, 'splits.conf')
        split_config.write_text('\n'.join(split_bindings) + '\n')
        tmux('source-file', str(split_config))
        # Split keybindings run in the selected window; tmux expands -c in that context.
        tmux('select-window', '-t', claimed_pane_id)
        tmux('select-pane', '-t', claimed_pane_id)
        split_pane = tmux('split-window', '-d', '-P', '-F', '#{pane_id}', '-t', claimed_pane_id,
                          '-c', '#{?@agent_nav_checkout,#{@agent_nav_checkout},#{pane_current_path}}')
        directory_deadline = time.monotonic() + 5
        while time.monotonic() < directory_deadline:
            split_directory = tmux('display-message', '-p', '-t', split_pane, '#{pane_current_path}')
            if Path(split_directory).resolve() == Path(claimed_checkout).resolve():
                break
            time.sleep(.05)
        else:
            raise AssertionError((split_directory, claimed_checkout, tmux('show-options', '-w', '-t', split_pane)))
        conflicting_claim = subprocess.run(['python3', search_script, 'claim', '--checkout', repository, '--pane', split_pane],
                                           env=environment, capture_output=True, text=True)
        assert conflicting_claim.returncode != 0 and 'already owns feature-claimed' in conflicting_claim.stderr
        duplicate_claim = subprocess.run(['python3', search_script, 'claim', '--checkout', claimed_checkout, '--pane', source_pane_id],
                                         env=environment, capture_output=True, text=True)
        assert duplicate_claim.returncode != 0 and 'already belongs to window' in duplicate_claim.stderr
        assert command('git', '-C', repository, 'branch', '--show-current') == 'second'
        # Both recorded URLs and previous successful lookups work without GitHub.
        gh_script.write_text('#!/bin/sh\nexit 91\n')
        for pr_number, destination in [('123', f'first-session:{pane_one}'),
                                       ('124', f'claimed-session:{claimed_pane_id}')]:
            tmux('switch-client', '-t', 'other-session')
            while select.select([terminal], [], [], .3)[0]:
                os.read(terminal, 65536)
            os.write(terminal, b'\x02o')
            read_until(b'Window / branch / PR')
            os.write(terminal, f'https://github.com/owner/repo/pull/{pr_number}'.encode())
            read_until(f'PR #{pr_number}'.encode())
            os.write(terminal, b'\r')
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                if tmux('display-message', '-p', '#{session_name}:#{pane_id}') == destination:
                    break
                if select.select([terminal], [], [], .1)[0]:
                    os.read(terminal, 65536)
            else:
                raise AssertionError(f'Offline PR lookup did not navigate to {destination}')
        # Ctrl+D edits repository scope independently of the window/branch query.
        tmux('rename-window', '-t', claimed_pane_id, 'Scope agent')
        other_repository = str(Path(directory, 'other-repository'))
        command('git', 'init', '-b', 'other', other_repository)
        command('git', '-C', other_repository, 'remote', 'add', 'origin', 'git@github.com:owner/other.git')
        tmux('new-session', '-d', '-s', 'scope-other', '-c', other_repository)
        other_pane_id = tmux('display-message', '-p', '-t', 'scope-other', '#{pane_id}')
        tmux('rename-window', '-t', other_pane_id, 'Scope decoy')
        subprocess.run(['python3', search_script, 'claim', '--checkout', other_repository, '--pane', other_pane_id],
                       env=environment, check=True, capture_output=True)
        tmux('switch-client', '-t', 'other-session')
        while select.select([terminal], [], [], .3)[0]:
            os.read(terminal, 65536)
        os.write(terminal, b'\x02o')
        read_until(b'Window / branch / PR')
        os.write(terminal, b'Scope')
        read_until(b'Scope')
        os.write(terminal, b'\x04')
        read_until(b'Repository >')
        os.write(terminal, b'owner/other\r')
        read_until(b'Window / branch / PR')
        # Canceling an edit retains the previously committed repository scope.
        os.write(terminal, b'\x04')
        read_until(b'Repository >')
        os.write(terminal, b'\x15owner/repo')
        read_until(b'owner/repo')
        os.write(terminal, b'\x03')
        canceled_scope_output = read_until(b'Window / branch / PR')
        if b'owner/other' not in canceled_scope_output:
            read_until(b'owner/other')
        # Clearing the repository query reveals the All repositories choice again.
        os.write(terminal, b'\x04')
        read_until(b'Repository >')
        os.write(terminal, b'\x15nonexistent-repository')
        read_until(b'nonexistent-repository')
        os.write(terminal, b'\x15\r')
        read_until(b'Window / branch / PR')
        os.write(terminal, b'\x04')
        read_until(b'Repository >')
        os.write(terminal, b'owner/repo\r')
        scoped_output = read_until(b'Window / branch / PR')
        if b'Scope' not in scoped_output:
            read_until(b'Scope')
        os.write(terminal, b'\r')
        navigation_output = b''
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if tmux('display-message', '-p', '#{session_name}:#{pane_id}') == f'claimed-session:{claimed_pane_id}':
                break
            if select.select([terminal], [], [], .1)[0]:
                navigation_output += os.read(terminal, 65536)
        else:
            raise AssertionError(('Repository filter lost the query or navigated to the wrong repository',
                                  tmux('list-clients', '-F', '#{session_name}:#{pane_id}'),
                                  scoped_output[-2000:], navigation_output[-3000:]))
        print('PASS: preview, reviewer filtering, branch/PR lookup, query recovery, clean shell input, real worktree/PR claims, offline recorded/cached PR lookup, and repository dropdown select/cancel/clear')
    finally:
        tmux('kill-server')
        if 'terminal' in locals():
            os.close(terminal)
            os.waitpid(client_pid, 0)
