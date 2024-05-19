import select
import subprocess
from collections.abc import Iterator

import cli
from cli.commands.runner import Runner


def generate_output_lines(runner: Runner[str]) -> Iterator[str]:
    runner.stdout = subprocess.PIPE
    runner.stderr = subprocess.PIPE
    process = runner.launch()
    extracted_outputs = extract_output_lines(process)
    error_lines = []
    output_generated = False
    for line, is_stdout in extracted_outputs:
        if is_stdout:
            output_generated = True
            yield line
        else:
            error_lines.append(line)
    if not output_generated and error_lines:
        message = "\n".join(error_lines)
        raise cli.CalledProcessError(message)


def extract_output_lines(process: subprocess.Popen[str]) -> Iterator[tuple[str, bool]]:
    outputs = [process.stdout, process.stderr]
    while outputs:
        readable_outputs, _, _ = select.select(outputs, [], [])
        for output in readable_outputs:
            line = output.readline().strip()
            if line:
                yield line, output is process.stdout
            else:
                outputs.remove(output)
