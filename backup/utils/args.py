import argparse
from enum import Enum


class Action(Enum):
    status = "status"
    push = "push"
    pull = "pull"
    diff = "diff"


class ArgumentParser(argparse.ArgumentParser):
    def __init__(self):
        super().__init__(description="Automate backup process")

    def add_option(self, name: str, help_message: str):
        dest = name.replace("-", "_")
        super().add_argument(
            f"--{name}",
            dest=dest,
            default=False,
            const=True,
            help=help_message,
            action="store_const",
        )


def get_args():
    parser = ArgumentParser()
    actions_string = ", ".join(action.name for action in Action)
    parser.add_argument(
        "action",
        type=Action,
        nargs="?",
        help=f"The action to do [{actions_string}]",
        default=Action.push,
    )
    parser.add_argument(
        "items",
        nargs="*",
        help="The items to run the action on",
    )
    parser.add_option("subcheck", "only check subpath of current working directory")
    parser.add_option("include-browser", "check browser config")
    parser.add_option("configure", "open configuration")
    parser.add_option("no-sync", "don't sync remote changes when pulling from remote")
    parser.add_option("export-resume", "export remote resume changes")
    parser.add_option("all", "diff all files")
    parser.add_option("show-diff", "show file diffs")
    return parser.parse_args()
