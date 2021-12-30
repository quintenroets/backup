import xattr
import sys
from libs.cli import Cli
from libs import climessage
from libs.output_copy import Output
from libs.tagmanager import TagManager
from libs.threading import Thread

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
        for path in Path.HOME.glob(pattern)
    }
    visited = set({})
    
    @staticmethod
    def status():
        if not Path.backup_cache.exists():
            Cli.run(f"sudo mkdir {Path.backup_cache}", f"sudo chmod -R $(whoami):$(whoami) {Path.backup_cache}")
        filters = BackupManager.get_filters()
        return Backup.compare(Path.HOME, Path.backup_cache, filters=filters)
    
    @staticmethod
    def push():
        title = "Drive"
        print(title + "\n" + "=" * (len(title) + 2))
        changes = BackupManager.status()
        if changes:
            BackupManager.process_changes(changes)
        elif sys.stdin.isatty():
            input("\nEveryting clean.\nPress enter to exit")
            
    @staticmethod
    def process_changes(changes):
        interactive = sys.stdin.isatty()
        do_push = not interactive or climessage.ask("\nPush?")
        if do_push:
            Thread(BackupManager.start_push, changes).start()
            
    @staticmethod
    def start_push(changes):
        filters = [f"+ /{c[2:]}" for c in changes]
        Backup.copy(Path.HOME, Path.remote, filters=filters, quiet=False, delete_missing=True)
        Backup.copy(Path.HOME, Path.backup_cache, filters=filters, delete_missing=True)
        
    @staticmethod
    def pull():
        first_time = not Path.backup_cache.exists()
        filters = BackupManager.get_filters() if not first_time else "+ **"
        Backup.copy(Path.backup_cache, Path.HOME, filters=filters, overwrite_newer=True, delete_missing=not first_time)
        if first_time:
            Backup.copy(Path.HOME, Path.backup_cache, filters=BackupManager.get_filters(), delete_missing=True)
        ProfileManager.reload()
        
    @staticmethod
    def get_filters():
        BackupManager.visited = set({})
        paths = BackupManager.load_path_config()
        items = set({})
        for (path, include) in paths:
            path = Path.HOME / path
            if include:
                for item in path.find(exclude=BackupManager.exclude):
                    if item.is_file():
                        pattern = item.relative_to(Path.HOME)
                        mirror = Path.backup_cache / pattern
                        if not mirror.exists() or item.stat().st_mtime != mirror.stat().st_mtime:
                            if not xattr.xattr(item).list():
                                items.add(pattern)
            BackupManager.visited.add(path)
        
        def match(p):
            if p.is_file():
                mirror = Path.HOME / p.relative_to(Path.backup_cache)
                try:
                    match = p.stat().st_mtime != mirror.stat().st_mtime
                except FileNotFoundError:
                    match = True
                return match
            
        new_items = list(Path.backup_cache.find(match, recurse_on_match=True))
        for it in new_items:
            items.add(it.relative_to(Path.backup_cache))
        return parser.make_filters(includes=items)

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
            or path in BackupManager.visited
            or path.name in BackupManager.ignore_names
            or (path / ".git").exists()
            or path.is_symlink()
            or (path.stat().st_size > 50 * 10 ** 6 and path.suffix != ".zip")
        )

    @staticmethod
    def check_browser(command):
        local = Path.HOME

        config_folder = local / "snap" / "chromium" / "common" / "chromium" / "Default"
        config_save_file = local / ".config" / "browser" / "config.zip"
        filters = parser.make_filters(includes=[config_save_file.relative_to(local)])

        if command == "push":
            ignores = ["Cache", "Code Cache", "Application Cache", "CacheStorage", "ScriptCache", "GPUCache"]
            flags = "".join([
                f"-x'*/{i}/*' " for i in ignores
            ])
            command = (
                f"zip -r -q -u '{config_save_file}' {flags} '{config_folder.name}'" # only compress changes
                if config_save_file.exists()
                else f"zip -r -q - {flags} '{config_folder.name}' | tqdm --bytes --desc='Compressing' > '{config_save_file}'"
                )
            # make sure that all zipped files have the same root
            Cli.run(command, pwd=config_folder.parent)
            Backup().upload(filters)

        elif command == "pull":
            Backup().download(filters)
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
