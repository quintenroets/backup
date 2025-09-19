from collections.abc import Iterable, Iterator
from itertools import groupby
from typing import TypeVar

import cli

from backup.context import context

T = TypeVar("T")


def count_items(items: Iterator[T]) -> Iterator[T]:
    number_of_entries = 0
    for number_of_entries, item in enumerate(items, start=1):  # noqa: B007
        yield item
    context.storage.number_of_paths = number_of_entries


def extract_pairs(sources: Iterable[Iterator[T]]) -> Iterator[int, T]:
    for i, values in enumerate(sources):
        for value in values:
            yield i, value


def aggregate_iterators_with_progress(
    sources: Iterable[Iterator[T]],
    description: str,
    unit: str,
) -> Iterator[Iterator[T]]:
    pairs = cli.track_progress(
        count_items(extract_pairs(sources)),
        description=description,
        unit=unit,
        total=context.storage.number_of_paths,
        cleanup_after_finish=True,
    )
    for _, group in groupby(pairs, key=lambda pair: pair[0]):
        yield (pair[1] for pair in group)
