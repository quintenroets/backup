import os
from functools import cached_property
from typing import cast

from package_utils.context import Context as Context_

from backup.models import Path
from backup.storage.storage import Storage

from .config import Config
from .options import Options
from .secrets_ import Secrets


class Context(Context_[Options, Config, Secrets]):
    @cached_property
    def storage(self) -> Storage:
        return Storage()

    def extract_backup_source(self) -> Path:
        return self.config.backup_source

    def extract_backup_dest(self) -> Path:
        return self.config.backup_dest

    def extract_cache_path(self) -> Path:
        self.config.cache_path.mkdir(parents=True, exist_ok=True)
        return self.config.cache_path

    def extract_profiles_source_root(self) -> Path:
        path = self.config.backup_source / Path.HOME.relative_to(Path.backup_source)
        return cast("Path", path)

    @property
    def profiles_source_root(self) -> Path:
        return self.extract_profiles_source_root()

    @property
    def profiles_path(self) -> Path:
        path = self.config.backup_source / Path.profiles.relative_to(Path.backup_source)
        return cast("Path", path)

    @cached_property
    def username(self) -> str:
        return os.getenv("USERNAME", default="")


context = Context(Options, Config, Secrets)
