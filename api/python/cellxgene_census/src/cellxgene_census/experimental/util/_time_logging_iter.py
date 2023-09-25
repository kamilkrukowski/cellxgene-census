import logging
import time
from typing import Iterator, TypeVar

T = TypeVar("T")


class TimeLoggingIterator(Iterator[T]):
    "An iterator wrapper that logs the time taken for each item processed."

    def __init__(self, logger: logging.Logger, iterator: Iterator[T], name: str) -> None:
        self.iterator = iterator
        self.name = name
        self.logger = logger
        self.item_number = 0

    def __iter__(self) -> "TimeLoggingIterator[T]":
        return self

    def __next__(self) -> T:
        start_time = time.time()
        try:
            value = next(self.iterator)
        except StopIteration:
            raise
        else:
            end_time = time.time()
            elapsed_time = round(end_time - start_time, 3)
            self.item_number += 1
            self.logger.warning(f"{self.name} iterator: {elapsed_time}s for item #{self.item_number}")
            return value
