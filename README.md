# Backup
[![PyPI version](https://badge.fury.io/py/backupmaster.svg)](https://badge.fury.io/py/backupmaster)
![PyPI downloads](https://img.shields.io/pypi/dm/backupmaster)
![Python version](https://img.shields.io/badge/python-3.11+-brightgreen)
![Operating system](https://img.shields.io/badge/os-linux-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)

Generic engine to back up important files across an entire disk to an [rclone](https://rclone.org) remote with change detection.
- Scales to a huge number of files
- Detailed configuration to maximize performance
- Perfect for files that are too volatile for a VCS like Git and too important to lose

## Usage
```python
from pathlib import Path

import backup

syncs = [backup.SyncEntry(includes=[".ssh", ".config/git"], excludes=["*.log"])]
dest = Path("remote:backup")  # rclone remote or local path
config = backup.Config(source=Path.home(), dest=dest, syncs=syncs)

backup.run(config)  # back up changed files under each include
```

## Installation
```shell
pip install backupmaster
```
