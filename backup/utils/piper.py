import subprocess


def run(commands):
    pipe = subprocess.PIPE
    stdin = None
    process = None
    last_command_index = len(commands) - 1
    for i, args in enumerate(commands):
        stdout = None if i == last_command_index else pipe
        process = subprocess.Popen(args, stdout=stdout, stdin=stdin)
        stdin = process.stdout  # noqa
    process.communicate()
