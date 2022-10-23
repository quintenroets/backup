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

config_path = Path.HOME / ".config" / "rclone" / "rclone.conf"
if not config_path.exists():
    raise Exception("manually download encrypted rclone config file to ~/.config/rclone/rclone.conf")
backup_config_paths = (Path.assets / NAME / "paths").relative_to(Path.HOME)
Backup().download(f"/{backup_config_paths}/**")
