import sys

sys.path.append("./")

import argparse
import asyncio
import logging
import logging.config
import sqlite3
import timeit
from pathlib import Path
from typing import Any

import aiosqlite
import httpx
import orjson
import rdflib
import yaml
from sanic import Request
from sanic.compat import Header
from sanic.models.protocol_types import TransportProtocol
from small_asc.client import JsonAPIRequest, Solr

from search_server.helpers.jsonld import (
    RISM_JSONLD_DEFAULT_CONTEXT,
    RISM_JSONLD_INSTITUTION_CONTEXT,
    RISM_JSONLD_PERSON_CONTEXT,
    RISM_JSONLD_PUBLICATION_CONTEXT,
    RISM_JSONLD_SOURCE_CONTEXT,
    RISM_JSONLD_WORK_CONTEXT,
)
from search_server.helpers.languages import filter_languages, load_translations
from search_server.resources.institutions.institution import Institution
from search_server.resources.people.person import Person
from search_server.resources.publications.publication import Publication
from search_server.resources.sources.full_source import FullSource
from search_server.resources.works.full_work import FullWork
from search_server.server import app

# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
with open("linked_data/logging.yml") as lg:
    log_config: dict[str, Any] = yaml.safe_load(lg)
logging.config.dictConfig(log_config)
log = logging.getLogger("ld_export")

# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------
with open("configuration.yml") as cf:
    config: dict[str, Any] = yaml.safe_load(cf)

SOLR_SERVER: str = config["solr"]["server"]


# -------------------------------------------------------------------
# Minimal request stub for serializers (exposes .app and common attrs)
# -------------------------------------------------------------------
class MockRoute:
    def __init__(self) -> None:
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
translations: dict = load_translations("locales/") or {}
filt_translations: dict = filter_languages({"en"}, translations)

req = Request(bytes("/foo", "ascii"), headers, "", "GET", TransportProtocol(), app)
req.ctx.translations = filt_translations
req.route = MockRoute()  # type: ignore


# -------------------------------------------------------------------
# Serialization helpers
# -------------------------------------------------------------------
serializer_map: dict[str, Any] = {
    "source": FullSource,
    "person": Person,
    "institution": Institution,
    "work": FullWork,
    "publication": Publication,
}

CONTEXTS: dict[str, Any] = {
    "source": RISM_JSONLD_SOURCE_CONTEXT,
    "person": RISM_JSONLD_PERSON_CONTEXT,
    "institution": RISM_JSONLD_INSTITUTION_CONTEXT,
    "work": RISM_JSONLD_WORK_CONTEXT,
    "publication": RISM_JSONLD_PUBLICATION_CONTEXT,
}


def to_ntriples(data: dict[str, Any]) -> str:
    json_serialized: str = orjson.dumps(data).decode("utf-8")
    graph_object: rdflib.Graph = rdflib.Graph().parse(
        data=json_serialized, format="application/ld+json"
    )
    ntrips = graph_object.serialize(format="nt")
    return ntrips.decode("utf-8") if isinstance(ntrips, (bytes, bytearray)) else ntrips


async def run_serializer_from_doc(
    this_doc: dict[str, Any],
    serializer_cls,
    ctx_val: dict[str, Any],
    session: httpx.AsyncClient,
    sqlconn: aiosqlite.Connection,
    db_lock: asyncio.Lock,
) -> None:
    if not this_doc:
        return
    try:
        serialized = await serializer_cls(
            this_doc,
            context={"request": req, "direct_request": True, "client": session},
        ).serialized
    except Exception as e:
        log.critical("=========== Serializer failed for %s: %s", this_doc.get("id"), e)
        return

    doc = {"@context": ctx_val["@context"], **serialized}
    ntrips: str = to_ntriples(doc)
    if not ntrips:
        log.critical("No N-Triples for %s", this_doc.get("id"))
        return

    async with db_lock:
        await sqlconn.execute(
            "INSERT OR REPLACE INTO serialized VALUES (?, ?, ?)",
            (this_doc.get("id"), this_doc.get("type"), ntrips),
        )


