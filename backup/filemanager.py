from libs.path import Path

class FileManager:
    root = Path.assets / Path(__file__).parent.name

    @staticmethod
    def get_path_names():
        paths = (FileManager.root / "paths").glob("*.yaml")
        names = [path.name.replace(".yaml", "") for path in paths]
        return names

    @staticmethod
    def get_sync_paths():
        return (FileManager.root / "paths" / "syncs" / "syncs").load()