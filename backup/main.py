import time
import argparse

from libs.errorhandler import ErrorHandler
from libs.path import Path

from .backupmanager import BackupManager
from . import syncer


def main():
    with ErrorHandler():
        _main()


def _main():
    parser = argparse.ArgumentParser(description='Automate common git workflows')
    parser.add_argument('action', nargs='?', help='The action to do [status, push, pull, sync, check]', default="push")
    parser.add_argument('option', nargs='?', help='Check browser or not', default="")
    args = parser.parse_args()
    
    if parser.option == "browser":
        BackupManager.check_browser(args.action)
    elif args.action == "status":
        BackupManager.status()
    elif args.action == "push":
        BackupManager.push()
    elif args.action == "pull":
        BackupManager.pull()
    return
    if args.option:
        if "." in args.option:
            pattern = str(Path.cwd().relative_to(Path.Home)) + "/*"
            if args.option == "..":
                pattern += "*"
        else:
            mapper = {"school": "Documents/School/**"}
            pattern = mapper.get(args.option, args.option)
        filters = [f"+ /{pattern}"]
    else:
        filters = syncer.get_filters()
    BackupManager.check(args.action, filters=filters)


if __name__ == "__main__":
    main()
