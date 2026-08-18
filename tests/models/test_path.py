from backup.backup.models import Path, resolve_overlapping_sub_path


def test_dest_nested_in_the_source_overlaps() -> None:
    source = Path("/source")
    assert resolve_overlapping_sub_path(source, source / "remote") == Path("remote")


def test_repeated_name_walks_up_to_the_outermost_overlap() -> None:
    source = Path("/root/name")
    dest = source / "sub_path" / source.name
    assert resolve_overlapping_sub_path(source, dest) == Path("sub_path")


def test_unrelated_roots_do_not_overlap() -> None:
    assert resolve_overlapping_sub_path(Path("/source"), Path("/dest")) is None
