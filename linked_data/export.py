import argparse
import asyncio
import concurrent.futures
import logging.config
import os
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
from shared_helpers.jsonld import RISM_JSONLD_SOURCE_CONTEXT
from shared_helpers.languages import load_translations, filter_languages

logging.config.dictConfig({'disable_existing_loggers': True, 'version': 1})
log = logging.getLogger("ld_export")

config: dict = yaml.safe_load(open('configuration.yml', 'r'))
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
headers: Header = Header({
    "X-Forwarded-Proto": "https",
    "X-Forwarded-Host": "rism.online",
})
translations: dict = load_translations("locales/")
filt_translations: dict = filter_languages({"en"}, translations)

route = Route()

req = Request(bytes("/foo", "ascii"), headers, "", "GET", TransportProtocol(), app)
req.ctx.translations = filt_translations
req.route = route

record_type_map: dict = {
    "source": "sources",
    "person": "people",
    "institution": "institutions"
}

serializer_map: dict = {
    "source": FullSource,
    "person": Person,
    "institution": Institution
}


def to_turtle(data: dict) -> str:
    json_serialized: str = orjson.dumps(data)
    graph_object: rdflib.Graph = rdflib.Graph().parse(data=json_serialized, format="application/ld+json")
    turtle: str = graph_object.serialize(format="turtle")

    return turtle


async def create_id_groups(num_groups: int, record_type: str) -> list:
    log.debug("Creating ID groups")
    fq = [f"type:{record_type}"]
    fl = ["id"]

    res = await solr_conn.search({"query": "*:*", "filter": fq, "fields": fl, "sort": "id asc", "limit": 1000},
                                 cursor=True)
    log.debug("Gathering groups")
    id_list: list = [sdoc["id"] async for sdoc in res]

    log.debug("Gathering done, found %s total IDs", res.hits)
    split_groups: list = [id_list[g::num_groups] for g in range(num_groups)]

    log.debug("Created %s groups, first has %s IDs, last has %s IDs",
              len(split_groups),
              len(split_groups[0]),
              len(split_groups[-1]))

    return split_groups


async def run_serializer(docid: str, serializer, ctx_val: dict, table_name: str, semaphore, session, sqlconn):
    async with semaphore:
        log.debug("Serializing %s", docid)
        this_doc = await solr_conn.get(docid)
        if this_doc is None:
            log.error("No document for %s", docid)

        serialized = await serializer(this_doc, context={"request": req,
                                                         "direct_request": True,
                                                         "session": session}).data
        serialized.update(ctx_val)
        sid = this_doc['rism_id']
        turtle: str = to_turtle(serialized)
        insert_stmt: str = f"INSERT INTO {table_name} VALUES (?, ?)"
        sqlconn.execute(insert_stmt, (sid, turtle))
        sqlconn.commit()
        await asyncio.sleep(0.1)


async def serialize(id_group: list, record_type: str, semaphore, dbname: str) -> None:
    log.debug("Actually serializing! Processing %s IDs", len(id_group))
    ctx_val = {"@context": RISM_JSONLD_SOURCE_CONTEXT}
    tasks = set()
    sqlconn = sqlite3.connect(dbname)

    table_name: Optional[str] = record_type_map.get(record_type)
    if not table_name:
        log.critical("Unknown record type %s. Could not proceed.", record_type)
        return None

    # Yeah, yeah, I know. Format strings for SQL statements...
    sql_stmt: str = f"CREATE TABLE {table_name}(rism_id TEXT PRIMARY KEY, ttl TEXT)"
    sqlconn.execute(sql_stmt)

    serializer = serializer_map.get(record_type)
    if not serializer:
        log.critical("There was a problem retrieving the serializer class for %s", record_type)
        return None

    async with aiohttp.ClientSession(json_serialize=lambda x: orjson.dumps(x).decode("utf-8")) as session:
        for docid in id_group:
            task = asyncio.create_task(run_serializer(docid, serializer, ctx_val, table_name, semaphore, session, sqlconn))
            tasks.add(task)
            task.add_done_callback(tasks.discard)

        _ = await asyncio.wait(tasks)

    sqlconn.close()


