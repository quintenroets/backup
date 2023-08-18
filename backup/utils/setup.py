import cli

from .path import Path


def check_setup(install=True):
    path = Path.rclone_config
    if not path.exists():
        download_config_file(path)
        if install:
            command = "sudo -v ; curl https://rclone.org/install.sh | sudo bash"
            cli.run(command, shell=True)


def download_config_file(path: Path):
    file_id = "13f7p1nTJ3mPhLxvMMmCBLuwYpMmsayvM"
    url = f"https://docs.google.com/uc?export=download&id={file_id}"
    path.create_parent()
    cli.get("wget --no-check-certificate", url, "-O", path)
