import sys
from .backupmanager import BackupManager
from .filemanager import FileManager
from .syncer import check_changes
from . import watch_syncer

def main():
    args = sys.argv[1:]

    if "autodapt" in args:
        autodapt_syncer.main()

    elif not args:
        check_changes()

    else:
        action = "status"
        for action_name in ["push", "pull"]:
            if action_name in args:
                action = action_name

        if "browser" in args:
            BackupManager.check_browser(action)
        else:
            path_names = FileManager.get_path_names()
            for path_name in path_names:
                if path_name in args:
                    BackupManager.check(action, path_name)


if __name__ == "__main__":
    main()