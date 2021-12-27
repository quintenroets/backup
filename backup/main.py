import argparse

from libs.errorhandler import ErrorHandler

from .backupmanager import BackupManager
from .syncer import check_changes


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
        BackupManager.check(args.action)


if __name__ == "__main__":
    main()
