from plib import Path


class Path(Path):
    # define here to make sure that all folders have this method
    
    @property
    def mtime(self):
        '''
        only precision up to one second to decide which files have the same mtime
        cannot be too precise to avoid false positives
        remote filesystem also has limited precision
        '''
        return int(super().mtime)
    
    @mtime.setter
    def mtime(self, time):
        '''
        setter needs to be redefined as well
        inheriting does not work for some reason
        '''
        import os
        import subprocess
        os.utime(self, (time, time)) # set create time as well
        try:
            subprocess.run(('touch', '-d', f'@{time}', self))
        except subprocess.CalledProcessError:
            pass # Doesn't work on Windows


class Path(Path):
    assets = Path.assets / 'backup'
    paths = assets / 'paths'
    syncs = paths / 'syncs'
    ignore_names = paths / 'ignore_names'
    ignore_patterns = paths / 'ignore_patterns'
    paths_include = paths / 'include'
    paths_include_pull = paths / 'pull_include'
    paths_exclude = paths / 'exclude'

    timestamps = assets / 'timestamps' / 'timestamps'
    profiles = assets / 'profiles'
    filters = assets / 'filters'
    active_profile = profiles / 'active'
    profile_paths = profiles / 'paths'

    exports = assets / 'exports'

    backup_cache = Path.HOME.parent / 'backup'

    remote = Path('backup:Home')