def do_serialize(id_group: list, resource_type: str, dbname: str):
    num_async_procs: int = 100
    semaphore = asyncio.Semaphore(num_async_procs)
    asyncio.run(serialize(id_group, resource_type, semaphore, dbname))


def main(args: argparse.Namespace):
    types_to_serialize: list
    if not args.include:
        types_to_serialize = ["source", "person", "institution"]
    else:
        types_to_serialize = args.include

    output_path: Path = args.output
    output_path.mkdir(parents=True, exist_ok=True)

    parallel_processes: int = os.cpu_count()
    log.info(f"Running with {parallel_processes} processes")

    for rec_type in types_to_serialize:
        id_groups: list = asyncio.run(create_id_groups(parallel_processes, rec_type))
        log.debug("Got %s id groups, for %s parallel processes", len(id_groups), parallel_processes)
        num_results: int = sum([len(x) for x in id_groups])
        start_serialize = timeit.default_timer()

        futures = []
        with concurrent.futures.ProcessPoolExecutor(parallel_processes) as executor:
            for i in range(parallel_processes):
                db_file = Path(args.output, f"output_{i}.db")
                if args.empty:
                    log.info("Removing %s", str(db_file))
                    db_file.unlink(missing_ok=True)

                db_name = str(db_file)
                new_future = executor.submit(do_serialize, id_groups[i], rec_type, db_name)
                futures.append(new_future)

        for f in concurrent.futures.as_completed(futures):
            f.result()

        end_serialize = timeit.default_timer()
        s_elapsed: float = end_serialize - start_serialize
        s_hours, s_remainder = divmod(s_elapsed, 60 * 60)
        s_minutes, s_seconds = divmod(s_remainder, 60)
        log.info(f"Total time to serialize {rec_type}: {int(s_hours):02}:{int(s_minutes):02}:{round(s_seconds):02} (Total: {s_elapsed}s)")
        log.info(f"Total processing rate: {num_results / s_elapsed} docs/s")

    for i in range(parallel_processes):
        db_name = Path(args.output, f"output_{i}.db")

        for rec_type in types_to_serialize:
            ttl_path = Path(args.output, f"output_{rec_type}_{i}.ttl")
            if args.empty:
                log.info("Removing %s", str(ttl_path))
                ttl_path.unlink(missing_ok=True)

            with open(ttl_path, "w") as ttl_out:
                log.info("Writing TTL output to %s", str(ttl_path))
                table_name = record_type_map.get(rec_type)
                if not table_name:
                    log.error("Bad record type %s", rec_type)
                    continue

                sql_stmt = f"SELECT ttl FROM {table_name}"

                subprocess.run(["sqlite3", str(db_name), sql_stmt],
                               stdout=ttl_out)

    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", default="../ttl", type=Path)
    parser.add_argument("-e", "--empty", dest="empty", action="store_true",
                        help="Empty the output directory before starting")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output (log level DEBUG)")
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet output (log level WARNING)")
    parser.add_argument("--include", action="extend", nargs="*")

    incoming_args = parser.parse_args()

    if incoming_args.verbose:
        log.setLevel(logging.DEBUG)
    elif incoming_args.quiet:
        log.setLevel(logging.WARNING)
    else:
        log.setLevel(logging.INFO)

    start = timeit.default_timer()

    result: bool = main(incoming_args)

    end = timeit.default_timer()
    elapsed: float = end - start
    hours, remainder = divmod(elapsed, 60 * 60)
    minutes, seconds = divmod(remainder, 60)
    log.info(f"Total time to run: {int(hours):02}:{int(minutes):02}:{round(seconds):02} (Total: {elapsed}s)")