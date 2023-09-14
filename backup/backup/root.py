from dataclasses import dataclass, field

from backup.utils import Path

from . import syncer


@dataclass
class Backup(syncer.Backup):
    root_paths: list[Path] = field(default_factory=list)

    def push(self):
        if self.dest.is_root():
            self.process_root_dest()
        else:
            super().push()

    def restore_paths(self):
        # self.paths expected to be unmodified
        self.paths += self.root_paths

    def process_root_dest(self):
        self.process_root_paths()
        if self.paths:
            super().push()
        self.restore_paths()

    def process_root_paths(self):
        root_paths = self.extract_root_paths()
        self.root_paths = list(root_paths)
        if self.root_paths or not self.paths:
            self.push_root_paths()

    def extract_root_paths(self):
        self.paths = list(self.paths)
        for path in self.paths:
            dest = self.dest / path
            if dest.is_root():
                self.paths.remove(path)
                yield path

    def push_root_paths(self):
        with Path.tempfile() as temp_dest:
            temp_dest.unlink()
            self.push_root_paths_with_intermediate(temp_dest)

    def push_root_paths_with_intermediate(self, temp_dest: Path):
        paths = self.root_paths
        backups = (
            syncer.Backup(
                source=self.source, dest=temp_dest, paths=paths, quiet=self.quiet
            ),
            # need local source and dest for root operation
            syncer.Backup(
                source=temp_dest, dest=self.dest, root=True, quiet=True, paths=paths
            ),
        )
        for backup in backups:
            backup.push()
