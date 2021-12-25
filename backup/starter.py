import sys
from .backupmanager import BackupManager
from .syncer import check_changes
from . import watch_syncer

def main():
    args = sys.argv[1:]

    if not args:
        check_changes()
    elif "syncer" in args:
        BackupManager.subcheck()
    else:
        action = "status"
        for action_name in ["push", "pull"]:
            if action_name in args:
                action = action_name

        if "browser" in args:
            BackupManager.check_browser(action)
        else:
            BackupManager.check(action)

if __name__ == "__main__":
    main()