# -------------------------------------------------------------------
# Solr streaming: single paginated search per record type
# -------------------------------------------------------------------
async def stream_solr_docs_for_type(
    solr_conn: Solr, record_type: str, country_code: str | None, page_size: int
):
    """
    Async generator that yields full documents for a given record type using a Solr cursor.
    Assumes the client handles cursor paging when cursor=True.
    """
    fq = [f"type:{record_type}", "!project_s:[* TO *]"]
    if record_type == "source" and country_code:
        fq.append(f"country_codes_sm:{country_code.upper()}")

    params: JsonAPIRequest = {
        "query": "*:*",
        "filter": fq,
        # "fields": ["*"],  # request full docs so serializers don't need per-id fetch
        "sort": "id asc",
        "limit": page_size,  # cursor page size
    }
    res = await solr_conn.search(params, cursor=True)
    log.info("Solr query received %s results", res.hits)
    async for sdoc in res:
        log.debug("Processing solr document")
        yield sdoc, res  # res carries .hits if you want to log totals at the end


# -------------------------------------------------------------------
# Main async pipeline for one record type
# -------------------------------------------------------------------
async def process_record_type(
    solr_conn: Solr,
    record_type: str,
    country_code: str | None,
    dbname: str,
    concurrency: int,
    page_size: int,
) -> int:
    """
    Performs a single paginated search via the client's cursor and serializes each document.
    Returns count of processed docs.
    """
    ctx_val = {"@context": CONTEXTS.get(record_type, RISM_JSONLD_DEFAULT_CONTEXT)}
    serializer_cls = serializer_map.get(record_type)

    # If you have a Publication serializer, add it to serializer_map instead of this fallback.
    if record_type == "publication" and serializer_cls is None:
        log.warning(
            "No explicit serializer for 'publication'; using FullWork as a fallback."
        )
        serializer_cls = FullWork

    if not serializer_cls:
        log.critical("No serializer class for %s", record_type)
        return 0

    # DB connection (async)
    async with aiosqlite.connect(dbname) as sqlconn:
        await sqlconn.executescript(
            """
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=NORMAL;
            CREATE TABLE IF NOT EXISTS serialized(
                id   TEXT PRIMARY KEY,
                type TEXT,
                ttl  TEXT
            );
            """
        )
        db_lock = asyncio.Lock()

        # HTTP client for any downstream network I/O in serializers
        limits = httpx.Limits(
            max_connections=8, max_keepalive_connections=4, keepalive_expiry=30.0
        )
        timeout = httpx.Timeout(20.0, connect=10.0, read=20.0, write=20.0)

        start_time = timeit.default_timer()
        last_log_time = start_time
        last_count = 0

        async with httpx.AsyncClient(limits=limits, timeout=timeout) as session:
            sem = asyncio.Semaphore(concurrency)
            in_flight: set[asyncio.Task] = set()
            processed = 0

            # Single Solr cursor stream
            res_last = None
            async for doc, res in stream_solr_docs_for_type(
                solr_conn, record_type, country_code, page_size
            ):
                res_last = res
                processed += 1

                # ---- rate logging every 60s (or every 1000 docs, whichever comes first)
                now = timeit.default_timer()
                if (now - last_log_time) >= 60 or (processed - last_count) >= 1000:
                    elapsed = now - start_time
                    per_min = processed / (elapsed / 60) if elapsed else 0
                    log.info(
                        "[%s] Progress: %d docs processed | %.1f docs/min | elapsed %.1f min",
                        record_type,
                        processed,
                        per_min,
                        elapsed / 60,
                    )
                    last_log_time = now
                    last_count = processed
                # ----------------------------------------------------------

                await sem.acquire()
                t = asyncio.create_task(
                    run_serializer_from_doc(
                        doc, serializer_cls, ctx_val, session, sqlconn, db_lock
                    )
                )
                in_flight.add(t)
                t.add_done_callback(lambda _t: (sem.release(), in_flight.discard(_t)))

                # Drain periodically to surface exceptions
                if len(in_flight) >= concurrency:
                    done, in_flight = await asyncio.wait(
                        in_flight, return_when=asyncio.FIRST_COMPLETED
                    )

            # Drain remaining tasks
            if in_flight:
                await asyncio.gather(*in_flight, return_exceptions=True)

        await sqlconn.commit()

    # Log total hits if available
    if res_last is not None and getattr(res_last, "hits", None) is not None:
        log.info(
            "Processed %s documents for %s (Solr hits reported: %s)",
            processed,
            record_type,
            res_last.hits,  # type: ignore[attr-defined]
        )
    else:
        log.info("Processed %s documents for %s", processed, record_type)

    return processed


