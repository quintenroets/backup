from package_utils.storage import CachedFileContent

from ..models import Path


class Storage:
    number_of_paths: CachedFileContent[int] = CachedFileContent(
        Path.number_of_paths, default=0
    )
