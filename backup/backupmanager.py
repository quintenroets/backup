import getpass
import json
import os
import pathlib
import shutil
import sys
import xattr

from libs.cli import Cli
from libs.climessage import CliMessage
from libs.tagmanager import TagManager

from .backup import Backup
from .filemanager import FileManager

args = sys.argv[1:]

root_mapper = {
    "docs": os.environ["docs"],
    "config": os.environ["HOME"],
}
drive_mapper = {
    "docs": "Documents",
    "config": "Config",
}

class BackupManager:
    @staticmethod
    def check(command, path_name):
        if command in ["push", "status"]:
            BackupManager.before_push(path_name, export=command=="push")

        paths, subpaths = BackupManager.get_paths(path_name)

        if command in ["status", "push"]:
            items = BackupManager.get_items(paths)
            filters, new_paths = BackupManager.get_filters(path_name, items)
        else:
            if path_name == "config":
                filters = ["+ *"]
            else:
                filters = BackupManager.get_pull_filters(paths, subpaths, path_name)

        if filters:
            src = root_mapper[path_name]
            dst = drive_mapper[path_name]

            if command == "status":
                result = Backup.compare(src, dst, filters=filters)
                BackupManager.after_push(path_name)
            elif command == "push":
                result = Backup.upload(src, dst, filters=filters)
                FileManager.save(new_paths, "timestamps", path_name)
                BackupManager.after_push(path_name)
            elif command =="pull":
                result = Backup.download(src, dst, filters=filters, delete_missing=path_name=="docs")
                items = BackupManager.get_items(paths)
                filters, new_paths = BackupManager.get_filters(path_name, items)
                FileManager.save(new_paths, "timestamps", path_name)
                BackupManager.after_pull(path_name)

            return result

    @staticmethod
    def get_paths(path_name):
        path_root = root_mapper[path_name]

        struct_list = [{path_root: FileManager.load("paths", path_name)}]
        finished = False

        while not finished:
            new_struct_list = []
            finished = True

            for struct in struct_list:
                if not isinstance(struct, dict): # normal complete path
                    new_struct_list.append(struct)
                else:
                    for root, items in struct.items():
                        for item in items:
                            if not isinstance(item, dict):
                                new_item = os.path.join(root, item)
                            else:
                                finished = False
                                new_item = {
                                    os.path.join(root, subroot):
                                        subitems for subroot, subitems in item.items()
                                }
                            new_struct_list.append(new_item)

            struct_list = new_struct_list

        paths = struct_list
        subpaths = [p.replace(path_root + "/", "") for p in paths]
        return paths, subpaths

    @staticmethod
    def get_items(paths):
        ignore_folders = FileManager.load("paths", "ignores", "patterns")
        items = []
        for path in paths:
            if os.path.exists(path):
                if not os.path.isdir(path):
                    items.append(path)  # files are not visited in os walk

                else:
                    path_ignore_folders = ignore_folders + BackupManager.get_git_folders(path)
                    git_folders = BackupManager.get_git_folders(path)
                    for folder, subfolders, filenames in os.walk(path):
                        if ".git" not in subfolders and not(
                            any([ig in folder and ig not in path for ig in path_ignore_folders])
                        ):
                            for filename in filenames:
                                file_full = os.path.join(folder, filename)
                                if not BackupManager.ignore(file_full):
                                    items.append(file_full)

        return items

    @staticmethod
    def get_filters(path_name, paths):
        old_paths = FileManager.load("timestamps", path_name)
        root = root_mapper[path_name]
        new_paths = {
            path.replace(root + "/", ""):
            os.path.getmtime(path) if os.path.exists(path) else 0
            for path in paths
        }
        changed_paths = BackupManager.calculate_difference(new_paths, old_paths)
        filters = BackupManager.get_ignore_root_filters(path_name) + [f"+ /{p}" for p in changed_paths]
        return filters, new_paths

    @staticmethod
    def calculate_difference(new, old):
        new_copy = {k: v for k, v in new.items()}
        old_copy = {k: v for k, v in old.items()}

        if "all" not in args:
            for path in old:
                if path in new and new[path] == old[path]:
                    old_copy.pop(path)
                    new_copy.pop(path)

        paths = set(list(old_copy) + list(new_copy))
        return paths

    @staticmethod
    def get_pull_filters(paths, subpaths, path_name):
        filters = BackupManager.get_ignore_root_filters(path_name)
        ignore_patterns = FileManager.load("paths", "ignores", "patterns")
        filters += [f"- {ignore}/**" for ignore in ignore_patterns]

        for path, subpath in zip(paths, subpaths):
            if not os.path.isdir(path):
                filters.append(f"+ /{subpath}")
            else:
                filters += BackupManager.get_ignores(path, path_name)
                filters.append(f"+ /{subpath}/**")
        return filters

    @staticmethod
    def get_ignores(path, path_name):
        ignores = []
        root = root_mapper[path_name]

        for folder, subfolders, files in os.walk(path, followlinks=True):
            if os.path.islink(folder):
                ignores.append(f"- {folder.replace(root, '')}/**")
            else:
                for filename in files:
                    file_full = os.path.join(folder, filename)
                    if BackupManager.ignore(file_full):
                        subpath = file_full.replace(root, "")
                        filter = f"- {subpath}"
                        ignores.append(filter)

        ignores += [
            f"- {f.replace(root, '')}/**"  for f in BackupManager.get_git_folders(path)
        ]
        return ignores

    @staticmethod
    def get_git_folders(path):
        folders = Cli.get(
            f"find {path} -type d -execdir test -d" + " {}/.git \; -print -prune"
            ).split("\n")
        folders = [f for f in folders if f]
        return folders

    @staticmethod
    def before_push(path_name, export=True):
        if path_name == "config":
            from colortheme.thememanager import ThemeManager
            if ThemeManager.get_theme() == "dark":
                ThemeManager.change_config("dark", "light")
            if export:
                Cli.get(f"konsave -e $(konsave -l | grep {theme} | cut -f1)" for theme in ["light", "dark"])
            #"crontab -l > ~/.config/crontab.conf"

    @staticmethod
    def after_push(path_name):
        if path_name == "config":
            from colortheme.thememanager import ThemeManager
            if ThemeManager.get_theme() == "dark":
                ThemeManager.change_config("light", "dark")

    @staticmethod
    def after_pull(path_name):
        if path_name == "config":
            from colortheme.thememanager import ThemeManager
            # remove present themes
            Cli.get(*(f"konsave -r $(konsave -l | grep {t} | cut -f1)" for t in ["light", "dark"]), check=False)
            theme = ThemeManager.get_theme()
            if not theme:
                theme = "light"
                FileManager.save("light", "settings")
            Cli.get(
                "konsave -i ~/light.knsv",
                "konsave -i ~/dark.knsv",
                f"konsave -a $(konsave -l | grep {theme} | cut -f1)"
                #f"sudo cp ~/.config/crontab.conf /var/spool/cron/crontabs/{getpass.getuser()}"
            )
            ThemeManager.restartplasma()

    @staticmethod
    def get_ignore_root_filters(path_name):
        ignore_roots = FileManager.load("paths", "ignores", path_name)
        ignore_roots = [ig + "**" if ig.endswith("/") else ig for ig in ignore_roots]
        filters = [f"- /{ig}" for ig in ignore_roots]
        return filters

    @staticmethod
    def ignore(path):
        return (
            os.path.islink(path)
            or xattr.xattr(path).list()
            or os.path.getsize(path) > 50 * 10 ** 6
            or str(pathlib.Path(path).resolve()) != path
        )

    @staticmethod
    def check_browser(command):
        config_folder = os.path.join(os.environ["home"], "snap", "chromium", "common", "chromium", "Default")
        config_file = os.path.join(os.environ["docs"], "config.zip")
        local = os.environ["docs"]
        remote = "Browser"
        filters = ["+ /config.zip"]

        if command == "push":
            ignores = [
                "*/Cache/*",
                "*/Code Cache/*",
                "*/Application Cache/*",
                "*/CacheStorage/*",
                "*/ScriptCache/*",
                "*/GPUCache/"
            ]
            ignores = [f"-x '{i}' " for i in ignores]
            ignore = "".join(ignores)

            with CliMessage("Compressing.."):
                Cli.run(
                    f"cd '{os.path.dirname(config_folder)}'",
                    f"zip -r -q '{config_file}' '{os.path.basename(config_folder)}' {ignore}"
                )

            with CliMessage("Uploading.."):
                Backup.upload(local, remote, filters=filters)
                os.remove(config_file)

        elif command == "pull":
            Backup.download(local, remote, filters=filters)
            os.makedirs(config_folder, exist_ok=True)
            Cli.get(
                f"unzip -o '{config_file}' -d '{os.path.dirname(config_folder)}'"
            )
            os.remove(config_file)

        else:
            print("Choose pull or push")
