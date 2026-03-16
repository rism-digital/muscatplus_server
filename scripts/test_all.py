import argparse
import asyncio
import logging
import random
import sys
from datetime import timedelta

from pyreqwest import exceptions
from pyreqwest.client import Client, ClientBuilder
from small_asc.client import Solr

solr_conn = Solr("http://localhost:8983/solr/muscatplus_live")

VALID_CODES = {200, 410}

# ---- tune these for your environment ----
MAX_CONCURRENCY = 50  # cap simultaneous requests
MAX_CONNECTIONS = 200
MAX_KEEPALIVE_CONNECTIONS = 50
CONNECT_TIMEOUT = timedelta(seconds=10)
READ_TIMEOUT = timedelta(seconds=10)
POOL_TIMEOUT = timedelta(seconds=10)
USE_HTTP2 = True
# ----------------------------------------


def id_from_solr_record(record: dict) -> str:
    record_type: str = record["type"]

    if record_type == "holding":
        source_id_value: str = record["source_id"].split("_")[-1]
        holding_id_value: str = record["holding_id"].split("_")[-1]
        return f"/sources/{source_id_value}/holdings/{holding_id_value}"
    elif record_type == "source":
        source_id = record["id"].split("_")[-1]
        return f"/sources/{source_id}"
    elif record_type == "person":
        person_id = record["id"].split("_")[-1]
        return f"/people/{person_id}"
    elif record_type == "institution":
        institution_id = record["id"].split("_")[-1]
        return f"/institutions/{institution_id}"
    elif record_type == "work":
        work_id = record["id"].split("_")[-1]
        return f"/works/{work_id}"
    elif record_type == "incipit":
        incipit_id = record["id"].split("_")[-1]
        return f"/incipits/{incipit_id}"
    else:
        raise ValueError(f"Unknown record type {record_type}")


async def fetch_url(
    url: str, client: Client, sem: asyncio.Semaphore
) -> tuple[str, bool, int | None, str | None]:
    log.debug("Fetching %s", url)
    async with sem:
        try:
            r = await (
                client.get(url)
                .timeout(READ_TIMEOUT)
                .error_for_status(False)
                .build()
                .send()
            )
            # read the body so the connection is reusable (even if you don’t need it)
            await r.bytes()
            return url, r.status in VALID_CODES, r.status, None
        except exceptions.StatusError as e:
            # only raised if error_for_status() used; included for completeness
            return (
                url,
                False,
                None,
                f"StatusError: {e}",
            )
        except exceptions.RequestTimeoutError:
            return url, False, None, "Timeout"
        except exceptions.RequestError as e:
            # DNS errors, TLS errors, refused connections, etc.
            return url, False, None, f"RequestError: {e}"
        except Exception as e:
            return url, False, None, f"Other error: {e}"


async def get_ids(record_type: str, baseurl: str, limit: int | None = None):
    fq = [f"type:{record_type}", "!project_s:diamm", "!project_s:cantus"]
    if limit:
        # if we have a limit set, we want to sample a random subset of the records. We use the
        # RandomSortField functionality to do this.
        rand_seed: int = random.randint(1, 9999)  # noqa: S311
        sort = f"random_{rand_seed} desc"
    else:
        sort = "id asc"

    fl: list = ["id"]

    res = await solr_conn.search(
        {"query": "*:*", "filter": fq, "fields": fl, "sort": sort, "limit": 500},
        cursor=True,
    )
    log.info("Found %s total URLs", res.hits)
    urls: list = []
    num_ids: int = 0
    async for s in res:
        record_id: str = id_from_solr_record(s)
        urls.append(f"{baseurl}{record_id}")
        num_ids += 1
        if limit and num_ids >= limit:
            # once we've reached our limit, stop adding IDs.
            break

    log.info("Actually running the test with %s URLs", len(urls))
    log.debug("First 10 URLs: %s", urls[:10])
    return urls


async def main(args: argparse.Namespace) -> bool:
    res: bool = True
    log.info("Getting IDs")
    list_of_urls: list = await get_ids(args.type, args.baseurl, args.limit)

    sem = asyncio.Semaphore(MAX_CONCURRENCY)
    client_builder = (
        ClientBuilder()
        .default_headers(
            {"Accept": "application/ld+json", "X-API-Accept-Language": "en"}
        )
        .max_connections(MAX_CONNECTIONS)
        .pool_max_idle_per_host(MAX_KEEPALIVE_CONNECTIONS)
        .connect_timeout(CONNECT_TIMEOUT)
        .read_timeout(READ_TIMEOUT)
        .pool_timeout(POOL_TIMEOUT)
        .http2(USE_HTTP2)
    )
    async with client_builder.build() as client:
        tasks = [fetch_url(url, client, sem) for url in list_of_urls]
        results = await asyncio.gather(*tasks)

    ok_nok = [ok for (_url, ok, _status, _err) in results]
    all_failures = [u for u in results if not u[1]]
    success: int = ok_nok.count(True)
    failure: int = ok_nok.count(False)

    log.info("Success: %s, Failures: %s", success, failure)
    if all_failures:
        log.error("Failures: %s", all_failures)

    return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("type")
    parser.add_argument(
        "-l", "--limit", help="Limit the number of records to process", type=int
    )
    parser.add_argument(
        "-c", "--count", action="store_true", help="Count the number of records"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose output (log level DEBUG)"
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Quiet output (log level WARNING)"
    )
    parser.add_argument("-b", "--baseurl", default="http://dev.rism.offline")

    parsed_args = parser.parse_args()
    print(parsed_args.verbose, parsed_args.quiet)

    if parsed_args.verbose:
        loglevel = logging.DEBUG
    elif parsed_args.quiet:
        loglevel = logging.WARNING
    else:
        loglevel = logging.INFO

    logging.basicConfig(
        format="[%(name)s][%(asctime)s] [%(levelname)8s] %(message)s (%(filename)s:%(lineno)s)",
        level=loglevel,
    )

    log = logging.getLogger("link_test")
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("pyreqwest").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    log.info("Parsed args: %s", parsed_args)

    res: bool = asyncio.run(main(parsed_args))

    if not res:
        sys.exit(1)
    sys.exit()
