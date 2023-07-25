import sys
from datetime import datetime, timezone

import cli
from rich import pretty

from . import custom_checker, parser, profilemanager
from .backup import Backup
from .changes import Change, Changes
from .path import Path


class BackupManager:
    updated = False
    ignore_names = Path.ignore_names.yaml
    ignore_patterns = Path.ignore_patterns.yaml
    exclude_zip = Path.exclude_zip.yaml
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
    def pull(cls, sub_check: bool):
        cls.sync_remote(sub_check)
        filters = cls.get_compared_filters(reverse=True)
        if filters:
            kwargs = {"delete_missing": True, "filters": filters}
            Backup.copy(
                Path.remote, Path.HOME, overwrite_newer=True, quiet=False, **kwargs
            )
            Backup.copy(Path.HOME, Path.backup_cache, **kwargs)
            cls.after_pull()

    @classmethod
    def after_pull(cls):
        profilemanager.reload()
        from . import exporter

        exporter.export_changes()

    @classmethod
    def sync_remote(cls, sub_check: bool):
        cls.check_cache_existence()
        sub_path = Path.cwd().relative_to(Path.HOME) if sub_check else ""
        present = set({})

        def extract_tuple(date: datetime):
            # drive only remote minute precision and month range
            return date.month, date.day, date.hour, date.minute

        def are_equal(date1: datetime, date2: datetime):
            return extract_tuple(date1) == extract_tuple(date2)

        # set cache to remote mod time
        for path_str, date in cls.get_remote_info(sub_path):
            cache_path = Path.backup_cache / sub_path / path_str
            cache_date = datetime.fromtimestamp(cache_path.mtime)
            cache_date = cache_date.astimezone(timezone.utc)

            if not are_equal(cache_date, date) or not cache_path.exists():
                mtime = cache_path.mtime + 1
                original_path = Path.HOME / cache_path.relative_to(Path.backup_cache)
                cache_path.text = "" if original_path.size else " "
                cache_path.touch(mtime=mtime)
            present.add(cache_path)

        def is_deleted(p: Path):
            return p.is_file() and p not in present

        sub_cache = Path.backup_cache / sub_path
        for path in sub_cache.find(is_deleted, recurse_on_match=True):
            # delete cache items not in remote
            path.unlink()

    @classmethod
    def get_remote_info(cls, sub_path):
        options = ("--all", "--modtime", "--noreport", "--full-path")
        command = "rclone tree"
        args = (command, options, Path.remote / sub_path)
        rclone_command = cli.prepare_args(args, command=True)[0]
        remove_color_command = r"sed 's/\x1B\[[0-9;]*[JKmsu]//g'"
        command = f"{rclone_command} | {remove_color_command}"
        with cli.status("Getting remote info"):
            lines = cli.lines(command, shell=True)

        for line in lines:
            if "[" in line:
                date_str, path_str = line.split("[")[1].split("]  /")
                date = datetime.strptime(date_str, "%b %d %H:%M")
                yield path_str, date

    @classmethod
    def get_compared_filters(cls, reverse=False):
        changes: Changes = cls.status(reverse=reverse)
        if changes:
            changes = cls.remove_excludes(changes)
        if changes:
            interactive = sys.stdin.isatty()
            if interactive:
                cli.console.clear()
                cli.console.rule("Drive")
                changes.print()
                cls.updated = True
                if not cli.confirm("Pull?" if reverse else "Push?", default=True):
                    changes.changes = []

        return changes.get_push_filters()

    @classmethod
    def remove_excludes(cls, changes: Changes) -> Changes:
        config = load_path_config()
        include_paths = [config_path for config_path, include in config if include]

        def is_include(change: Change):
            return any([change.path.is_relative_to(path) for path in include_paths])

        changes = [change for change in changes if is_include(change)]
        return Changes(changes)

    @classmethod
    def status(cls, reverse=False):
        profilemanager.save_active()
        cls.check_cache_existence()
        filters = cls.get_filters()
        src = Path.HOME
        dst = Path.backup_cache
        if reverse:
            src, dst = dst, src

        changes = Backup.compare(src, dst, filters=filters) if filters else Changes([])
        filters_without_change = cls.get_filters_without_change(filters, changes)
        if filters_without_change:
            # adapt modified times to avoid checking again in future
            Backup.copy(src, dst, filters=filters_without_change)

        return changes

    @classmethod
    def get_filters_without_change(cls, filters, changes):
        filters = cls.generate_filters_without_change(filters, changes)
        return list(filters)

    @classmethod
    def generate_filters_without_change(cls, filters, changes):
        changed_path_strings = [str(c.path) for c in changes]
        for pattern in filters:
            if pattern:
                pattern_path = pattern[3:]
                if pattern_path not in changed_path_strings:
                    yield pattern

    @classmethod
    def get_filters(cls):
        cls.visited = set({})
        paths = load_path_config()
        items = set({})

        def check_item(item):
            pattern = item.relative_to(Path.HOME)
            mirror = Path.backup_cache / pattern
            # zip_changed to notify file deletion from zip export
            if item.mtime != mirror.mtime and not item.tag:
                # check for tag here because we do not want to exclude tags recursively
                items.add(pattern)

        for path, include in paths:
            path = Path.HOME / path
            if include:
                for item in path.find(exclude=cls.exclude):
                    if item.is_file():
                        check_item(item)
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
            for volatile in parser.parse_paths_comb(Path.paths_volatile.yaml, {})
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


def subcheck(custom_filters=None, command=None):
    if custom_filters is None:
        custom_filters = []
    command = command or "status"
    syncs = Path.syncs.yaml
    ignore_names = Path.ignore_names.yaml
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
    if not Path.paths.exists():
        download_filter = f"/{Path.paths.relative_to(Path.HOME)}/**"
        Backup().download(download_filter)

    return parser.parse_paths_comb(Path.paths_include.yaml, Path.paths_exclude.yaml)
