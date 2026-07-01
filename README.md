# Backup
[![PyPI version](https://badge.fury.io/py/backupmaster.svg)](https://badge.fury.io/py/backupmaster)
![PyPI downloads](https://img.shields.io/pypi/dm/backupmaster)
![Python version](https://img.shields.io/badge/python-3.10+-brightgreen)
![Operating system](https://img.shields.io/badge/os-linux-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)

Back up the files that matter from across your entire disk to any [rclone](https://rclone.org) remote, transferring only what changed.
- Scales to millions of files: one stat per file, no content hashing
- Selective and disk-wide: back up scattered paths, skip everything else
- Ideal for volatile files a VCS like Git cannot handle efficiently

Pair it with a versioned remote to keep every file recoverable, not just mirrored.

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
