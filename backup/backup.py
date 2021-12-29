from libs.cli import Cli
from libs.output_copy import Output
from .path import Path

from datetime import datetime

remote_root = "/home/autobackup/"
remote_root = "backup:"

class Backup:
    # remote root defined in .config/rclone/rclone.conf backup -> Google Drive: Autobackup

    @staticmethod
    def upload(folder, remote, filters=[]):
        remote = f"{remote_root}{remote}"
        Backup.sync(folder, remote, filters)

    @staticmethod
    def download(folder, remote, filters=[], delete_missing=False):
        remote = f"{remote_root}{remote}"
        Backup.sync(remote, folder, filters, delete_missing)

    @staticmethod
    def compare(folder, remote, filters=[]):
        total_option = ""
        # amount of checks known if only include filters
        if all([f.startswith("+") for f in filters]):
            folder = Path(folder)            
            files = [f for f in filters if (folder / f[3:]).is_file()]
            total_option = f"--total={len(files)}"
            
        remote = f"{remote_root}{remote}"
        title = "Checks"
        command = (
            "check --combined -"                        # for every file: report +/-/*/=
             " --log-file /dev/null"                    # command throws errors if not match: discard error messages
             f" \"{folder}\" \"{remote}\""              # compare folder with remote
             f" | tqdm  --desc={title} {total_option}"  # pipe all output to tqdm that displays number of checks
             #" | grep --color=never '^*\|^-\|^+'"      # only show changed items in stdout
             " || :"                                    # command throws errors if not match: catch error code
             )
        
        with Output() as out:
            Backup.run(command, filters)
        result = [line for line in str(out).split("\n") if line and f"{title}:" not in line] # filter tqdm output
        return result

    @staticmethod
    def sync(source, dest, filters=[], delete_missing=True, quiet=False):
        command = "sync --create-empty-src-dirs" if delete_missing else "copy"
        flag = "q" if quiet else "P"
        command = f"-{flag} {command} \"{source}\" \"{dest}\""
        Backup.run(command, filters)

    @staticmethod
    def run(command, filters=[]):
        filters_path = Backup.set_filters(filters + ["- **"])
        options = {
            "copy-links": "",
            "retries-sleep": "30s",
            "retries": "5",
            "log-file": "~/.config/scripts/backup/filters/log.out",
            "skip-links": "",
            "filter-from": f"'{filters_path}'"
            }
        options= " ".join([f"--{k} {v}" for k, v in options.items()])
        try:
            Cli.run(f"rclone {options} {command}")
        finally:
            # catch interruptions
            filters_path.unlink()

    @staticmethod
    def set_filters(filters):
        folder = Path.root / "filters"
        folder.mkdir(parents=True, exist_ok=True)

        # allow parallel runs without filter file conflicts
        path = (folder / str(datetime.now())).with_suffix(".txt")
        path.write_text(
            "\n".join(filters)
        )
        return path

    @staticmethod
    def get_function(command):
        functions_mapper = {
            "push": Backup.upload,
            "pull": Backup.download
        }
        function = functions_mapper.get(command, Backup.compare)
        return function
