from collections.abc import Iterable, Iterator
from itertools import groupby
from operator import itemgetter
from typing import TypeVar

import cli

from backup.context import context

T = TypeVar("T")


def count_items(items: Iterator[T]) -> Iterator[T]:
    number_of_entries = 0
    for number_of_entries, item in enumerate(items, start=1):  # noqa: B007
        yield item
    context.storage.number_of_paths = number_of_entries


def extract_pairs(sources: Iterable[Iterator[T]]) -> Iterator[tuple[int, T]]:
    for i, values in enumerate(sources):
        for value in values:
            yield i, value


def fill_gaps(
    indexed_groups: Iterable[tuple[int, Iterator[T]]],
    total: int,
) -> Iterator[Iterator[T]]:
    groups = iter(indexed_groups)
    current = next(groups, None)
    for expected in range(total):
        if current is not None and current[0] == expected:
            yield current[1]
            current = next(groups, None)
        else:
            yield iter(())


def aggregate_iterators_with_progress(
    sources: Iterable[Iterator[T]],
    description: str,
    unit: str,
) -> Iterator[Iterator[T]]:
    sources_list = list(sources)
    pairs = cli.track_progress(
        count_items(extract_pairs(sources_list)),
        description=description,
        unit=unit,
        total=context.storage.number_of_paths,
        cleanup_after_finish=True,
    )
    indexed_groups = (
        (i, (pair[1] for pair in group))
        for i, group in groupby(pairs, key=itemgetter(0))
    )
    yield from fill_gaps(indexed_groups, len(sources_list))
