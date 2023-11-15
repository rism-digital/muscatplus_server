from typing import Iterable


async def to_aiter(iterable: Iterable):
    for item in iterable:
        yield item


def is_number(num: str) -> bool:
    try:
        float(num)
    except ValueError:
        return False
    return True
