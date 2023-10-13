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


def merge_language_maps(d1: dict[str, list], d2: dict[str, list]) -> dict[str, list]:
    return {key: [", ".join(value + d2[key])] for key, value in d1.items()}
