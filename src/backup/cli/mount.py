from package_utils.cli import create_entry_point

from backup.main.mount import Mounter

entry_point = create_entry_point(Mounter.run, Mounter)
