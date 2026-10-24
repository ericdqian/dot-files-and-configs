"""Verify the new-tab command returns to a usable shell after tmux detach."""
import fcntl
import importlib.util
import os
import pty
import select
import shlex
import shutil
import signal
import struct
import subprocess
import tempfile
import termios
import time
from pathlib import Path

module_spec = importlib.util.spec_from_file_location('search', Path(__file__).with_name('search.py'))
search = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(search)

with tempfile.TemporaryDirectory(prefix='tmux-detach-', dir='/tmp') as test_directory:
    socket_path = str(Path(test_directory, 'socket'))
    shell_arguments_path = Path(test_directory, 'shell-arguments')
    shell_environment_path = Path(test_directory, 'shell-environment')
    preferred_shell_path = Path(test_directory, 'login shell with spaces')
    preferred_shell_path.write_text(
        '#!/bin/sh\n'
        'printf "%s\\n" "$@" > ' + shlex.quote(str(shell_arguments_path)) + '\n'
        'printf "%s:%s" "${TMUX-unset}" "${TMUX_PANE-unset}" > '
        + shlex.quote(str(shell_environment_path)) + '\n'
        'exec /bin/zsh -f -i\n')
    preferred_shell_path.chmod(0o755)
    tmux_executable = shutil.which('tmux')
    tmux_command = [tmux_executable, '-f', '/dev/null', '-S', socket_path]
    subprocess.run([*tmux_command, 'new-session', '-d', '-s', 'dest', 'cat'], check=True)
    terminal = None
    client_pid = None
    client_reaped = False
    try:
        attach_command = search.session_tab_command(shutil.which('env'), str(preferred_shell_path),
                                                   tmux_executable, socket_path, 'dest')
        client_pid, terminal = pty.fork()
        if client_pid == 0:
            child_environment = {**os.environ, 'TERM': 'xterm-256color',
                                 'TMUX': 'must-not-be-inherited', 'TMUX_PANE': '%999'}
            os.execvpe(attach_command[0], attach_command, child_environment)
        fcntl.ioctl(terminal, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 100, 0, 0))

        def read_until(expected):
            terminal_output = b''
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                if select.select([terminal], [], [], .1)[0]:
                    terminal_output += os.read(terminal, 65536)
                    if expected in terminal_output:
                        return
            raise AssertionError((expected, terminal_output[-1000:]))

        read_until(b'dest')
        os.write(terminal, b'\x02d')
        deadline = time.monotonic() + 8
        while not shell_environment_path.exists() and time.monotonic() < deadline:
            if select.select([terminal], [], [], .1)[0]:
                os.read(terminal, 65536)
        assert shell_environment_path.exists(), 'Detach did not start the configured shell'
        assert shell_arguments_path.read_text().strip() == '-il'
        assert shell_environment_path.read_text() == 'unset:unset'
        assert os.waitpid(client_pid, os.WNOHANG) == (0, 0), 'Tab process exited on detach'
        subprocess.run([*tmux_command, 'has-session', '-t', 'dest'], check=True)
        os.write(terminal, b"printf 'SHELL_ALIVE_%s\\n' yes\r")
        read_until(b'SHELL_ALIVE_yes')
        os.write(terminal, b'exit\r')
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            completed_pid, exit_status = os.waitpid(client_pid, os.WNOHANG)
            if completed_pid:
                client_reaped = True
                assert os.waitstatus_to_exitcode(exit_status) == 0
                break
            if select.select([terminal], [], [], .05)[0]:
                try:
                    os.read(terminal, 65536)
                except OSError:
                    pass  # The PTY reports EOF as EIO on some platforms.
        else:
            raise AssertionError('Explicit exit did not close the shell')
        print('PASS: detach preserves the tab and session, starts a usable configured shell, and explicit exit closes it')
    finally:
        subprocess.run([*tmux_command, 'kill-server'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if client_pid is not None and not client_reaped:
            try:
                os.kill(client_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            os.waitpid(client_pid, os.WNOHANG)
        if terminal is not None:
            os.close(terminal)
