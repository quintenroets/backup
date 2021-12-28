import xattr

from libs.cli import Cli
from libs.output_copy import Output
from libs.tagmanager import TagManager

from .backup import Backup
from .path import Path
from .profilemanager import ProfileManager
from . import parser

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
        filters = BackupManager.get_pull_filters() if command == "pull" else BackupManager.get_filters()
        if filters:
            if command == "status":
                show_filters = sorted(["  " + f.replace("+ /", "") for f in filters[:10]])
                message = "\n".join(["Checking..", *show_filters, ""])
                print(message)

            return BackupManager.sync(command, filters, **kwargs)

    @staticmethod
    def sync(command, filters, src=Path.home, dst="Home"):
        kwargs = {"delete_missing": True} if command == "pull" else {}
        sync = Backup.get_function(command)
        if command == "status":
            with Output() as out:
                sync(src, dst, filters=filters, **kwargs)
        else:
            sync(src, dst, filters=filters, **kwargs)
            out = ""
            
        result = str(out)
        if command != "status" or not result:
            BackupManager.save_timestamps()
        if command =="pull":
            ProfileManager.reload()
        return result

    @staticmethod
    def get_filters():
        new_timestamps = BackupManager.calculate_timestamps()
        timestamps = Path.timestamps.load()
        paths = parser.calculate_difference(new_timestamps, timestamps)
        filters = parser.make_filters(includes=paths, recursive=False)
        return filters

    @staticmethod
    def calculate_timestamps():
        paths = BackupManager.load_path_config()
        items = []
        for (path, include) in paths:
            path = Path.home / path
            if include:
                for item in path.find(condition=None, exclude=BackupManager.exclude):
                    items.append(item)
            BackupManager.ignore_paths.add(path)

        BackupManager.timestamps = { # cache because needed later
            str(p.relative_to(Path.home)): int(p.stat().st_mtime) for p in items if p.exists()
        }
        return BackupManager.timestamps

    @staticmethod
    def get_pull_filters():
        paths = BackupManager.load_path_config()
        filters = []
        for (path, include) in paths:
            if include:
                for item in (Path.home / path).find(condition=BackupManager.exclude):
                    filters += parser.make_filters(excludes=[item.relative_to(Path.home)], recursive=True)
                filters += parser.make_filters(includes=[path, f"{path}/**"], recursive=False)
            else:
                BackupManager.ignore_paths.add(Path.home / path)
                filters += parser.make_filters(excludes=[path, f"{path}/**"], recursive=False)

        filters += parser.make_filters(excludes=BackupManager.ignore_patterns, recursive=False)
        return filters

    @staticmethod
    def load_path_config():
        return parser.parse_paths_comb(
            Path.paths_include.load(),
            Path.paths_exclude.load()
        )

    @staticmethod
    def exclude(path: Path):
        return (
            path in BackupManager.ignore_paths
            or path.name in BackupManager.ignore_names
            or (path / ".git").exists()
            or path.is_symlink()
            or (path.is_file() and xattr.xattr(path).list())
            or path.stat().st_size > 50 * 10 ** 6
        )

    @staticmethod
    def save_timestamps():
        if BackupManager.timestamps is None:
            BackupManager.calculate_timestamps()
        Path.timestamps.save(BackupManager.timestamps)

    @staticmethod
    def check_browser(command):
        local = Path.home
        remote = "Home"

        config_folder = local / "snap" / "chromium" / "common" / "chromium" / "Default"
        config_save_file = local / ".config" / "browser" / "config.zip"
        filters = parser.make_filters(includes=[config_save_file.relative_to(local)])

        if command == "push":
            ignores = ["Cache", "Code Cache", "Application Cache", "CacheStorage", "ScriptCache", "GPUCache"]
            flags = "".join([
                f"-x'*/{i}/*' " for i in ignores
            ])
            command = (
                f"zip -r -q -f '{config_save_file}' {flags} '{config_folder.name}'" # only compress changes
                if config_save_file.exists()
                else f"zip -r -q - {flags} '{config_folder.name}' | tqdm --bytes --desc='Compressing' > '{config_save_file}'"
                )
            # make sure that all zipped files have the same root
            Cli.run(command, pwd=config_folder.parent)
            Backup.upload(local, remote, filters=filters)

        elif command == "pull":
            Backup.download(local, remote, filters=filters)
            config_folder.mkdir(parents=True, exist_ok=True)
            Cli.get(f"unzip -o '{config_save_file}' -d '{config_folder.parent}'")
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
