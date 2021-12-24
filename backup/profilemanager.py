from libs.path import Path

from .backup import Backup
from .filemanager import FileManager
from . import parser


class ProfileManager:
    @staticmethod
    def get_filters():
        paths = (FileManager.get_profiles_root() / "paths").load()
        paths = parser.parse_paths(paths)
        filters = parser.make_filters(paths)
        return filters

    @staticmethod
    def copy(source, dest):
        filters = ProfileManager.get_filters()
        # cannot use delete_missing because source and dest overlap partly
        return Backup.sync(source, dest, filters=filters, delete_missing=False, quiet=False)

    @staticmethod
    def save(name):
        dest = FileManager.get_profiles_root() / name
        ProfileManager.copy(Path.home(), dest)

    @staticmethod
    def load(name):
        """
        Load new profile without saving the previous and changing active profile name
        """
        source = FileManager.get_profiles_root() / name
        if source.exists():
            ProfileManager.copy(source, Path.home())

    @staticmethod
    def apply(name):
        active_path = FileManager.get_profile_path()
        active_name = active_path.load() or "light"
        ProfileManager.save(active_name)
        ProfileManager.load(name)
        active_path.save(name)

    @staticmethod
    def apply_dark():
        ProfileManager.apply("dark")

    @staticmethod
    def apply_light():
        ProfileManager.apply("light")