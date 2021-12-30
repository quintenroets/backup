from libs.path import Path

assets = Path.assets / Path(__file__).parent.name
Path.paths = assets / "paths"
Path.syncs = Path.paths / "syncs"
Path.ignore_names = Path.paths / "ignore_names"
Path.ignore_patterns = Path.paths / "ignore_patterns"
Path.paths_include = Path.paths / "include"
Path.paths_include_pull = Path.paths / "pull_include"
Path.paths_exclude = Path.paths / "exclude"

Path.timestamps = assets / "timestamps" / "timestamps"
Path.profiles = assets / "profiles"
Path.filters = assets / "filters"
Path.active_profile = Path.profiles / "active"
Path.profile_paths = Path.profiles / "paths"

Path.exports = assets / "exports"

Path.backup_cache = Path.HOME.parent / "backup"

Path.remote = "backup:Home"

Path.trusted = True
