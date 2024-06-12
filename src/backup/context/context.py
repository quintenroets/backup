from functools import cached_property

from package_utils.context import Context as Context_

from ..models import Config, Options, Path, Secrets
from ..storage.storage import Storage


class Context(Context_[Options, Config, Secrets]):
    @cached_property
    def storage(self) -> Storage:
        return Storage()

    def extract_backup_source(self) -> Path:
        return self.config.backup_source

    def extract_backup_dest(self) -> Path:
        return self.config.backup_dest

    def extract_profiles_path(self) -> Path:
        return self.config.profiles_path

    def extract_cache_path(self) -> Path:
        return self.config.cache_path


context = Context(Options, Config, Secrets)
