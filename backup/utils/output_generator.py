import select
import subprocess

import cli


def generate_output_lines(*args):
    process = cli.run(*args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, wait=False)

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
