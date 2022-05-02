import asyncio
import re
import timeit
from typing import Callable

import aiohttp
import aiofiles
import uvloop
from small_asc.client import Solr

asyncio.set_event_loop(uvloop.new_event_loop())


async def download(url: str, session) -> bool:
    async with session.get(url, headers={"Accept": "text/turtle"}) as response:
        turtle = await response.text()
        fname = url.split("/")[-1]
        if response.status == 200:
            async with aiofiles.open(f"../ttl/{fname}.ttl", mode="w") as ttlout:
                await ttlout.write(turtle)
                return True
        return False


async def fetch(url, session) -> bool:
    """Execute an http call async
    Args:
        session: contexte for making the http call
        url: URL to call
    Return:
        responses: A dict like object containing http response
    """
    async with session.get(url, headers={"Accept": "application/ld+json"}) as response:
        if response.status != 200:
            return False
        return True


async def gather_with_concurrency(n, *tasks):
    semaphore = asyncio.Semaphore(n)

    async def sem_task(task):
        async with semaphore:
            return await task
    return await asyncio.gather(*(sem_task(task) for task in tasks), return_exceptions=True)


async def fetch_all(sources: list) -> tuple[int, int]:
    """ Gather many HTTP call made async
    Args:
        sources: a list of string
    Return:
        responses: A list of strings. If a call is successful, the entry is 'None'.
    """
    print("Fetching all!")
    async with aiohttp.ClientSession() as session:
        tasks = []

        for source in sources:
            tasks.append(
                fetch(f"http://dev.rism.offline/sources/{source}", session)
            )

        responses = await gather_with_concurrency(100, *tasks)

        successes: int = responses.count(True)
        failures: int = responses.count(False)

        return successes, failures


async def download_all(sources: list) -> tuple[int, int]:
    """ Gather many HTTP call made async
    Args:
        sources: a list of string
    Return:
        responses: A list of strings. If a call is successful, the entry is 'None'.
    """
    async with aiohttp.ClientSession(headers={"Accept": "application/ld+json"}) as session:
        tasks = []

        for source in sources:
            tasks.append(
                download(f"http://dev.rism.offline/sources/{source}", session)
            )
        responses = await gather_with_concurrency(100, *tasks)

        successes: int = responses.count(True)
        failures: int = responses.count(False)

        return successes, failures


def run(source_ids: list, action: Callable) -> tuple[int, int]:
    success, failure = asyncio.run(
        action(source_ids)
    )
    return success, failure


if __name__ == "__main__":
    s = Solr("http://localhost:8983/solr/muscatplus_live")
    fq = ["type:source", "country_code_s:GB"]
    sort = "id asc"
    fl: list = ["id"]

    res = s.search({"query": "*:*", "filter": fq, "fields": fl, "sort": sort, "limit": 500}, cursor=True)
    id_sub = re.compile(r"source_")
    print("Assembling IDs")
    ids: list = [re.sub(id_sub, "", s.get("id")) for s in res]

    print(f"Fetching {res.hits} sources")

    start = timeit.default_timer()
    successes, failures = run(ids, download_all)
    end = timeit.default_timer()
    elapsed: float = end - start

    hours, remainder = divmod(elapsed, 60 * 60)
    minutes, seconds = divmod(remainder, 60)
    total = successes + failures
    print(f"Found {failures} errors ({(failures / total) * 100}%)")
    print(f"Total time to download: {int(hours):02}:{int(minutes):02}:{seconds:02.2}")
    print(f"Download rate: {total / elapsed}r/s")
