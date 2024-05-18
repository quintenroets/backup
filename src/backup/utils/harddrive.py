import cli

from ..models import Path


def check(subpaths: str) -> None:
    if not Path.harddrive.exists():
        raise Exception("Connect harddrive first")

    if not subpaths:
        subpaths = Path.harddrive_paths.yaml

    for subpath in subpaths:
        source = Path.docs / "Backup" / subpath
        dest = Path.harddrive / subpath
        diff(source, dest)
        diff(dest, source)


def diff(source: Path, dest: Path) -> None:
    items = cli.track_progress(
        source.find(),
        description=f"Checking changes ({source})",
        unit="files",
        total=sum(1 for _ in source.find()),
    )

    for item in items:
        if item.is_file():
            mirror_item = dest / item.relative_to(source)
            if item.mtime != mirror_item.mtime:
                print(item)
