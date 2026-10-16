"""Exercise the real popup and fzf in an isolated tmux server (no GitHub calls)."""
import fcntl
import json
import os
import pty
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
    repository = directory + '/repository'
    os.mkdir(repository)
    def command(*arguments, **kwargs):
        return subprocess.check_output(arguments, text=True, **kwargs).strip()
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
        assert options.count('@agent_nav_') == 2, options
        tmux('new-session', '-d', '-s', 'other-session')
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
            raise AssertionError((expected, output[-3000:]))
        read_until(b'other-ses')
        os.write(terminal, b'\x02o')
        output = read_until(b'Window / branch / PR')
        assert tmux('display-message', '-p', '#{client_width}x#{client_height}') == '100x40'
        os.write(terminal, b'second\r')
        observed_output = b''
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if tmux('display-message', '-p', '#{session_name}:#{pane_id}') == f'first-session:{pane_one}':
                break
            if select.select([terminal], [], [], .1)[0]:
                observed_output += os.read(terminal, 65536)
        else:
            raise AssertionError(('Picker did not switch', tmux('list-clients', '-F', '#{client_name}:#{session_name}:#{pane_id}'), observed_output[-5000:]))
        # A PR URL has no fuzzy match; Enter must still submit it for resolution.
        gh_directory = directory + '/bin'
        os.mkdir(gh_directory)
        gh_script = Path(gh_directory, 'gh')
        gh_script.write_text('#!/bin/sh\nprintf \'%s\' \'{"head":{"repo":{"full_name":"owner/repo"},"ref":"first"}}\'\n')
        gh_script.chmod(0o755)
        tmux('set-environment', '-g', 'PATH', gh_directory + ':' + os.environ['PATH'])
        tmux('switch-client', '-t', 'other-session')
        while select.select([terminal], [], [], .5)[0]:
            os.read(terminal, 65536)
        os.write(terminal, b'\x02o')
        read_until(b'Window / branch / PR')
        os.write(terminal, b'https://github.com/owner/repo/pull/123\r')
        observed_output = b''
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if tmux('display-message', '-p', '#{session_name}:#{pane_id}') == f'first-session:{pane_one}':
                break
            if select.select([terminal], [], [], .1)[0]:
                observed_output += os.read(terminal, 65536)
        else:
            raise AssertionError(('PR URL failed', observed_output[-3500:]))
        print('PASS: history retained, full-size popup opens, branch and PR URL select across sessions')
    finally:
        tmux('kill-server')
        if 'terminal' in locals():
            os.close(terminal)
            os.waitpid(client_pid, 0)
