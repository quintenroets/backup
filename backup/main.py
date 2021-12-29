import argparse

from libs.errorhandler import ErrorHandler
from libs.path import Path

from .backupmanager import BackupManager
from .syncer import check_changes
from .parser import make_filters


def main():
    with ErrorHandler():
        _main()


def _main():
    parser = argparse.ArgumentParser(description='Automate common git workflows')
    parser.add_argument('action', nargs='?', help='The action to do [status, push, pull, sync, check]', default="check")
    parser.add_argument('option', nargs='?', help='Check browser or not', default="")
    
    args = parser.parse_args()
    if args.action == "check":
        check_changes()
    elif args.action == "sync":
        BackupManager.subcheck()
    elif args.option == "browser":
        BackupManager.check_browser(args.action)
    else:
        if "." in args.option:
            rec = args.option == ".."
            filters = make_filters(includes=[f"{Path.cwd().relative_to(Path.home)}/*"], recursive = rec)
        else:
            filters = None
        BackupManager.check(args.action, filters=filters)


if __name__ == "__main__":
    main()
