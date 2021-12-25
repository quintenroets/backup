import pyinotify
import os
import json

from libs.threading import Thread

from .backupmanager import BackupManager
from .path import Path

class Watcher:
    def __init__(self, folder=None):
        self.threads = []
        self.max_threads = 1
        self.folder = folder if folder else os.getcwd()


    def process_event(self, event):
        path = event.pathname

        if not any([path.endswith(end) for end in [".kate-swp", ".part", ".py~"]]):
            if not any([f in path for f in BackupManager.ignore_names]):
                filename = path.replace(self.folder, "")
                print(filename)
                filters = [f"+ {filename}"]
                BackupManager.subcheck(custom_filters=filters, command="push")

    def watch(self, folder=None):
        mask = (
            pyinotify.IN_CLOSE_WRITE
            | pyinotify.IN_CREATE
            #| pyinotify.IN_MOVED_FROM
            #| pyinotify.IN_MOVED_TO
            | pyinotify.IN_DELETE
            #| pyinotify.IN_MODIFY
            #| pyinotify.IN_ATTRIB
        )

        watcher = pyinotify.WatchManager()
        if folder is None:
            folder = self.folder
        watcher.add_watch(folder, mask, self.process_event, rec=True)

        notifier = pyinotify.Notifier(watcher)
        notifier.loop()

def main():
    syncs = Path.syncs.load()
    for path in syncs:
        Watcher().watch(path)
