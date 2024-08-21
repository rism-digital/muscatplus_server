import asyncio
import re
import timeit

import aiohttp
import uvloop
from small_asc.client import Solr

asyncio.set_event_loop(uvloop.new_event_loop())


async def fetch(url: str, session, num: int) -> bool:
    print(f"{num}. fetching {url}")
    async with session.get(url) as r:
        txt = await r.json()
        # print(txt)
        if r.status == 200:
            return True

        print(f"Error fetching {url}")
        return False


async def get_ids():
    s = Solr("http://localhost:8983/solr/muscatplus_live")
    # fq = ["type:source", "country_code_s:CH"]
    # fq = ["type:source", "project_s:diamm"]
    # fq = ["type:institution", "project_s:diamm"]
    fq = ["type:institution", "!project_s:diamm"]
    # fq = ["type:person", "project_s:diamm"]
    # fq = ["type:person", "!project_s:diamm"]
    # fq = ["type:institution"]
    # fq = ["type:person"]
    sort = "id asc"
    fl: list = ["id"]

    res = await s.search(
        {"query": "*:*", "filter": fq, "fields": fl, "sort": sort, "limit": 500},
        cursor=True,
    )
    id_sub = re.compile(
        r"source_|person_|institution_|diamm_source_|diamm_organization_|diamm_person_"
    )
    print(f"Assembling {res.hits} IDs")
    ids: list = []
    async for s in res:
        ids.append(re.sub(id_sub, "", s.get("id")))

    print(f"Actually got {len(ids)}")
    return ids


async def run() -> (int, int):
    item_ids: list = await get_ids()
    responses: list = []

    async with aiohttp.ClientSession(
        headers={"Accept": "application/ld+json", "X-API-Accept-Language": "en"}
    ) as session:
        for num, itm in enumerate(item_ids):
            url: str = f"http://dev.rism.offline/institutions/{itm}"
            # url: str = f"http://dev.rism.offline/external/diamm/person/{itm}"
            res: bool = await fetch(url, session, num)
            responses.append(res)

    successes: int = responses.count(True)
    failures: int = responses.count(False)

    return successes, failures


async def main():
    start = timeit.default_timer()
    successes, failures = await run()
    end = timeit.default_timer()
    elapsed: float = end - start

    hours, remainder = divmod(elapsed, 60 * 60)
    minutes, seconds = divmod(remainder, 60)
    total = successes + failures
    print(f"Processed {total} records")
    print(f"Found {failures} errors ({(failures / total) * 100}%)")
    print(f"Total time to download: {int(hours):02}:{int(minutes):02}:{seconds:02.2}")
    print(f"Download rate: {total / elapsed}r/s")


if __name__ == "__main__":
    asyncio.run(main())
