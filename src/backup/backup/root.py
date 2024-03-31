import subprocess
from dataclasses import dataclass, field

from ..models import Path
from . import syncer


@dataclass
class Backup(syncer.Backup):
    root_paths: list[Path] = field(default_factory=list)

    def push(self, reverse: bool = False) -> subprocess.CompletedProcess:
        return (
            self.process_root_dest() if self.dest.is_root() else super().push(reverse)
        )

    def restore_paths(self) -> None:
        # self.paths expected to be unmodified
        self.paths += self.root_paths

    def process_root_dest(self) -> subprocess.CompletedProcess:
        self.process_root_paths()
        if self.paths:
            output = super().push()
        self.restore_paths()
        return output

    def process_root_paths(self) -> None:
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

    def push_root_paths(self) -> None:
        with Path.tempfile() as temp_dest:
            temp_dest.unlink()
            self.push_root_paths_with_intermediate(temp_dest)

    def push_root_paths_with_intermediate(self, temp_dest: Path) -> None:
        paths = self.root_paths
        (syncer.Backup(source=self.source, dest=temp_dest, paths=paths).push(),)
        # need local source and dest for root operation
        (
            syncer.Backup(
                source=temp_dest, dest=self.dest, root=True, paths=paths
            ).push(),
        )
