from pathlib import Path

from libs.filemanager import FileManager as FileManagerLib

class FileManager(FileManagerLib):
    root = FileManagerLib.root / Path(__file__).parent.name

    @staticmethod
    def get_path_names():
        paths = (FileManager.root / "paths").glob("*.yaml")
        names = [path.name.replace(".yaml", "") for path in paths]
        return names

    @staticmethod
    def get_sync_paths():
        return FileManager.load("paths", "syncs", "syncs")
