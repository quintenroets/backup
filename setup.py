from setuptools import setup, find_packages
from pathlib import Path
import os
import shutil
import subprocess

from backup.backup import Backup
from backup.filemanager import FileManager

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
    description='',
    name=NAME,
    version='1.0',
    packages=find_packages(),
    install_requires=read("requirements.txt"),
    entry_points={
        "console_scripts": [
            "drive = backup.starter:main",
            "drivesync = backup.syncer:main",
            "watcher = backup.watcher:main"
        ]
    },
)

filename = "rclone.conf"
src = Path(__file__).parent / "assets" / filename
dst = Path.home() / ".config" / "rclone" / filename

# install newest version of rclone
subprocess.run(
    "sudo apt install -y curl; curl https://rclone.org/install.sh | sudo bash", 
    shell=True
    )

if not os.path.exists(src):
    subprocess.run(f"yes | gpg {src}.gpg", shell=True) # decrypt credentials

os.makedirs(os.path.dirname(dst), exist_ok=True)
shutil.copyfile(src, dst)

# download path assets before other drive sync can happen
Backup.download(FileManager.root, "Config/.config/scripts/backup", filters=["+ **"])
# download core config files
Backup.download(Path.home(), "Config", filters=["+ *"])
