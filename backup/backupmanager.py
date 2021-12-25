import os
import sys
import xattr

from libs.cli import Cli
from libs.climessage import CliMessage
from libs.tagmanager import TagManager

from .backup import Backup
from .path import Path
from .profilemanager import ProfileManager
from . import parser

args = sys.argv[1:]


class BackupManager:
    ignore_names = Path.ignore_names.load()
    ignore_patterns = Path.ignore_patterns.load()
    ignore_paths = {
        path
        for pattern in ignore_patterns
        for path in Path.home.glob(pattern)
    }
    timestamps = None

    @staticmethod
    def check(command, **kwargs):
        ProfileManager.save_active()
        filters = BackupManager.get_filters(pull=command == "pull")
        if filters:
            BackupManager.sync(command, filters, **kwargs)

    @staticmethod
    def sync(command, filters, src=Path.home, dst="Home"):
        kwargs = {"delete_missing": True} if command == "pull" else {}
        sync = Backup.get_function(command)
        sync(src, dst, filters=filters, **kwargs)

        if command != "status":
            BackupManager.save_timestamps()
        if command =="pull":
            ProfileManager.reload()

    @staticmethod
    def get_filters(pull=False):
        paths = BackupManager.get_paths(exclusions=pull)
        if pull:
            paths = [p.relative_to(Path.home) for p in paths] + BackupManager.ignore_patterns
        else:
            timestamps = Path.timestamps.load()
            BackupManager.timestamps = {
                str(p.relative_to(Path.home)): p.stat().st_mtime for p in paths if p.exists()
            }
            paths = BackupManager.calculate_difference(BackupManager.timestamps, timestamps)

        filters = parser.make_filters(
            includes=paths if not pull else [],
            excludes=paths if pull else [],
            recursive=False,
            include_others=pull
        )
        return filters

    @staticmethod
    def get_paths(exclusions=False):
        condition = BackupManager.exclude if exclusions else None
        exclude = BackupManager.exclude if not exclusions else None

        paths = Path.paths_include.load()
        paths = parser.parse_paths(paths)
        paths = [
            item for path in paths for item in (Path.home / path).find(condition=condition, exclude=exclude)
        ]
        return paths

    @staticmethod
    def exclude(path: Path):
        return (
            path.name in BackupManager.ignore_names
            or (path / ".git").exists()
            or path.is_symlink()
            or (path.is_file() and xattr.xattr(path).list())
            or path.stat().st_size > 50 * 10 ** 6
            or path in BackupManager.ignore_paths
        )

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
    def save_timestamps():
        if BackupManager.timestamps is None:
            BackupManager.get_paths()
        Path.timestamps.save(BackupManager.timestamps)

    @staticmethod
    def check_browser(command):
        config_folder = Path.home / "snap" / "chromium" / "common" / "chromium" / "Default"
        local = Path.home / ".config" / "browser"
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

    @staticmethod
    def subcheck(custom_filters=[], command=None):
        syncs = Path.syncs.load()

        for local, remote_info in syncs.items():
            for remote, ignore_patterns in remote_info.items():
                filters = parser.make_filters(
                    excludes=ignore_patterns, recursive=True, include_others=not custom_filters
                )
                if custom_filters:
                    filters += custom_filters

                function = Backup.get_function(command)
                function(local, remote, filters=filters)
