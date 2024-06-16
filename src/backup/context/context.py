from functools import cached_property
from typing import cast

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

    def extract_cache_path(self) -> Path:
        return self.config.cache_path

    def extract_profiles_source_root(self) -> Path:
        path = self.config.backup_source / Path.HOME.relative_to(Path.backup_source)
        return cast(Path, path)

    @property
    def profiles_source_root(self) -> Path:
        return self.extract_profiles_source_root()

    @property
    def resume_path(self) -> Path:
        path = self.config.backup_source / Path.resume.relative_to(Path.backup_source)
        return cast(Path, path)

    @property
    def profiles_path(self) -> Path:
        path = self.config.backup_source / Path.profiles.relative_to(Path.backup_source)
        return cast(Path, path)

    @property
    def config_path(self) -> Path:
        path = self.config.backup_source / Path.config.relative_to(Path.backup_source)
        return cast(Path, path)

    @property
    def main_resume_pdf_path(self) -> Path:
        return self.resume_path / "Resume Quinten Roets.pdf"

    @property
    def selected_resume_pdf_path(self) -> Path:
        return self.resume_path / "Main" / self.main_resume_pdf_path.name


context = Context(Options, Config, Secrets)