# -------------------------------------------------------------------
# Orchestration (no multiprocessing; one cursor per type)
# -------------------------------------------------------------------
def dump_nt_from_db(db_path: Path, nt_path: Path) -> None:
    log.info("Writing N-Triples output to %s", str(nt_path))
    with (
        sqlite3.connect(str(db_path)) as db,
        open(nt_path, "w", encoding="utf-8") as nt_out,
    ):
        for (ttl,) in db.execute("SELECT ttl FROM serialized"):
            if ttl:
                nt_out.write(ttl)
                if not ttl.endswith("\n"):
                    nt_out.write("\n")


def main(args: argparse.Namespace) -> bool:
    types_to_serialize: list[str] = (
        ["source", "person", "institution", "work", "publication"]
        if not args.include
        else args.include
    )

    output_path: Path = args.output
    output_path.mkdir(parents=True, exist_ok=True)

    # Optional cleanup
    if args.empty:
        for rec_type in types_to_serialize:
            nt_path = Path(args.output, f"{rec_type}.nt")
            db_file = Path(args.output, f"{rec_type}.db")
            if nt_path.exists():
                log.info("Removing %s", str(nt_path))
                nt_path.unlink(missing_ok=True)
            if db_file.exists():
                log.info("Removing %s", str(db_file))
                db_file.unlink(missing_ok=True)

    async def run_all() -> None:
        solr_conn = Solr(SOLR_SERVER)

        for rec_type in types_to_serialize:
            log.info("Running single-cursor serialization for %s", rec_type)

            db_file = Path(args.output, f"{rec_type}.db")
            db_name = str(db_file)

            start_serialize = timeit.default_timer()
            processed = await process_record_type(
                solr_conn=solr_conn,
                record_type=rec_type,
                country_code=args.country,
                dbname=db_name,
                concurrency=args.concurrency,
                page_size=args.page_size,
            )
            elapsed = timeit.default_timer() - start_serialize
            rate = (processed / elapsed) if elapsed else 0.0
            log.info(
                "Total time to serialize %s: %.3fs  |  processed=%d  |  rate=%.2f docs/s",
                rec_type,
                elapsed,
                processed,
                rate,
            )

            # Dump N-Triples to per-type file
            nt_path = Path(args.output, f"{rec_type}.nt")
            dump_nt_from_db(db_file, nt_path)

    asyncio.run(run_all())
    return True


# -------------------------------------------------------------------
# CLI
# -------------------------------------------------------------------
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
    parser.add_argument(
        "--include",
        nargs="*",
        choices=["source", "person", "institution", "work", "publication"],
        help="Limit to specific record types",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=8,
        help="Max concurrent serializer tasks (affects CPU/DB only; Solr is single-cursor).",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=500,
        help="Solr cursor page size (number of docs per page).",
    )

    incoming_args = parser.parse_args()

    if incoming_args.verbose:
        log.setLevel(logging.DEBUG)
    elif incoming_args.quiet:
        log.setLevel(logging.WARNING)
    else:
        log.setLevel(logging.INFO)

    start = timeit.default_timer()
    result: bool = main(incoming_args)
    elapsed = timeit.default_timer() - start

    hours, remainder = divmod(elapsed, 60 * 60)
    minutes, seconds = divmod(remainder, 60)
    log.info(
        "Total time to run: %02d:%02d:%02d (Total: %.3fs)",
        int(hours),
        int(minutes),
        round(seconds),
        elapsed,
    )
