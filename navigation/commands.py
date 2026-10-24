"""Run navigation commands without consuming interactive input."""
import subprocess


def run(command, check=False, input_text=None, timeout=20):
    # Noninteractive commands must never consume keys intended for the popup or shell.
    input_arguments = {'input': input_text} if input_text is not None else {'stdin': subprocess.DEVNULL}
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=timeout, **input_arguments)
    if check and result.returncode:
        raise ValueError(result.stderr.strip() or f'{command[0]} failed')
    return result.stdout.strip()
