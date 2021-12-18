import sys

from .backup import Backup
from .filemanager import FileManager

def main(custom_filters=[], command=None):
    syncs = FileManager.get_sync_paths()
    for local, remote in syncs.items():
        ignore_patterns = FileManager.load("paths", "ignores", "patterns")

        filters = [f"- {ignore}/**" for ignore in ignore_patterns]
        if custom_filters:
            filters += custom_filters
        else:
            filters.append("+ *")

        if "push" in sys.argv or command and command == "push":
            Backup.upload(local, remote, filters=filters)
        elif "pull" in sys.argv:
            Backup.download(local, remote, filters=filters)
        else:
            Backup.compare(local, remote, filters=filters)

if __name__ == "__main__":
    main()
