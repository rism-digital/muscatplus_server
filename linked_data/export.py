import argparse
import asyncio
import concurrent.futures
import logging.config
import sqlite3
import subprocess
import timeit
from pathlib import Path
from typing import Optional

import aiohttp
import rdflib
import uvloop
import yaml
from orjson import orjson
from sanic.compat import Header
from sanic.models.protocol_types import TransportProtocol
from sanic.request import Request
from small_asc.client import Solr

from search_server.resources.institutions.institution import Institution
from search_server.resources.people.person import Person
from search_server.resources.sources.full_source import FullSource
from search_server.server import app
from shared_helpers.jsonld import (
    RISM_JSONLD_SOURCE_CONTEXT,
    RISM_JSONLD_PERSON_CONTEXT,
    RISM_JSONLD_INSTITUTION_CONTEXT,
    RISM_JSONLD_DEFAULT_CONTEXT,
)
from shared_helpers.languages import load_translations, filter_languages


log_config: dict = yaml.safe_load(open("linked_data/logging.yml", "r"))
logging.config.dictConfig(log_config)

log = logging.getLogger("ld_export")

config: dict = yaml.safe_load(open("configuration.yml", "r"))
SOLR_SERVER: str = config["solr"]["server"]

solr_conn = Solr(SOLR_SERVER)

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


# Mock route for the request
class Route:
    def __init__(self):
        self.name = ""


# Alters the response to make all the URIs appear to be coming from the production site.
# Since every URL in the serializers runs through the `get_identifier` function, it will
# pick up on this info for constructing the URI.
headers: Header = Header(
    {
        "X-Forwarded-Proto": "https",
        "X-Forwarded-Host": "rism.online",
    }
)
translations: dict = load_translations("locales/")
filt_translations: dict = filter_languages({"en"}, translations)

route = Route()

req = Request(bytes("/foo", "ascii"), headers, "", "GET", TransportProtocol(), app)
req.ctx.translations = filt_translations
req.route = route

serializer_map: dict = {
    "source": FullSource,
    "person": Person,
    "institution": Institution,
}


def to_turtle(data: dict) -> str:
    json_serialized: str = orjson.dumps(data)
    graph_object: rdflib.Graph = rdflib.Graph().parse(
        data=json_serialized, format="application/ld+json"
    )
    turtle: str = graph_object.serialize(format="nt")

    return turtle


async def create_id_groups(
    num_groups: int, record_type: str, country_code: Optional[str]
) -> list:
    log.info("Creating ID groups")
    fq = [f"type:{record_type}", "!project_s:[* TO *]"]

    if record_type == "source" and country_code:
        fq.append(f"country_codes_sm:{country_code}")

    fl = ["id"]

    res = await solr_conn.search(
        {"query": "*:*", "filter": fq, "fields": fl, "sort": "id asc", "limit": 1000},
        cursor=True,
    )
    log.debug("Gathering groups")
    id_list: list = [sdoc["id"] async for sdoc in res]

    log.debug("Gathering done, found %s total IDs", res.hits)
    split_groups: list = [id_list[g::num_groups] for g in range(num_groups)]

    log.info(
        "Created %s groups from %s documents, first has %s IDs, last has %s IDs",
        len(split_groups),
        res.hits,
        len(split_groups[0]),
        len(split_groups[-1]),
    )

    return split_groups


async def run_serializer(
    docid: str, serializer, ctx_val: dict, semaphore, session, sqlconn
) -> None:
    async with semaphore:
        log.debug("Serializing %s", docid)

        try:
            this_doc = await solr_conn.get(docid)
        except Exception as e:
            log.critical(
                "=========== Exception raised in get request for source %s: %s",
                docid,
                e,
            )
            return None

        if this_doc is None:
            log.error("No document for %s", docid)

        try:
            serialized = await serializer(
                this_doc,
                context={"request": req, "direct_request": True, "session": session},
            ).data
        except Exception as e:
            log.critical(
                "=========== Exception raised in serializer for source %s: %s", docid, e
            )
            return None

        serialized.update(ctx_val)
        turtle: str = to_turtle(serialized)
        if not turtle:
            log.critical("No output! %s", docid)

        with sqlconn:
            sqlconn.execute(
                "INSERT INTO serialized VALUES (?, ?, ?)",
                (docid, this_doc["type"], turtle),
            )

        sqlconn.commit()
        await asyncio.sleep(0.5)


async def serialize(id_group: list, record_type: str, semaphore, dbname: str) -> None:
    log.debug("Actually serializing! Processing %s IDs", len(id_group))
    if record_type == "source":
        ctx_val = {"@context": RISM_JSONLD_SOURCE_CONTEXT}
    elif record_type == "person":
        ctx_val = {"@context": RISM_JSONLD_PERSON_CONTEXT}
    elif record_type == "institution":
        ctx_val = {"@context": RISM_JSONLD_INSTITUTION_CONTEXT}
    else:
        log.warning(
            "Could not determine context for %s. Using the default context", record_type
        )
        ctx_val = {"@context": RISM_JSONLD_DEFAULT_CONTEXT}

    tasks = set()
    serializer = serializer_map.get(record_type)
    if not serializer:
        log.critical(
            "There was a problem retrieving the serializer class for %s", record_type
        )
        return None

    sqlconn = sqlite3.connect(dbname)
    async with aiohttp.ClientSession(
        json_serialize=lambda x: orjson.dumps(x).decode("utf-8")
    ) as session:
        for docid in id_group:
            task = asyncio.create_task(
                run_serializer(docid, serializer, ctx_val, semaphore, session, sqlconn)
            )
            tasks.add(task)
            task.add_done_callback(tasks.discard)

        for coro in asyncio.as_completed(tasks):
            try:
                _ = await coro
            except Exception as e:
                log.critical(
                    "===========================================   Exception raised! %s",
                    e,
                )

    sqlconn.commit()
    sqlconn.close()


