import os
import sys
import xattr
from pathlib import Path

from libs.cli import Cli
from libs.climessage import CliMessage
from libs.tagmanager import TagManager

from .backup import Backup
from .filemanager import FileManager
from .profilemanager import ProfileManager
from . import parser

args = sys.argv[1:]

root_mapper = {
    "docs": Path.docs,
    "config": Path.home(),
}
drive_mapper = {
    "docs": "Documents",
    "config": "Config",
}

class BackupManager:
    @staticmethod
    def check(command, path_name):
        paths = BackupManager.get_paths(path_name)

        if command in ["status", "push"]:
            ProfileManager.save_active()
            items = BackupManager.get_items(paths)
            #filters, new_paths = BackupManager.get_filters(path_name, items)
            return
        else:
            if path_name == "config":
                filters = ["+ **"]
            else:
                filters = BackupManager.get_pull_filters(paths, subpaths, path_name)

        if filters:
            src = root_mapper[path_name]
            dst = drive_mapper[path_name]

            if command == "status":
                result = Backup.compare(src, dst, filters=filters)
            elif command == "push":
                result = Backup.upload(src, dst, filters=filters)
                FileManager.save(new_paths, "timestamps", path_name)
            elif command =="pull":
                result = Backup.download(src, dst, filters=filters, delete_missing=path_name=="docs")
                items = BackupManager.get_items(paths)
                filters, new_paths = BackupManager.get_filters(path_name, items)
                FileManager.save(new_paths, "timestamps", path_name)
                BackupManager.after_pull(path_name)

            return result

    @staticmethod
    def get_paths(path_name):
        paths = (FileManager.root / "paths" / path_name).load()
        paths = parser.parse_paths(paths)
        return paths

    @staticmethod
    def get_items(paths):
        ignore_folders = FileManager.load("paths", "ignores", "patterns")
        def exclude(path: Path):
            return (
                path.name in ignore_folders
                or (path / ".git").exists()
                or BackupManager.ignore(path)
            )
        return [p.find(exclude=exclude) for p in paths]

    @staticmethod
    def get_filters(path_name, paths):
        old_paths = (FileManager.root / "timestamps" / path_name).load()
        root = root_mapper[path_name]
        new_paths = {}
        for p in paths:
            absolute = root / p
            if absolute.exists():
                new_paths[p] = absolute.stat().st_mtime

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
            if not os.path.isdir(path) and os.path.exists(path):
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
            ).split("\n") if os.path.exists(path) else []
        folders = [f for f in folders if f]
        return folders

    @staticmethod
    def after_pull(path_name):
        if path_name == "config":
            ProfileManager.reload()

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
            or str(Path(path).resolve()) != path
        )

    @staticmethod
    def check_browser(command):
        config_folder = Path.home() / "snap" / "chromium" / "common" / "chromium" / "Default"
        local = Path.home() / ".config" / "browser"
        config_file = local / "config.zip"

        remote = "Browser"
        filters = ["+ /config.zip"]

        if command == "push":
            ignores = ["Cache", "Code Cache", "Application Cache", "CacheStorage", "ScriptCache", "GPUCache"]
            flags = "".join([
                f"-x '*/{i}/*' " for i in ignores
            ])
            if config_file.exists():
                flags += " -f" # only add changes to zip

            with CliMessage("Compressing.."):
                # make sure that all zipped files have the same root
                Cli.run(f"zip -r -q {flags} '{config_file}' '{config_folder.name}'", pwd=config_folder.parent)
            with CliMessage("Uploading.."):
                Backup.upload(local, remote, filters=filters)

        elif command == "pull":
            Backup.download(local, remote, filters=filters)
            config_folder.mkdir(parents=True, exist_ok=True)
            Cli.get(f"unzip -o '{config_file}' -d '{config_folder.parent}'")
        else:
            print("Choose pull or push")
