import time
import argparse

from libs.cli import Cli
from libs.errorhandler import ErrorHandler
from libs.path import Path

from .backup import Backup
from .backupmanager import BackupManager


def main():
    with ErrorHandler():
        _main()


def _main():
    parser = argparse.ArgumentParser(description='Automate common git workflows')
    parser.add_argument('action', nargs='?', help='The action to do [status, push, pull, sync, check]', default="push")
    parser.add_argument('option', nargs='?', help='Check browser or not', default="")
    args = parser.parse_args()
        
    if args.option == "browser":
        BackupManager.check_browser(args.action)
    elif args.action == "status":
        BackupManager.status()
    elif args.action == "push":
        BackupManager.push()
    elif args.action == "pull":
        BackupManager.pull(args.option)


if __name__ == "__main__":
    main()
