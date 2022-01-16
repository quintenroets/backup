from .backup import Backup
from .path import Path
from . import parser


class ProfileManager:
    @staticmethod
    def get_filters():
        paths = Path.profile_paths.load()
        paths = parser.parse_paths(paths)
        filters = parser.make_filters(paths)
        return filters

    @staticmethod
    def copy(source, dest):
        filters = ProfileManager.get_filters()
        # cannot use delete_missing because source and dest overlap partly
        return Backup.copy(source, dest, filters=filters, delete_missing=False, quiet=True, overwrite_newer=True)

    @staticmethod
    def save(name):
        ProfileManager.copy(Path.HOME, Path.profiles / name)

    @staticmethod
    def load(name):
        '''
        Load new profile without saving the previous and changing active profile name
        '''
        source = Path.profiles / name
        if source.exists():
            ProfileManager.copy(source, Path.HOME)

    @staticmethod
    def apply(name):
        ProfileManager.save_active()
        ProfileManager.load(name)
        ProfileManager.set_active(name)

    @classmethod
    @property
    def active_profile(cls):
        return Path.active_profile.load() or 'light'

    @staticmethod
    def set_active(name):
        return Path.active_profile.save(name)

    @staticmethod
    def reload():
        '''
        Reload config of active profile
        '''
        ProfileManager.load(ProfileManager.active_profile)

    @staticmethod
    def save_active():
        '''
        Save config files to active profile
        '''
        ProfileManager.save(ProfileManager.active_profile)
