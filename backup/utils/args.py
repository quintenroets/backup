import argparse


class ArgumentParser(argparse.ArgumentParser):
    def __init__(self):
        super().__init__(description="Automate backup process")

    def add_option(self, name, help):
        super().add_argument(
            f"--{name}",
            dest=name.replace("-", "_"),
            default=False,
            const=True,
            help=help,
            action="store_const",
        )


def get_args():
    parser = ArgumentParser()
    parser.add_argument(
        "action",
        nargs="?",
        help="The action to do [status, push, pull]",
        default="push",
    )
    parser.add_option("subcheck", "only check subpath of current working directory")
    parser.add_option("browser", "check browser config")
    parser.add_option("configure", "open configuration")
    parser.add_option("no-sync", "don't sync remote changes when pulling from remote")
    return parser.parse_args()
