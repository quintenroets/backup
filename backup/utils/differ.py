import cli

from .path import Path


def get_diff(
    path: Path, source_root: Path, dest_root: Path, color=True, max_lines: int = 20
):
    diff_command = "diff", "-u", "--new-file", dest_root / path, source_root / path
    if color:
        diff_command = *diff_command, "--color=always"
    return cli.lines(*diff_command, check=False)[2 : 2 + max_lines]


def run_diff(*args, **kwargs):
    diff_lines = get_diff(*args, **kwargs)
    message = "\n".join(diff_lines)
    print(message)
