import asyncio
import timeit

import httpx
import uvloop
from small_asc.client import Solr

asyncio.set_event_loop(uvloop.new_event_loop())


async def do_something(results, session) -> tuple[int, int]:
    succ = 0
    fail = 0

    for result in results:
        rid = result.get("id")
        if not rid:
            print("no id!")
            fail += 1
            continue

        rr = session.get(rid)
        if rr.status_code == 200:
            succ += 1
        else:
            fail += 1

    return succ, fail


async def search_request(url, session, succ, fail):
    r = await session.get(url)
    response = r.json()
    search_info = response.get("view")
    this_page = search_info["thisPage"]
    total_pages = search_info["totalPages"]
    results = search_info["results"]
    next = search_info["next"]

    p_succ, p_fail = await do_something(results, session)

    succ += p_succ
    fail += p_fail

    while this_page <= total_pages:
        print(f"Processing page {this_page} of {total_pages}")
        _ = await search_request(next, session, succ, fail)

    return succ, fail


async def run_search() -> tuple[int, int]:
    async with httpx.AsyncClient(
        headers={"Accept": "application/ld+json", "X-API-Accept-Language": "en"}
    ) as session:
        initial_url = "https://rism.online/search?mode=people"
        succ, fail = await search_request(initial_url, session, 0, 0)

    return succ, fail


async def get_ids():
    s = Solr("http://localhost:8983/solr/muscatplus_live")
    # fq = ["type:source", "country_code_s:CH"]
    # fq = ["type:source", "project_s:diamm"]
    # fq = ["type:institution", "project_s:diamm"]
    fq = ["type:institution", "!project_s:diamm", "!project_s:cantus"]
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
    print(f"Assembling {res.hits} IDs")
    ids: list = []
    async for s in res:
        ids.append(s.get("id", "").split("_")[-1])

    print(f"Actually got {len(ids)}")
    return ids


async def run() -> tuple[int, int]:
    item_ids: list = await get_ids()
    responses: list = []

    async with httpx.AsyncClient(
        headers={"Accept": "application/ld+json", "X-API-Accept-Language": "en"}
    ) as session:
        for num, itm in enumerate(item_ids):
            print(f"Processing record {num}")
            url: str = f"http://dev.rism.offline/institutions/{itm}"
            # url: str = f"http://dev.rism.offline/external/diamm/person/{itm}"
            res = await session.get(url)
            if res.status_code in (200, 410):
                responses.append(True)
            else:
                print(f"Error fetching {url}. Response code: {res.status_code}")
                responses.append(False)

    successes: int = responses.count(True)
    failures: int = responses.count(False)

    return successes, failures


async def main():
    start = timeit.default_timer()
    successes, failures = await run()
    # successes, failures = await run_search()
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