def do_serialize(id_group: list, resource_type: str, dbname: str):
    num_async_procs: int = 10
    semaphore = asyncio.Semaphore(num_async_procs)
    asyncio.run(serialize(id_group, resource_type, semaphore, dbname))


def main(args: argparse.Namespace, parallel_processes: int) -> bool:
    types_to_serialize: list
    if not args.include:
        types_to_serialize = ["source", "person", "institution"]
    else:
        types_to_serialize = args.include

    output_path: Path = args.output
    output_path.mkdir(parents=True, exist_ok=True)

    log.info(f"Running with {parallel_processes} processes")

    if args.empty:
        for i in range(parallel_processes):
            db_file = Path(args.output, f"output_{i}.db")
            if db_file.exists():
                log.info("Removing %s", str(db_file))
                db_file.unlink(missing_ok=True)

    for i in range(parallel_processes):
        db_file = Path(args.output, f"output_{i}.db")
        db_name = str(db_file)

        sqlconn = sqlite3.connect(db_name)
        sql_stmt: str = f"CREATE TABLE IF NOT EXISTS serialized(id TEXT PRIMARY KEY, type TEXT, ttl TEXT)"
        sqlconn.execute(sql_stmt)
        sqlconn.commit()
        sqlconn.close()

    for rec_type in types_to_serialize:
        log.info("Running serializer for %s", rec_type)
        id_groups: list = asyncio.run(
            create_id_groups(parallel_processes, rec_type, args.country)
        )
        log.debug(
            "Got %s id groups, for %s parallel processes",
            len(id_groups),
            parallel_processes,
        )
        num_results: int = sum([len(x) for x in id_groups])
        log.info("The number of results we will process is %s", num_results)
        start_serialize = timeit.default_timer()

        futures = []
        with concurrent.futures.ProcessPoolExecutor(parallel_processes) as executor:
            for i in range(parallel_processes):
                this_group = id_groups[i]
                if not this_group:
                    continue

                db_file = Path(args.output, f"output_{i}.db")
                db_name = str(db_file)

                new_future = executor.submit(
                    do_serialize, id_groups[i], rec_type, db_name
                )
                futures.append(new_future)

        for f in concurrent.futures.as_completed(futures):
            f.result()

        end_serialize = timeit.default_timer()
        s_elapsed: float = end_serialize - start_serialize
        s_hours, s_remainder = divmod(s_elapsed, 60 * 60)
        s_minutes, s_seconds = divmod(s_remainder, 60)
        log.info(
            f"Total time to serialize {rec_type}: {int(s_hours):02}:{int(s_minutes):02}:{round(s_seconds):02} (Total: {s_elapsed}s)"
        )
        log.info(f"Total processing rate: {num_results / s_elapsed} docs/s")

    for i in range(parallel_processes):
        db_name = Path(args.output, f"output_{i}.db")
        ttl_path = Path(args.output, f"output_{i}.nt")

        if args.empty:
            log.info("Removing %s", str(ttl_path))
            ttl_path.unlink(missing_ok=True)

        with open(ttl_path, "w") as ttl_out:
            log.info("Writing TTL output to %s", str(ttl_path))
            sql_stmt = f"SELECT ttl FROM serialized"

            subprocess.run(["sqlite3", str(db_name), sql_stmt], stdout=ttl_out)

    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-o", "--output", default="../ttl", type=Path, help="Output directory"
    )
    parser.add_argument(
        "-e",
        "--empty",
        dest="empty",
        action="store_true",
        help="Empty the output directory before starting",
    )
    parser.add_argument("-c", "--country", help="Optional country code for sources")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose output (log level DEBUG)"
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Quiet output (log level WARNING)"
    )
    parser.add_argument("--include", action="extend", nargs="*")

    incoming_args = parser.parse_args()

    if incoming_args.verbose:
        log.setLevel(logging.DEBUG)
    elif incoming_args.quiet:
        log.setLevel(logging.WARNING)
    else:
        log.setLevel(logging.INFO)

    start = timeit.default_timer()
    # num_procs: int = os.cpu_count()
    num_procs: int = 6

    result: bool = main(incoming_args, num_procs)

    end = timeit.default_timer()
    elapsed: float = end - start
    hours, remainder = divmod(elapsed, 60 * 60)
    minutes, seconds = divmod(remainder, 60)
    log.info(
        f"Total time to run: {int(hours):02}:{int(minutes):02}:{round(seconds):02} (Total: {elapsed}s)"
    )
