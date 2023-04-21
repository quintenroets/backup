import cli

from .path import Path


def check_setup():
    if not Path.config.exists():
        download_config_file(Path.config)
        cli.install("rclone")


def download_config_file(path: Path):
    file_id = "13f7p1nTJ3mPhLxvMMmCBLuwYpMmsayvM"
    url = f"https://docs.google.com/uc?export=download&id={file_id}"
    path.create_parent()
    cli.get("wget --no-check-certificate", url, "-O", path)
