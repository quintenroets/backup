import sys
import time
from threading import Thread

from libs.cli import Cli
from libs.gui import Gui
from libs.output_copy import Output

from .backupmanager import BackupManager

def main():
    while True:
        time.sleep(8 * 60 * 60)
        Thread(target=check_changes).start()

def check_changes():
    interactive = sys.stdin.isatty()
    if interactive:
        title = "Drive"
        print(title + "\n" + "=" * (len(title) + 2) )
        
    with Output() as out:
        BackupManager.check("status")

    check_ignores = [f"* {ig}" for ig in Path.check_ignores.load()]
    changes = [
        o for o in str(out).split("\n") if o and (interactive or o not in check_ignores)
    ]

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
    push_changes = Gui.ask_yn(question) if not interactive else input("\nPush? [Y/n]") == ""
    if push_changes:
        print("Pushing..")
        Cli.run("drive push")

if __name__ == "__main__":
    main()
