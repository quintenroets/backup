from datetime import datetime

from libs.cli import Cli
from libs.output_copy import Output

from .path import Path


class Backup:
    def __init__(self, local=None, remote=None):
        self.local = local or Path.HOME
        self.remote = remote or Path.remote
        # remote mappings defined in .config/rclone/rclone.conf
        
    def upload(self, *filters, **kwargs):
        return Backup.copy(self.local, self.remote, filters=filters, **kwargs)
        
    def download(self, *filters, **kwargs):
        return Backup.copy(self.remote, self.local, filters=filters, **kwargs)
    
    @staticmethod
    def copy(source, dest, filters=[], overwrite_newer=True, delete_missing=False, quiet=True):
        action = "sync --create-empty-src-dirs" if delete_missing else "copy"
        command = f'{action} "{source}" "{dest}"'
        return Backup.run(
            command, filters, update=not overwrite_newer, quiet=quiet, progress=not quiet
            )

    @staticmethod
    def compare(local, remote, filters=["+ **"]):
        command = (
            "check --combined -"                    # for every file: report +/-/*/=
             " --log-file /dev/null"                # command throws errors if not match: discard error messages
             f" \"{local}\" \"{remote}\""           # compare folder with remote
             " | grep --color=never '^*\|^-\|^+'"   # only show changed items in stdout
             " || :"                                # command throws errors if not match: catch error code
             )
        
        out = Backup.run(command, filters, show=False)
        changes = [line for line in out.split("\n") if line]
        return changes
    
    @staticmethod
    def run(command, filters, show=True, **kwargs):
        filters_path = Backup.set_filters(filters)
        options = {
            "skip-links": "",
            "copy-links": "",
            
            "retries": "5",
            "retries-sleep": "30s",
            
            "order-by": "size,desc", # send largest files first
            # "fast-list": "", bad option: makes super slow
            
            "exclude-if-present": ".gitignore",
            "filter-from": f"'{filters_path}'",
            }
        
        if kwargs.get("overwrite_newer", False) == False:
            options["update"] = "" # dont overwrite newer files
        
        for k, v in kwargs.items():
            if v != False:
                options[k] = v if v != True else ""
                
        command_options= " ".join([f"--{k} {v}" for k, v in options.items()])
        command = f"rclone {command_options} {command}"
        try:
            return Cli.run(command) if show else Cli.get(command)
        finally:
            # catch interruptions
            filters_path.unlink()

    @staticmethod
    def set_filters(filters):
        filename = str(datetime.now()) # allow parallel runs without filter file conflicts
        Path.filters.mkdir(parents=True, exist_ok=True)
        path = (Path.filters / filename).with_suffix(".txt")
        
        filters = Backup.parse_filters(filters)
        path.write_text(filters)
        return path
        
    @staticmethod
    def parse_filters(filters):
        if filters and (isinstance(filters[0], list) or isinstance(filters[0], tuple)):
            filters = filters[0]
        filters = [f if f[0] in "+-" else f"+ {f}" for f in filters] + ["- **"]
        filters = "\n".join(filters)
        return filters
