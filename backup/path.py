from plib import Path

assets = Path.assets / Path(__file__).parent.name

class Path(Path):
    paths = assets / "paths"
    syncs = paths / "syncs"
    ignore_names = paths / "ignore_names"
    ignore_patterns = paths / "ignore_patterns"
    paths_include = paths / "include"
    paths_include_pull = paths / "pull_include"
    paths_exclude = paths / "exclude"

    timestamps = assets / "timestamps" / "timestamps"
    profiles = assets / "profiles"
    filters = assets / "filters"
    active_profile = profiles / "active"
    profile_paths = profiles / "paths"

    exports = assets / "exports"

    backup_cache = Path.HOME.parent / "backup"

    remote = "backup:Home"

    @property
    def mtime(self):
        # no huge precision needed and remote path also has limited precision
        # so avoid precision differences to lead to detected differences in mtime
        return int(super().mtime)    
