from datetime import datetime

from libs.filemanager import FileManager as FileManagerLib
from libs.path import Path

class FileManager(FileManagerLib):
    root = Path.assets / Path(__file__).parent.name

    @staticmethod
    def get_path_names():
        paths = (FileManager.root / "paths").glob("*.yaml")
        names = [path.name.replace(".yaml", "") for path in paths]
        return names

    @staticmethod
    def get_sync_paths():
        return (FileManager.root / "paths" / "syncs" / "syncs").load()

    @staticmethod
    def get_profile_path():
        return FileManager.root / "profiles" / "active"

    @staticmethod
    def get_profiles_root():
        return FileManager.root / "profiles"

    @staticmethod
    def set_filters(filters):
        folder = FileManager.root / "filters"
        folder.mkdir(parents=True, exist_ok=True)

        # allow parallel runs without filter file conflicts
        path = (folder / str(datetime.now())).with_suffix(".txt")
        path.write_text(
            "\n".join(filters)
        )
        return path
