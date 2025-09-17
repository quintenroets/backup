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

    @property
    def profiles_path(self) -> Path:
        path = self.config.backup_source / Path.profiles.relative_to(Path.backup_source)
        return cast("Path", path)

    @cached_property
    def sub_check_path(self) -> Path | None:  # pragma: no cover
        if self.options.export_resume_changes:
            sub_check_path = Path.resume
        elif self.options.sub_check:
            sub_check_path = Path.cwd()
        else:
            sub_check_path = None
        # if sub_check_path is not None:
        ## sub_check_path = sub_check_path.relative_to(self.config.backup_source)
        return cast("Path | None", sub_check_path)


context = Context(Options, Config, Secrets)
