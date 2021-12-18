from pathlib import Path

from .backup import Backup
from .filemanager import FileManager


def start():
    # download path assets before other drive sync can happen
    Backup.download(FileManager.root, "Config/.config/scripts/backup", filters=["+ **"])
    # download core config files
    Backup.download(Path.home(), "Config", filters=["+ /.*"])


if __name__ == "__main__":
    start()