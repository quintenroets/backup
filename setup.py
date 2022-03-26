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

import cli  # isort:skip
from plib import Path  # isort:skip
from backup.backup import Backup  # isort:skip

installed = cli.get("which rclone", check=False)
if not installed:
    cli.install("curl")
    # install newest version of rclone this way
    cli.run("curl https://rclone.org/install.sh | sudo bash", shell=True)

filename = "rclone.conf"
src = Path(__file__).parent / "assets" / filename
dst = Path.HOME / ".config" / "rclone" / filename


if not dst.exists():
    if not src.exists():
        cli.run("gpg {src}.gpg", input="yes")  # decrypt credentials

    src.rename(dst)
    config_paths = (Path.assets / NAME / "paths").relative_to(Path.HOME)
    Backup().download(f"/{config_paths}/**")
