from libs.path import Path

Path.root = Path.assets / Path(__file__).parent.name
Path.paths = Path.root / "paths"
Path.syncs = Path.paths / "syncs"
Path.ignore_names = Path.paths / "ignore_names"
Path.ignores_patterns = Path.paths / "ignore_patterns"
Path.check_ignores = Path.paths / "check_ignores"
Path.paths_include = Path.paths / "include"

Path.timestamps = Path.root / "timestamps" / "timestamps"
Path.profiles = Path.root / "profiles"
Path.active_profile = Path.profiles / "active"
Path.profile_paths = Path.profiles / "paths"