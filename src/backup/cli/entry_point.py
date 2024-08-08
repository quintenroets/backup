from package_utils.context.entry_point import create_entry_point

from backup.context import context
from backup.main.main import main

entry_point = create_entry_point(main, context)
