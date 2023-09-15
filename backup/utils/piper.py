import cli


def run(commands):
    output = None
    for args in commands:
        output = cli.get(*args, input=output, check=False)
    return output
