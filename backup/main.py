import argparse

import cli

from . import harddrive, setup
from .backupmanager import BackupManager, subcheck
from .path import Path


def main():
    setup.check_setup()
    parser = argparse.ArgumentParser(description="Automate backup process")
    parser.add_argument(
        "action",
        nargs="?",
        help="The action to do [status, push, pull, sync, check]",
        default="push",
    )
    parser.add_argument("option", nargs="?", help="Check browser or not", default="")
    parser.add_argument(
        "--subcheck",
        default=False,
        const=True,
        help="only check subpath of current working directory",
        action="store_const",
    )
    args = parser.parse_args()

    if args.option == "browser":
        BackupManager.check_browser(args.action)
    else:
        match args.action:
            case "browser":
                BackupManager.check_browser(args.option)
            case "status":
                BackupManager.status()
            case "push":
                BackupManager.push()
            case "pull":
                BackupManager.pull(args.subcheck)
            case "sync":
                subcheck(command=args.option)
            case "harddrive":
                harddrive.check(args.option)
            case "paths":
                cli.urlopen(Path.paths)


if __name__ == "__main__":
    main()
