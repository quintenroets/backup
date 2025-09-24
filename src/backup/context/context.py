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

    @cached_property
    def sub_check_path(self) -> Path | None:  # pragma: no cover
        if self.options.export_resume_changes:
            sub_check_path = Path.resume
        elif self.options.sub_check:
            sub_check_path = Path.cwd()
        else:
            sub_check_path = None
        return cast("Path | None", sub_check_path)


context = Context(Options, Config, Secrets)
