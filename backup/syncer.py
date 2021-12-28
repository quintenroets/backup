import sys
import time

from libs.cli import Cli
from libs.gui import Gui
from libs.climessage import ask

from .backupmanager import BackupManager
from .path import Path

def main():
    while True:
        #time.sleep(8 * 60 * 60)
        time.sleep(10 * 60)
        check_changes()

def check_changes():
    interactive = sys.stdin.isatty()
    if interactive:
        title = "Drive"
        print(title + "\n" + "=" * (len(title) + 2) )
        
    changes = BackupManager.check("status")
    
    if changes:
        check_ignores = [f"* {ig}" for ig in Path.check_ignores.load()]
        changes = [c for c in changes if c not in check_ignores and not c.startswith("=")]

    if changes:
        process_changes(changes)
    elif interactive:
        input("\nEveryting clean.\nPress enter to exit")


def process_changes(changes):
    interactive = sys.stdin.isatty()
    title = "Push changes?"
    question = "\n".join([
        " " * 10 + title + " " * 10,
        "=" * (len(title) + 10),
        "",
        *changes
    ])
    push_changes = not interactive or ask("\nPush?")
    #push_changes = Gui.ask_yn(question) if not interactive else ask("\nPush?")
    if push_changes:
        filters = [f"+ {c[2:]}" for c in changes]
        BackupManager.check("push", filters=filters)

if __name__ == "__main__":
    main()
