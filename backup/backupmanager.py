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
        export_resume_changes()

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
                cache_path.touch(mtime=cache_path.mtime + 1)
                cache_path.text = ""
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

        src, dst = (
            (Path.HOME, Path.backup_cache)
            if not reverse
            else (Path.backup_cache, Path.HOME)
        )
        changes = Backup.compare(src, dst, filters=filters) if filters else Changes([])
        changed_path_strings = [str(c.path) for c in changes]

        def filter_path(filter_str: str):
            # cut away +/*, space, slash
            return filter_str[3:]

        def is_no_change_filter(filter_str: str):
            return filter_str and filter_path(filter_str) not in changed_path_strings

        no_changes_filters = [f for f in filters if is_no_change_filter(f)]
        if no_changes_filters:
            # adapt modified times to avoid checking again in future
            Backup.copy(src, dst, filters=no_changes_filters)

        return changes

    @classmethod
    def get_filters(cls):
        cls.visited = set({})
        paths = load_path_config()
        items = set({})

        def check_item(item):
            pattern = item.relative_to(Path.HOME)
            mirror = Path.backup_cache / pattern
            # zip_changed to notify file deletion from zip export
            zip_changed = item.suffix == ".zip" and item.size != mirror.size
            if (item.mtime != mirror.mtime or zip_changed) and not item.tag:
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

    @classmethod
    def check_browser(cls, command):
        local = Path.HOME

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
            command = (
                f'zip -r -q - {flags} "{Path.browser_config_folder.name}" | tqdm'
                f' --bytes --desc=Compressing > "{config_save_file}"'
            )
            # make sure that all zipped files have the same root
            cli.run(command, cwd=Path.browser_config_folder.parent, shell=True)
            Backup().upload(filters, quiet=False)

        elif command == "pull":
            Backup().download(filters, quiet=False)
            Path.browser_config_folder.mkdir(parents=True, exist_ok=True)
            cli.get(
                "unzip", "-o", config_save_file, "-d", Path.browser_config_folder.parent
            )
        else:
            print("Choose pull or push")


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


def export_resume_changes():
    resume_local_folder = Path.drive / "resume"
    resume_file = resume_local_folder / "Resume Quinten Roets.docx"
    exported_resume_file = resume_file.with_suffix(".pdf")
    if exported_resume_file.mtime < resume_file.mtime:
        remote_resume_file = Path.remote / exported_resume_file.relative_to(Path.HOME)
        cli.run(
            f"rclone --drive-export-formats pdf copy '{remote_resume_file}'"
            f" {resume_local_folder}"
        )
        exported_resume_file.mtime = resume_file.mtime
