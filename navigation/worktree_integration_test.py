"""Exercise pasted PR queries in cwt's real fzf using an isolated tmux server."""
import os
import shlex
import subprocess
import tempfile
import time
from pathlib import Path

repository_path = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='cwt-picker-') as test_directory:
    test_root = Path(test_directory)
    socket_path = test_root / 'tmux.sock'
    shell_directory = test_root / 'zsh_config'
    shell_directory.mkdir()
    (test_root / 'navigation').symlink_to(repository_path / 'navigation')
    shell_source = (repository_path / 'zsh_config/general_zsh_config').read_text()
    shell_fixture = shell_directory / 'worktrees.zsh'
    shell_fixture.write_text(shell_source[shell_source.index('cwt() {'):shell_source.index('dwt() {')])
    feature_path = test_root / 'feature checkout'
    main_path = test_root / 'main checkout'
    feature_path.mkdir()
    main_path.mkdir()
    binary_directory = test_root / 'bin'
    binary_directory.mkdir()
    gh_stub = binary_directory / 'gh'
    gh_stub.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
if sys.argv[1] == 'repo':
    print('https://github.com/owner/repo')
else:
    with Path(os.environ['GH_CALLS']).open('a') as calls:
        calls.write(sys.argv[-1] + '\\n')
    branch = 'missing' if sys.argv[-1].endswith('/999') else 'feature'
    print(json.dumps({'head': {'repo': {'full_name': 'owner/repo'}, 'ref': branch}}))
''')
    gh_stub.chmod(0o755)
    calls_path = test_root / 'gh-calls'
    test_environment = {**os.environ, 'PATH': str(binary_directory) + ':' + os.environ['PATH'],
                        'XDG_CACHE_HOME': str(test_root / 'cache'), 'GH_CALLS': str(calls_path),
                        'PYTHONDONTWRITEBYTECODE': '1'}
    def tmux(*arguments):
        return subprocess.check_output(['tmux', '-f', '/dev/null', '-S', str(socket_path), *arguments],
                                       text=True, env=test_environment).strip()
    tmux('new-session', '-d', '-s', 'cwt-test', '-x', '180', '-y', '45', 'zsh -f')
    def send(command):
        tmux('send-keys', '-l', command)
    def wait_for(expected):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            screen = tmux('capture-pane', '-p')
            if expected in screen:
                return screen
            time.sleep(.05)
        raise AssertionError((expected, screen))
    try:
        candidates = f'{main_path}\tmain\n{feature_path}\tfeature\n'
        with shell_fixture.open('a') as shell_file:
            shell_file.write('\n_emit_worktrees() { printf %s ' + shlex.quote(candidates) + '; }\n')
        setup_command = 'source ' + shlex.quote(str(shell_fixture)) + '; clear'
        send(setup_command)
        tmux('send-keys', 'Enter')
        for pr_query in ['https://github.com/owner/repo/pull/84', '#84', '84',
                         'https://github.com/owner/repo/pull/84/files?x=1#discussion']:
            send('cwt; print -r -- "SELECTED:$PWD"')
            tmux('send-keys', 'Enter')
            wait_for('worktree >')
            send(pr_query)
            wait_for('1/1')
            tmux('send-keys', 'Enter')
            wait_for('SELECTED:' + str(feature_path))
            send('clear')
            tmux('send-keys', 'Enter')
        assert calls_path.read_text().splitlines() == ['repos/owner/repo/pulls/84'], calls_path.read_text()
        send('cwt; print -r -- "RECOVERED:$PWD"')
        tmux('send-keys', 'Enter')
        wait_for('worktree >')
        send('https://github.com/owner/repo/pull/999')
        wait_for('No local worktree')
        tmux('send-keys', 'Enter')
        wait_for('Search updating or no destination')
        tmux('send-keys', 'C-u')
        send('main')
        wait_for('1/2')
        tmux('send-keys', 'Enter')
        wait_for('RECOVERED:' + str(main_path))
        send('cwt; print -r -- "CANCELLED:$PWD"')
        tmux('send-keys', 'Enter')
        wait_for('worktree >')
        tmux('send-keys', 'Escape')
        wait_for('CANCELLED:' + str(main_path))
        print('PASS: pasted PR URLs/numbers, shared cache, paths with spaces, missing-result Enter guard, fuzzy recovery, cancellation')
    finally:
        tmux('kill-server')
