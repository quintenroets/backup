from itertools import groupby

import cli

from backup.context import context

from typing import Any, Iterator, TypeVar, Iterable

K = TypeVar("K")
V = TypeVar("V")


def count_items(items: Iterator[Any]) -> Iterator[Any]:
    number_of_entries = 0
    for number_of_entries, item in enumerate(items, start=1):
        yield item
    context.storage.number_of_paths = number_of_entries


def extract_pairs(sources: Iterable[Iterator[Any]]):
    for i, values in enumerate(sources):
        for value in values:
            yield i, value


def aggregate_iterators_with_progress(
    sources: Iterable[Iterator[Any]],
    description: str,
    unit: str,
) -> Iterator[Iterator[V]]:
    pairs = cli.track_progress(
        count_items(extract_pairs(sources)),
        description=description,
        unit=unit,
        total=context.storage.number_of_paths,
        cleanup_after_finish=True,
    )
    for _, group in groupby(pairs, key=lambda pair: pair[0]):
        yield (pair[1] for pair in group)
