from pprint import pprint
from typing import List, Optional
import re
import small_asc
import aiohttp
import asyncio
import uvloop

asyncio.set_event_loop(uvloop.new_event_loop())


async def fetch(session, url) -> Optional[str]:
    """Execute an http call async
    Args:
        session: contexte for making the http call
        url: URL to call
    Return:
        responses: A dict like object containing http response
    """
    async with session.get(url) as response:
        if response.status != 200:
            return f"Problem fetching {url}. Status code {response.status}."
        return None


async def fetch_all(sources: List) -> List:
    """ Gather many HTTP call made async
    Args:
        sources: a list of string
    Return:
        responses: A list of strings
    """
    async with aiohttp.ClientSession(headers={"Accept": "application/ld+json"}) as session:
        tasks = []

        for source in sources:
            tasks.append(
                fetch(session, f"http://dev.rism.offline/sources/{source}")
            )

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        return [r for r in responses if r]


def run(source_ids: List) -> List:
    responses = asyncio.run(
        fetch_all(source_ids)
    )
    return responses


if __name__ == "__main__":
    s = small_asc.Solr("http://localhost:8983/solr/muscatplus_live")
    fq = ["type:source", "country_code_s:CH"]
    sort = "id asc"
    fl: str = "id"

    res = s.search("*:*", fq=fq, fl=fl, sort=sort, rows=500, cursorMark="*")
    id_sub = re.compile(r"source_")
    print("Assembling IDs")
    ids: List = [re.sub(id_sub, "", s.get("id")) for s in res]

    print(f"Fetching {len(ids)} sources")
    responses = run(ids)

    print(f"Found {len(responses)} errors ({(len(responses) / len(ids)) * 100}%)")

    pprint(responses)
