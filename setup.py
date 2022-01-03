from setuptools import setup, find_packages

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
    setup_requires=read("setup_requirements.txt"),
    install_requires=read("requirements.txt"),
    entry_points={
        "console_scripts": [
            "drive = backup.main:main",
            "drivesync = backup.syncer:main",
            "watcher = backup.watcher:main",
        ]
    },
)
        
from libs.cli import Cli
from path import Path
from backup.backup import Backup

installed = Cli.get("which rclone", check=False)
if not installed:
    Cli.install("curl")
    # install newest version of rclone this way
    Cli.run("curl https://rclone.org/install.sh | sudo bash")

filename = "rclone.conf"
src = Path(__file__).parent / "assets" / filename
dst = Path.HOME / ".config" / "rclone" / filename


if not dst.exists():
    if not src.exists():
        Cli.run(f"yes | gpg {src}.gpg") # decrypt credentials
        
    dst.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dst)
    
    config_paths = (Path.assets / NAME / "paths").relative_to(Path.HOME)
    Backup().download(f"/{config_paths}/**")
