import pyinotify
from rich import pretty

from . import backupmanager
from .path import Path


class Watcher:
    def __init__(self, path):
        self.path = Path(path or Path.cwd())

    def process_event(self, event):
        path = Path(event.pathname)
        if path.suffix not in [".kate-swp", ".part", ".py~"]:
            if not any(
                [f in path.parts for f in backupmanager.BackupManager.ignore_names]
            ):
                subpath = path.relative_to(self.path)
                pretty.pprint(subpath)
                filters = [f"+ {subpath}", "- **"]
                backupmanager.subcheck(custom_filters=filters, command="push")

    def watch(self):
        mask = (
            pyinotify.IN_CLOSE_WRITE
            | pyinotify.IN_CREATE
            | pyinotify.IN_MOVED_FROM
            | pyinotify.IN_MOVED_TO
            | pyinotify.IN_DELETE
            | pyinotify.IN_MODIFY
            | pyinotify.IN_ATTRIB
        )
        watcher = pyinotify.WatchManager()
        watcher.add_watch(str(self.path), mask, self.process_event, rec=True)
        pyinotify.Notifier(watcher).loop()


def main():
    syncs = Path.syncs.load()
    for path in syncs:
        Watcher(Path.HOME / path).watch()
