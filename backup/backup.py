from libs.cli import Cli
from .filemanager import FileManager

class Backup:
    # remote root defined in .config/rclone/rclone.conf backup -> Google Drive: Autobackup

    @staticmethod
    def upload(folder, remote, filters=[]):
        remote = f"backup:{remote}"
        Backup.sync(folder, remote, filters)

    @staticmethod
    def download(folder, remote, filters=[], delete_missing=False):
        remote = f"backup:{remote}"
        Backup.sync(remote, folder, filters, delete_missing)

    @staticmethod
    def compare(folder, remote, filters=[]):
        remote = f"backup:{remote}"
        command = f"check --combined - --log-file /dev/null \"{folder}\" \"{remote}\" | grep --color=never '^*\|^-\|^+'"
        return Backup.run(command, filters)

    @staticmethod
    def sync(source, dest, filters=[], delete_missing=True, quiet=False):
        command = "sync --create-empty-src-dirs" if delete_missing else "copy"
        flag = "q" if quiet else "P"
        command = f"-{flag} {command} \"{source}\" \"{dest}\""
        Backup.run(command, filters)

    @staticmethod
    def run(command, filters=[]):
        filters_path = FileManager.set_filters(filters + ["- **"])
        command = f"rclone -L --skip-links --filter-from '{filters_path}' {command}"
        try:
            Cli.run(command, check=False) # rclone throws error if nothing changed
        finally:
            # catch interruptions
            filters_path.unlink()