import cli

from . import setup
from .changes import Changes
from .path import Path


class Backup:
    def __init__(self, local=None, remote=None):
        self.local = local or Path.HOME
        self.remote = remote or Path.remote
        # remote mappings defined in Path.config

    def upload(self, *filters, **kwargs):
        return Backup.copy(self.local, self.remote, filters=filters, **kwargs)

    def download(self, *filters, **kwargs):
        return Backup.copy(self.remote, self.local, filters=filters, **kwargs)

    @staticmethod
    def copy(
        source,
        dest,
        filters=None,
        overwrite_newer=True,
        delete_missing=False,
        quiet=True,
        **kwargs,
    ):
        action = ("sync", "--create-empty-src-dirs") if delete_missing else ("copy",)
        return Backup.run(
            *action,
            source,
            dest,
            filters=filters,
            overwrite_newer=overwrite_newer,
            quiet=quiet,
            progress=not quiet,
            show=not quiet,
            **kwargs,
        )

    @staticmethod
    def compare(local, remote, filters=None, show=False, **kwargs) -> Changes:
        options = {
            "combined": "-",  # for every file: report +/-/*/=
            "log-file": "/dev/null",  # discard errors thrown when files are different
        }
        change_patterns = Backup.run(
            "check", options, local, remote, filters=filters, show=show, **kwargs
        )
        if not show:
            change_patterns = [c for c in change_patterns if not c.startswith("=")]

        changes = Changes.from_patterns(change_patterns)
        return changes

    @staticmethod
    def run(
        *args,
        filters=None,
        show=True,
        overwrite_newer=False,
        exclude_git=True,
        **kwargs,
    ):
        setup.check_setup()
        with Path.tempfile() as filters_path:
            filters_path.lines = Backup.parse_filters(filters or ["+ **"])

            options = {
                "skip-links": None,
                "retries": "5",
                "retries-sleep": "30s",
                "order-by": "size,desc",  # send largest files first
                "filter-from": filters_path,
            }
            if not exclude_git:
                options.pop("exclude-if-present")

            if not overwrite_newer:
                options["update"] = None  # don't overwrite newer files

            for k, v in kwargs.items():
                if v:
                    options[k] = None if v is True else v

            args = ("rclone", options, *args)
            if show and args and args[0] == "check":
                clean_output_postprocessing = " | ".join(
                    (
                        "",
                        "tee /dev/stdout",
                        "tqdm --desc='Checking changes' --unit=files",
                        "grep -v =",
                    )
                )
                cli.run(*args, clean_output_postprocessing, shell=True)
            elif show:
                cli.run(*args)
            else:
                return cli.lines(*args, check=False)

    @staticmethod
    def parse_filters(filters):
        if filters and (isinstance(filters[0], list) or isinstance(filters[0], tuple)):
            filters = filters[0]
        filters = [f if f[0] in "+-" else f"+ {f}" for f in filters] + ["- **"]
        return filters
