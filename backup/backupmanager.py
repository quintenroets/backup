import cli
import sys
from datetime import datetime

from libs.threading import Thread

from .backup import Backup
from .path import Path
from .profilemanager import ProfileManager
from . import parser


class BackupManager:
    updated = False
    ignore_names = Path.ignore_names.load()
    ignore_patterns = Path.ignore_patterns.load()
    ignore_paths = {
        path
        for pattern in ignore_patterns
        for path in Path.HOME.glob(pattern)
    }
    visited = set({})
    
    @staticmethod
    def push():
        filters = BackupManager.get_compared_filters()
        if filters:
            Backup().upload(filters, delete_missing=True, quiet=False)
            Backup.copy(Path.HOME, Path.backup_cache, filters=filters, delete_missing=True)
        
    @staticmethod
    def pull(option=None):
        if option:
            BackupManager.sync_remote(option)
        filters = BackupManager.get_compared_filters(reverse=True)
        if filters:
            src = Path.remote if option else Path.backup_cache
            Backup.copy(src, Path.HOME, filters=filters, overwrite_newer=True, delete_missing=True, quiet=not option)
            if option:
                Backup.copy(Path.HOME, Path.backup_cache, filters=filters, delete_missing=True)
            BackupManager.after_pull(filters)
            
    @staticmethod
    def after_pull(filters=None):
        if filters is None:
            filters = [f"   {p}" for p in Path.exports.iterdir()]
        for filter_name in filters:
            if filter_name.endswith(".zip"):
                path = Path(filter_name[3:])
                src = Path.HOME / path
                dst = (Path.HOME / "/".join(path.name.split("_"))).with_suffix("")
                dst.rmtree(missing_ok=True)
                dst.parent.mkdir(parents=True, exist_ok=True)
                cli.get(f"unzip -o '{src}' -d '{dst}'")
        ProfileManager.reload()
        
    @staticmethod
    def sync_remote(option):
        BackupManager.check_cache_existence()
        if option == ".":
            option = "" # ls all files
        else:
            option = Path(option).relative_to(Path.HOME)
        
        with cli.spinner("Reading remote"):
            lines = cli.get(f"rclone lsl {Path.remote}/{option}").split("\n")
        changes = []
        present = set({})
        
        # set cache to remote mod time
        for line in lines:
            size, date, time, *names = line.strip().split(" ")
            path = Path.HOME / option / " ".join(names)
            mtime = int(datetime.strptime(f"{date} {time[:-3]}", '%Y-%m-%d %H:%M:%S.%f').timestamp())
            cache_path = Path.backup_cache / option / ' '.join(names)
            if mtime > cache_path.mtime:
                cache_path.touch(mtime=mtime)
            present.add(cache_path)
        
        # delete cache items not in remote
        def is_deleted(p):
            return p.is_file() and p not in present
            
        for deleted in (Path.backup_cache / option).find(is_deleted, recurse_on_match=True):
            deleted.unlink()
                
    @staticmethod
    def export_path(path):
        root = Path.HOME / path
        BackupManager.visited.add(root)
        dest = (Path.exports / "_".join(path.parts)).with_suffix(".zip")
        
        changed = False
        for item in root.find():
            if item.is_file() and item.mtime > dest.mtime and not BackupManager.exclude(item):
                changed = True
                print(f"{'*' if dest.mtime else '+'} {item.relative_to(Path.HOME)}")
        
        if changed:
            dest.parent.mkdir(parents=True, exist_ok=True)
            cli.run(f'zip -r -q -o "{dest}" *', cwd=root, shell=True)
                    
        return dest
    
    @staticmethod
    def get_compared_filters(reverse=False):
        changes = BackupManager.status(reverse=reverse)
        if changes:
            interactive = sys.stdin.isatty()
            if interactive:
                message = "\n".join(["", "Drive", "=" * 80, *changes, "", "Pull?" if reverse else "Push?"])
                BackupManager.updated = True
                if not cli.ask(message):
                    changes = []
                
        filters = [f"+ /{c[2:]}" for c in changes]
        return filters
    
    @staticmethod
    def status(reverse=False):
        ProfileManager.save_active()
        BackupManager.check_cache_existence()
        filters = BackupManager.get_filters()
        src, dst = (Path.HOME, Path.backup_cache) if not reverse else (Path.backup_cache, Path.HOME)
        status = Backup.compare(src, dst, filters=filters) if filters else []
        changed_paths = [s[2:] for s in status] # cut away +/* and space
        no_changes_filters = [f for f in filters if f and f[3:] not in changed_paths] # cut away +/*, space, slash
        if no_changes_filters:
            # adapt modified times to avoid checking again in future
            Backup.copy(src, dst, filters=no_changes_filters)
        
        return status
        
    @staticmethod
    def get_filters():
        BackupManager.visited = set({})
        paths = BackupManager.load_path_config()
        items = set({})
        for (path, include) in paths:
            path_full = Path.HOME / path
            if path_full.is_dir() and include:
                if path_full.is_relative_to(Path.docs / "Drive") or (not path_full.is_relative_to(Path.docs) and not path_full.is_relative_to(Path.assets.parent)):
                    if not path_full.is_relative_to(Path.HOME / ".config" / "browser"):
                        path_full = BackupManager.export_path(path)
            path = path_full
            
            
            if include:
                for item in path.find(exclude=BackupManager.exclude):
                    if item.is_file():
                        pattern = item.relative_to(Path.HOME)
                        mirror = Path.backup_cache / pattern
                        if item.mtime != mirror.mtime and not item.tag: 
                            # check for tag here because we do not want to exclude tags recusively
                            items.add(pattern)
            BackupManager.visited.add(path)

        def match(p):
            if p.is_file():
                mirror = Path.HOME / p.relative_to(Path.backup_cache)
                try:
                    match = p.mtime != mirror.mtime
                except FileNotFoundError:
                    match = True
                return match
            
        new_items = list(Path.backup_cache.find(match, recurse_on_match=True))
        for it in new_items:
            items.add(it.relative_to(Path.backup_cache))
        return parser.make_filters(includes=items)
    
    @staticmethod
    def check_cache_existence():
        # first time run
        if not Path.backup_cache.exists():
            cli.run(f"mkdir {Path.backup_cache}", f"chown -R $(whoami):$(whoami) {Path.backup_cache}", shell=True, root=True)
            Backup.copy(Path.remote, Path.backup_cache, filters=["+ **"], quiet=False)

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
            or path.suffix == ".part"
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
                if config_save_file.exists() and False # zip update is not a good idea
                else f"zip -r -q - {flags} '{config_folder.name}' | tqdm --bytes --desc='Compressing' > '{config_save_file}'"
                )
            # make sure that all zipped files have the same root
            cli.run(command, cwd=config_folder.parent)
            Backup().upload(filters, quiet=False)

        elif command == "pull":
            Backup().download(filters, quiet=False)
            config_folder.mkdir(parents=True, exist_ok=True)
            cli.get(f"unzip -o '{config_save_file}' -d '{config_folder.parent}'")
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
