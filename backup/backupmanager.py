import sys
from datetime import datetime

import cli
from rich import pretty

from . import custom_checker, parser, profilemanager
from .backup import Backup
from .path import Path


class BackupManager:
    updated = False
    ignore_names = Path.ignore_names.load()
    ignore_patterns = Path.ignore_patterns.load()
    exclude_zip = Path.exclude_zip.load()
    ignore_paths = {
        path for pattern in ignore_patterns for path in Path.HOME.glob(pattern)
    }
    visited = set({})
    export_changes = []

    @classmethod
    def push(cls):
        filters = cls.get_compared_filters()
        if filters:
            Backup().upload(filters, delete_missing=True, quiet=False)
            Backup.copy(
                Path.HOME, Path.backup_cache, filters=filters, delete_missing=True
            )

    @classmethod
    def pull(cls, option=None):
        if option:
            cls.sync_remote(option)
        filters = cls.get_compared_filters(reverse=True)
        if filters:
            src = Path.remote if option else Path.backup_cache
            Backup.copy(
                src,
                Path.HOME,
                filters=filters,
                overwrite_newer=True,
                delete_missing=True,
                quiet=not option,
            )
            if option:
                Backup.copy(
                    Path.HOME, Path.backup_cache, filters=filters, delete_missing=True
                )
            cls.after_pull(filters)

    @classmethod
    def after_pull(cls, filters=None):
        if filters is None:
            filters = [f"   {p}" for p in Path.exports.iterdir()]
        for filter_name in filters:
            if filter_name.endswith(".zip"):
                path = Path(filter_name[3:])
                src = Path.HOME / path
                dst = (Path.HOME / "/".join(path.name.split("_"))).with_suffix("")
                dst.rmtree(missing_ok=True)
                dst.parent.mkdir(parents=True, exist_ok=True)
                cli.get("unzip", "-o", src, "-d", dst)
        profilemanager.reload()

    @classmethod
    def sync_remote(cls, option):
        cls.check_cache_existence()
        if option == ".":
            option = ""  # ls all files
        else:
            option = Path(option).relative_to(Path.HOME)

        config = load_path_config()
        drive_includes = [
            path
            for path, include in config
            if include
            and path.is_relative_to("Documents/Drive")
            and path != Path("Documents/Drive")
        ]
        drive_include_filters = [f"/{path}/**" for path in drive_includes]
        with Path.tempfile() as tmp, Path.tempfile() as filters_path:
            filters_path.lines = Backup.parse_filters(
                drive_include_filters + ["- /Documents/Drive/**"]
            )[:-1]
            cli.run(
                f"rclone lsl --filter-from {filters_path} {Path.remote / option}"
                f" | tee {tmp} |"
                f' tqdm --desc="Reading Remote" --null --unit=files',
                shell=True,
            )
            lines = tmp.lines

        present = set({})

        # set cache to remote mod time
        for line in lines:
            size, date, time, *names = line.strip().split(" ")
            mtime = int(
                datetime.strptime(
                    f"{date} {time[:-3]}", "%Y-%m-%d %H:%M:%S.%f"
                ).timestamp()
            )
            cache_path = Path.backup_cache / option / " ".join(names)
            if mtime > cache_path.mtime:
                cache_path.touch(mtime=mtime)
                cache_path.text = ""
            present.add(cache_path)

        # delete cache items not in remote
        def is_deleted(p: Path):
            deleted = p.is_file() and p not in present
            if deleted and p.is_relative_to(Path.backup_cache / "Documents" / "Drive"):
                deleted = any(p.is_relative_to(parent) for parent in drive_includes)

            return deleted

        for path in (Path.backup_cache / option).find(
            is_deleted, recurse_on_match=True
        ):
            path.unlink()

    @classmethod
    def export_path(cls, path):
        root = Path.HOME / path
        cls.visited.add(root)
        dest = (Path.exports / "_".join(path.parts)).with_suffix(".zip")

        changed = False
        for item in root.find():
            if item.is_file() and item.mtime > dest.mtime and not cls.exclude(item):
                changed = True
                cls.export_changes.append(
                    f'{"*" if dest.mtime else "+"} {item.relative_to(Path.HOME)}'
                )

        if changed:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.unlink(missing_ok=True)
            cli.run(f'zip -r -q -o "{dest}" *', cwd=root, shell=True)

        return dest

    @classmethod
    def get_compared_filters(cls, reverse=False):
        changes = cls.status(reverse=reverse)
        if changes:
            changes = cls.remove_excludes(changes)
        if changes:
            interactive = sys.stdin.isatty()
            if interactive:
                cli.console.clear()
                cli.console.rule("Drive")
                message = "\n".join([*cls.export_changes, *changes, ""])
                print(message)
                cls.updated = True
                if not cli.confirm("Pull?" if reverse else "Push?", default=True):
                    changes = []

        filters = [f"+ /{c[2:]}" for c in changes]
        return filters

    @classmethod
    def remove_excludes(cls, changes):
        filtered_changes = []
        config = load_path_config()

        for change in changes:
            path = Path(change[2:])
            for config_path, include in config:
                if path.is_relative_to(config_path):
                    if include:
                        filtered_changes.append(change)
                    break

        return filtered_changes

    @classmethod
    def status(cls, reverse=False):
        profilemanager.save_active()
        cls.check_cache_existence()
        filters = cls.get_filters()

        src, dst = (
            (Path.HOME, Path.backup_cache)
            if not reverse
            else (Path.backup_cache, Path.HOME)
        )
        status = Backup.compare(src, dst, filters=filters) if filters else []
        changed_paths = [s[2:] for s in status]  # cut away +/* and space

        no_changes_filters = [
            f for f in filters if f and f[3:] not in changed_paths
        ]  # cut away +/*, space, slash
        if no_changes_filters:
            # adapt modified times to avoid checking again in future
            Backup.copy(src, dst, filters=no_changes_filters)

        return status

    @classmethod
    def get_filters(cls):
        cls.visited = set({})
        paths = load_path_config()
        items = set({})
        for (path, include) in paths:
            path_full = Path.HOME / path
            if path_full.is_dir() and include:
                if (
                    False  # path_full.is_relative_to(Path.drive) # disable zipping in drive folder
                    or (
                        not path_full.is_relative_to(Path.docs)
                        and not path_full.is_relative_to(Path.assets.parent)
                    )
                    and not path_full.is_relative_to(Path.browser_config)
                    and str(path) not in cls.exclude_zip
                ):
                    path_full = cls.export_path(path)
            path = path_full

            if include:
                for item in path.find(exclude=cls.exclude):
                    if item.is_file():
                        pattern = item.relative_to(Path.HOME)
                        mirror = Path.backup_cache / pattern
                        # zip_changed to notify file deletion from zip export
                        zip_changed = item.suffix == ".zip" and item.size != mirror.size
                        if (item.mtime != mirror.mtime or zip_changed) and not item.tag:
                            # check for tag here because we do not want to exclude tags recusively
                            items.add(pattern)
            cls.visited.add(path)
        volatile_items = cls.load_volatile()

        def match(p: Path):
            if p.is_file():
                relative = p.relative_to(Path.backup_cache)
                mirror = Path.HOME / relative
                return p.mtime != mirror.mtime and relative not in volatile_items

        new_items = Path.backup_cache.find(match, recurse_on_match=True)
        for it in new_items:
            items.add(it.relative_to(Path.backup_cache))

        items = custom_checker.reduce(items)
        return parser.make_filters(includes=items)

    @classmethod
    def check_cache_existence(cls):
        # first time run
        if not Path.backup_cache.exists():
            cli.sh(
                f"mkdir {Path.backup_cache}",
                f"chown -R $(whoami):$(whoami) {Path.backup_cache}",
                root=True,
            )
            Backup.copy(Path.remote, Path.backup_cache, filters=["+ **"], quiet=False)

    @classmethod
    def load_volatile(cls):
        return tuple(
            volatile[0]
            for volatile in parser.parse_paths_comb(Path.paths_volatile.content, {})
        )

    @classmethod
    def exclude(cls, path: Path):
        return (
            path in cls.ignore_paths
            or path in cls.visited
            or path.name in cls.ignore_names
            or (path / ".git").exists()
            or path.is_symlink()
            or (path.stat().st_size > 50 * 10**6 and path.suffix != ".zip")
            or path.suffix == ".part"
        )

    @classmethod
    def check_browser(cls, command):
        local = Path.HOME

        config_folder = local / "snap" / "chromium" / "common" / "chromium" / "Default"
        config_save_file = Path.browser_config / "config.zip"
        filters = parser.make_filters(includes=[config_save_file.relative_to(local)])

        if command == "push":
            ignores = [
                "Cache",
                "Code Cache",
                "Application Cache",
                "CacheStorage",
                "ScriptCache",
                "GPUCache",
            ]
            flags = "".join([f'-x"*/{i}/*" ' for i in ignores])
            command = f'zip -r -q - {flags} "{config_folder.name}" | tqdm --bytes --desc=Compressing > "{config_save_file}"'
            # make sure that all zipped files have the same root
            cli.run(command, cwd=config_folder.parent, shell=True)
            Backup().upload(filters, quiet=False)

        elif command == "pull":
            Backup().download(filters, quiet=False)
            config_folder.mkdir(parents=True, exist_ok=True)
            cli.get("unzip", "-o", config_save_file, "-d", config_folder.parent)
        else:
            print("Choose pull or push")


def subcheck(custom_filters=None, command=None):
    if custom_filters is None:
        custom_filters = []
    command = command or "status"
    syncs = Path.syncs.load()
    ignore_names = Path.ignore_names.load()
    ignore_name_filters = [f"- **{n}**" for n in ignore_names]

    for local, remote_info in syncs.items():
        for remote, ignore_patterns in remote_info.items():
            local = Path.HOME / local
            remote = "backup:" + remote
            filters = ignore_name_filters + parser.make_filters(
                excludes=ignore_patterns,
                recursive=True,
                include_others=not custom_filters,
                root=local,
            )
            if custom_filters:
                filters += custom_filters

            if command == "status":
                changes = Backup.compare(
                    local, remote, filters=filters, exclude_git=False
                )
                pretty.pprint(changes)
            elif command == "push":
                Backup().copy(
                    local,
                    remote,
                    filters=filters,
                    delete_missing=True,
                    exclude_git=False,
                    quiet=False,
                )


def load_path_config():
    return parser.parse_paths_comb(
        Path.paths_include.content, Path.paths_exclude.content
    )
