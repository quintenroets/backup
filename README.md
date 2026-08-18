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
import backup

config = {
    "source": "/home/user",
    "dest": "remote:backup",  # any rclone destination; a local path also works
    "syncs": [
        {"includes": [".ssh", ".config/git"], "excludes": ["*.log"]},
    ],
    "max_backup_size": int(50e6),        # larger files are left alone
    "rclone": {"n_parallel_transfers": 100},  # see RcloneConfig for the full set
}

backup.run(config)  # back up changed files under each include
```

The config says what to back up. How one run behaves is a separate argument, so
the same config can be driven in either direction:

```python
from backup import Action, Options

backup.run(config, Options(action=Action.pull))     # restore from the remote
backup.run(config, Options(diff=True))              # show content diffs first
backup.run(config, Options(confirm=False))          # apply without asking
```

### Syncing without change detection

`backup.syncer` is the rclone layer on its own: filters, transfers and remote
listings, with no sync state involved. Use it to move a known path around.

```python
from backup import create_syncer
from superpathlib import Path

syncer = create_syncer(directory=Path.HOME / "documents")
syncer.push()                      # mirror it to the configured remote
syncer.pull()                      # and back again

files = syncer.list_remote_files() # {"report.pdf": FileState(mtime, size), ...}
```

## Installation
```shell
pip install backupmaster
```
