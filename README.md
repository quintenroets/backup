# Backup
[![PyPI version](https://badge.fury.io/py/backupmaster.svg)](https://badge.fury.io/py/backupmaster)
![PyPI downloads](https://img.shields.io/pypi/dm/backupmaster)
![Python version](https://img.shields.io/badge/python-3.10+-brightgreen)
![Operating system](https://img.shields.io/badge/os-linux-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)

Generic engine to back up important files across an entire disk to an [rclone](https://rclone.org) remote with change detection.
- Scales to a huge number of files
- Detailed configuration to maximize performance
- Perfect for files that are too volatile for a VCS like Git and too important to lose

## Usage
```python
import backup

config = {
    "source": "/home/user",
    "dest": "remote:backup",  # any rclone destination; a local path also works
    "syncs": [
        {"includes": [".ssh", ".config/git"], "excludes": ["*.log"]},
    ],
}

backup.run(config)   # back up changed files under each include
```

## Installation
```shell
pip install backupmaster
```
