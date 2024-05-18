import select
import subprocess
from collections.abc import Iterator
from typing import Any

import cli
from cli.commands.commands import CommandItem


def generate_output_lines(*args: CommandItem, **kwargs: Any) -> Iterator[str]:
    pipe = subprocess.PIPE
    process = cli.run(*args, stdout=pipe, stderr=pipe, wait=False, **kwargs)

    output_generated = False
    outputs = [process.stdout, process.stderr]
    error_lines = []
    while outputs:
        readable_outputs, _, _ = select.select(outputs, [], [])
        for output in readable_outputs:
            line = output.readline()
            if not line:
                outputs.remove(output)
            elif output is process.stdout:
                output_generated = True
                yield line.strip()
            elif not output_generated:
                error_lines.append(line.strip())

    if not output_generated and error_lines:
        message = "\n".join(error_lines)
        raise cli.CalledProcessError(message)
