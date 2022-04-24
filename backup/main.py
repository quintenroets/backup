import argparse

from . import harddrive
from .backupmanager import BackupManager, subcheck


def main():
    parser = argparse.ArgumentParser(description="Automate common git workflows")
    parser.add_argument(
        "action",
        nargs="?",
        help="The action to do [status, push, pull, sync, check]",
        default="push",
    )
    parser.add_argument("option", nargs="?", help="Check browser or not", default="")
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
                BackupManager.pull(args.option)
            case "sync":
                subcheck(command=args.option)
            case "harddrive":
                harddrive.check(args.option)


if __name__ == "__main__":
    main()
