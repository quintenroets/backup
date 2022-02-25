from . import parser
from .active_profile import active_profile
from .backup import Backup
from .path import Path


def get_filters():
    paths = Path.profile_paths.load()
    paths = parser.parse_paths(paths)
    filters = parser.make_filters(paths)
    return filters


def copy(source, dest):
    filters = get_filters()
    # cannot use delete_missing because source and dest overlap partly
    return Backup.copy(
        source,
        dest,
        filters=filters,
        delete_missing=False,
        quiet=True,
        overwrite_newer=True,
    )


def save(name):
    copy(Path.HOME, Path.profiles / name)


def load(name):
    """
    Load new profile without saving the previous and changing active profile name
    """
    source = Path.profiles / name
    if source.exists():
        copy(source, Path.HOME)


def apply(name):
    save_active()
    load(name)
    active_profile.name = name


def reload():
    """
    Reload config of active profile
    """
    load(active_profile.name)


def save_active():
    """
    Save config files to active profile
    """
    save(active_profile.name)
