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
    test_environment = {**os.environ, 'PATH': gh_directory + ':' + os.environ['PATH']}
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
    environment = {**os.environ, 'TMUX': f'{socket},0,0', 'TMUX_PANE': pane_one}
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
        tmux('new-session', '-d', '-s', 'other-session')
        tmux('new-session', '-d', '-s', 'claude-pr-123-security', '-c', repository)
        binding = next(line for line in (repository_root / 'tmux_config/.tmux.conf').read_text().splitlines() if line.startswith('bind-key o '))
        binding_file = Path(directory, 'binding.conf')
        binding_file.write_text(binding.replace('~/.agent-notify/navigation/search.py', search_script) + '\n')
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
        os.write(terminal, b'\x1b')
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
        claimed_pane_id = tmux('display-message', '-p', '-t', 'claimed-session', '#{pane_id}')
        claimed_checkout = str(Path(directory, 'claimed-worktree'))
        subprocess.run(['python3', search_script, 'start', 'feature-claimed', '--checkout', claimed_checkout,
                        '--pane', claimed_pane_id], cwd=repository, env=environment, check=True, capture_output=True)
        claim_environment = {**environment, 'PATH': test_environment['PATH']}
        subprocess.run(['python3', search_script, 'claim', 'https://github.com/owner/repo/pull/124',
                        '--checkout', claimed_checkout, '--pane', claimed_pane_id],
                       env=claim_environment, check=True, capture_output=True)
        claimed_options = tmux('show-options', '-p', '-t', claimed_pane_id)
        claims = [json.loads(shlex.split(line)[1]) for line in claimed_options.splitlines()
                  if line.startswith('@agent_nav_') and not line.startswith('@agent_nav_directory ')]
        self_claim = next(association for association in claims if association.get('source') == 'claim')
        assert self_claim['branch'] == 'feature-claimed'
        assert self_claim['checkout'] == str(Path(claimed_checkout).resolve())
        assert self_claim['url'] == 'https://github.com/owner/repo/pull/124'
        assert command('git', '-C', repository, 'branch', '--show-current') == 'second'
        print('PASS: preview, reviewer filtering, branch/PR lookup, query recovery, clean shell input, and real worktree/PR claims')
    finally:
        tmux('kill-server')
        if 'terminal' in locals():
            os.close(terminal)
            os.waitpid(client_pid, 0)
