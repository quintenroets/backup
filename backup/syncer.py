import sys
import time
from threading import Thread

from libs.cli import Cli
from libs.gui import Gui
from libs.output_copy import Output

from .backupmanager import BackupManager
from .filemanager import FileManager

def main():
    while True:
        time.sleep(8 * 60 * 60)
        Thread(target=check_changes).start()

def check_changes():
    interactive = sys.stdin.isatty()
    if interactive:
        title = "Drive"
        print(title + "\n" + "=" * (len(title) + 2) )
        
    total_changes = {}
    path_names = FileManager.get_path_names()
    for path_name in path_names:
        with Output() as out:
            BackupManager.check("status", path_name)
        output_list = str(out).split("\n")
        output_list = [o for o in output_list if o]
        total_changes[path_name] = output_list

    check_ignores = FileManager.load("paths", "check_ignores", "config")
    check_ignores = [f"* {ig}" for ig in check_ignores]
    changes = [c for changes in total_changes.values() for c in changes if c not in check_ignores or interactive]

    if changes:
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
            Cli.run(
                (f"drive push {path_name}" for path_name, filter_items in total_changes.items() if filter_items)
            )
    elif interactive:
        input("\nEveryting clean.\nPress enter to exit")

if __name__ == "__main__":
    main()
