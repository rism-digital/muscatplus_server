from typing import Iterable


async def to_aiter(iterable: Iterable):
    for item in iterable:
        yield item
