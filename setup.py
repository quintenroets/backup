from setuptools import find_packages, setup

NAME = "backup"


def read(filename):
    try:
        with open(filename) as fp:
            content = fp.read().split("\n")
    except FileNotFoundError:
        content = []
    return content


setup(
    author="Quinten Roets",
    author_email="quinten.roets@gmail.com",
    description="",
    name=NAME,
    version="1.0",
    packages=find_packages(),
    setup_requires=read("setup_requirements.txt"),
    install_requires=read("requirements.txt"),
    entry_points={
        "console_scripts": [
            "drive = backup.main:main",
            "watcher = backup.watcher:main",
        ]
    },
)

import cli  # isort:skip # noqa: autoimport
from plib import Path  # isort:skip # noqa: autoimport
from backup.backup import Backup  # isort:skip # noqa: autoimport

installed = cli.get("which rclone", check=False)
if not installed:
    cli.install("curl")
    # install newest version of rclone this way
    cli.run("curl https://rclone.org/install.sh | sudo bash", shell=True)


def download_config_file(path):
    file_id = "13f7p1nTJ3mPhLxvMMmCBLuwYpMmsayvM"
    url = f"https://docs.google.com/uc?export=download&id={file_id}"
    cli.get("wget --no-check-certificate", url, "-O", path)


config_path = Path.HOME / ".config" / "rclone" / "rclone.conf"
if not config_path.exists():
    download_config_file(config_path)
