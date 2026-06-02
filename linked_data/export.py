import argparse
import asyncio
import json
import logging.config
import sqlite3
import sys
import timeit
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parent.parent))

import aiosqlite
import orjson
import rdflib
import yaml
from pyreqwest.client import Client, ClientBuilder
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
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

with open(SCRIPT_DIR / "logging.yml") as lg:
    log_config: dict[str, Any] = yaml.safe_load(lg)
logging.config.dictConfig(log_config)
log = logging.getLogger("ld_export")

# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------
with open(PROJECT_ROOT / "configuration.yml") as cf:
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
translations: dict = load_translations(str(PROJECT_ROOT / "locales")) or {}
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

RECORD_TYPES: list[str] = list(serializer_map.keys())


def to_ntriples(data: dict[str, Any]) -> str:
    json_serialized: str = orjson.dumps(data).decode("utf-8")
    graph_object: rdflib.Graph = rdflib.Graph().parse(
        data=json_serialized, format="application/ld+json"
    )
    ntrips = graph_object.serialize(format="nt")
    return ntrips.decode("utf-8") if isinstance(ntrips, (bytes, bytearray)) else ntrips


def _is_transient_error(stage: str, err: Exception) -> bool:
    if isinstance(err, (asyncio.TimeoutError, TimeoutError, ConnectionError)):
        return True
    if stage in {"serialize", "db"} and isinstance(err, OSError):
        return True
    if stage == "db" and isinstance(err, sqlite3.OperationalError):
        return True
    msg = str(err).lower()
    return any(
        hint in msg
        for hint in ("timeout", "temporar", "connection reset", "connection refused")
    )


def _failure_payload(
    doc_id: Any,
    doc_type: Any,
    stage: str,
    attempts: int,
    err: Exception,
) -> dict[str, Any]:
    return {
        "id": doc_id,
        "type": doc_type,
        "stage": stage,
        "attempts": attempts,
        "error_class": err.__class__.__name__,
        "error_message": str(err),
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def _write_failure_report_line(report_file: Any, payload: dict[str, Any]) -> None:
    report_file.write(json.dumps(payload, ensure_ascii=False))
    report_file.write("\n")


async def run_serializer_from_doc(
    this_doc: dict[str, Any],
    serializer_cls: Any,
    ctx_val: dict[str, Any],
    session: Client,
    sqlconn: aiosqlite.Connection,
    db_lock: asyncio.Lock,
    max_retries: int,
    retry_backoff_ms: int,
) -> dict[str, Any]:
    if not this_doc:
        payload = {
            "id": None,
            "type": None,
            "stage": "input",
            "attempts": 0,
            "error_class": "ValueError",
            "error_message": "Empty source document",
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
        return {"ok": False, "attempts": 0, "failure": payload}
    doc_id = this_doc.get("id")
    doc_type = this_doc.get("type")

    attempts = 0
    backoff_seconds = max(retry_backoff_ms, 0) / 1000.0

    while attempts <= max_retries:
        attempts += 1
        try:
            serialized = await serializer_cls(
                this_doc,
                context={"request": req, "direct_request": True, "client": session},
            ).serialized
        except Exception as e:
            log.exception("Serializer failed for %s on attempt %s", doc_id, attempts)
            if _is_transient_error("serialize", e) and attempts <= max_retries:
                await asyncio.sleep(backoff_seconds * (2 ** (attempts - 1)))
                continue
            return {
                "ok": False,
                "attempts": attempts,
                "failure": _failure_payload(doc_id, doc_type, "serialize", attempts, e),
            }

        try:
            doc = {"@context": ctx_val["@context"], **serialized}
            ntrips: str = to_ntriples(doc)
            if not ntrips:
                raise ValueError("No N-Triples output")
        except Exception as e:
            log.exception(
                "N-Triples conversion failed for %s on attempt %s", doc_id, attempts
            )
            if _is_transient_error("convert", e) and attempts <= max_retries:
                await asyncio.sleep(backoff_seconds * (2 ** (attempts - 1)))
                continue
            return {
                "ok": False,
                "attempts": attempts,
                "failure": _failure_payload(doc_id, doc_type, "convert", attempts, e),
            }

        try:
            async with db_lock:
                await sqlconn.execute(
                    "INSERT OR REPLACE INTO serialized VALUES (?, ?, ?)",
                    (doc_id, doc_type, ntrips),
                )
        except Exception as e:
            log.exception(
                "Database write failed for %s on attempt %s", doc_id, attempts
            )
            if _is_transient_error("db", e) and attempts <= max_retries:
                await asyncio.sleep(backoff_seconds * (2 ** (attempts - 1)))
                continue
            return {
                "ok": False,
                "attempts": attempts,
                "failure": _failure_payload(doc_id, doc_type, "db", attempts, e),
            }

        return {"ok": True, "attempts": attempts}

    unexpected = RuntimeError("Retry loop exhausted without result")
    return {
        "ok": False,
        "attempts": attempts,
        "failure": _failure_payload(doc_id, doc_type, "unknown", attempts, unexpected),
    }


JSON_FIELD_SUFFIX = "_json"
JSON_MULTI_FIELD_SUFFIX = "_jsonm"
JSON_FIELD_SUFFIXES = (JSON_FIELD_SUFFIX, JSON_MULTI_FIELD_SUFFIX)


def _expand_json_fields(doc: dict[str, Any]) -> dict[str, Any]:
    expanded_fields: dict[str, Any] | None = None

    for key, value in doc.items():
        if not key.endswith(JSON_FIELD_SUFFIXES):
            continue

        val = _parse_json_field(key, value)
        if val is None:
            continue

        if expanded_fields is None:
            expanded_fields = {}
        expanded_fields[key] = val

    if expanded_fields is None:
        return doc

    return {**doc, **expanded_fields}


def _parse_json_field(field_name: str, field_value: Any) -> Any | None:
    if field_value is None:
        return None

    if field_name.endswith(JSON_MULTI_FIELD_SUFFIX):
        return _parse_json_multi_field(field_name, field_value)

    if not isinstance(field_value, str | bytes | bytearray):
        log.error("Field '%s' must be a JSON string before expansion.", field_name)
        return None

    try:
        return orjson.loads(field_value)
    except orjson.JSONDecodeError:
        log.error("Field '%s' contains invalid JSON.", field_name)
        return None


def _parse_json_multi_field(field_name: str, field_value: Any) -> list[Any] | None:
    if not isinstance(field_value, list):
        log.error("Field '%s' must be a list before expansion.", field_name)
        return None

    expanded_values: list[Any] = []
    for item in field_value:
        if not isinstance(item, str | bytes | bytearray):
            log.error("Field '%s' contains a non-JSON string value.", field_name)
            return None
        try:
            expanded_values.append(orjson.loads(item))
        except orjson.JSONDecodeError:
            log.error("Field '%s' contains invalid JSON.", field_name)
            return None

    return expanded_values


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
        expanded_doc = _expand_json_fields(sdoc)
        yield (
            expanded_doc,
            res,
        )  # res carries .hits if you want to log totals at the end


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
    output_path: Path,
    max_retries: int,
    retry_backoff_ms: int,
    commit_every: int,
    failure_report_prefix: str,
) -> dict[str, int]:
    """
    Performs a single paginated search via the client's cursor and serializes each document.
    Returns summary counts.
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
        return {"seen": 0, "succeeded": 0, "failed": 0, "retried": 0}

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
        commit_every = max(commit_every, 1)
        report_path = output_path / f"{failure_report_prefix}_{record_type}.jsonl"

        # HTTP client for any downstream network I/O in serializers
        client_builder = (
            ClientBuilder()
            .max_connections(8)
            .pool_max_idle_per_host(4)
            .pool_idle_timeout(timedelta(seconds=30))
            .timeout(timedelta(seconds=20))
            .connect_timeout(timedelta(seconds=10))
            .read_timeout(timedelta(seconds=20))
        )

        start_time = timeit.default_timer()
        last_log_time = start_time
        last_count = 0

        async with client_builder.build() as session:
            sem = asyncio.Semaphore(concurrency)
            in_flight: set[asyncio.Task] = set()
            seen = 0
            succeeded = 0
            failed = 0
            retried = 0
            since_commit = 0

            async def run_one(doc: dict[str, Any]) -> dict[str, Any]:
                async with sem:
                    return await run_serializer_from_doc(
                        doc,
                        serializer_cls,
                        ctx_val,
                        session,
                        sqlconn,
                        db_lock,
                        max_retries=max_retries,
                        retry_backoff_ms=retry_backoff_ms,
                    )

            def consume_result(result: dict[str, Any], report_file: Any) -> None:
                nonlocal succeeded, failed, retried, since_commit
                attempts = int(result.get("attempts", 0))
                if attempts > 1:
                    retried += attempts - 1
                if result.get("ok"):
                    succeeded += 1
                    since_commit += 1
                    return
                failed += 1
                failure = result.get("failure")
                if isinstance(failure, dict):
                    _write_failure_report_line(report_file, failure)

            # Single Solr cursor stream
            res_last = None
            with open(report_path, "w", encoding="utf-8") as report_file:
                try:
                    async for doc, res in stream_solr_docs_for_type(
                        solr_conn, record_type, country_code, page_size
                    ):
                        res_last = res
                        seen += 1

                        # ---- rate logging every 60s (or every 1000 docs, whichever comes first)
                        now = timeit.default_timer()
                        if (now - last_log_time) >= 60 or (seen - last_count) >= 1000:
                            elapsed = now - start_time
                            per_min = seen / (elapsed / 60) if elapsed else 0
                            pending = max(seen - (succeeded + failed), 0)
                            log.info(
                                "[%s] Progress: seen=%d success=%d failed=%d pending=%d retried=%d | %.1f docs/min | elapsed %.1f min",
                                record_type,
                                seen,
                                succeeded,
                                failed,
                                pending,
                                retried,
                                per_min,
                                elapsed / 60,
                            )
                            last_log_time = now
                            last_count = seen
                        # ----------------------------------------------------------

                        t = asyncio.create_task(run_one(doc))
                        in_flight.add(t)

                        if len(in_flight) >= concurrency:
                            done, in_flight = await asyncio.wait(
                                in_flight, return_when=asyncio.FIRST_COMPLETED
                            )
                            for finished in done:
                                try:
                                    consume_result(finished.result(), report_file)
                                except Exception as e:
                                    failed += 1
                                    payload = _failure_payload(
                                        None, record_type, "task", 1, e
                                    )
                                    _write_failure_report_line(report_file, payload)
                            if since_commit >= commit_every:
                                async with db_lock:
                                    await sqlconn.commit()
                                since_commit = 0
                except Exception:
                    log.exception(
                        "Cursor stream failed for record type %s; finishing in-flight tasks",
                        record_type,
                    )

                if in_flight:
                    done, _ = await asyncio.wait(in_flight)
                    for finished in done:
                        try:
                            consume_result(finished.result(), report_file)
                        except Exception as e:
                            failed += 1
                            payload = _failure_payload(None, record_type, "task", 1, e)
                            _write_failure_report_line(report_file, payload)

            async with db_lock:
                await sqlconn.commit()

    # Log total hits if available
    if res_last is not None and getattr(res_last, "hits", None) is not None:
        log.info(
            "Completed %s export: seen=%s success=%s failed=%s retried=%s (Solr hits reported: %s)",
            record_type,
            seen,
            succeeded,
            failed,
            retried,
            res_last.hits,  # type: ignore[attr-defined]
        )
    else:
        log.info(
            "Completed %s export: seen=%s success=%s failed=%s retried=%s",
            record_type,
            seen,
            succeeded,
            failed,
            retried,
        )

    return {
        "seen": seen,
        "succeeded": succeeded,
        "failed": failed,
        "retried": retried,
    }


# -------------------------------------------------------------------
# Orchestration (no multiprocessing; one cursor per type)
# -------------------------------------------------------------------
def dump_nt_from_db(db_path: Path, nt_path: Path) -> None:
    log.info("Writing N-Triples output to %s", str(nt_path))
    with (
        sqlite3.connect(str(db_path)) as db,
        open(nt_path, "w", encoding="utf-8") as nt_out,
    ):
        for (ttl,) in db.execute("SELECT ttl FROM serialized ORDER BY id"):
            if ttl:
                nt_out.write(ttl)
                if not ttl.endswith("\n"):
                    nt_out.write("\n")


def main(args: argparse.Namespace) -> bool:
    types_to_serialize: list[str] = RECORD_TYPES if not args.include else args.include

    output_path: Path = args.output
    output_path.mkdir(parents=True, exist_ok=True)

    # Optional cleanup
    if args.empty:
        for rec_type in types_to_serialize:
            nt_path = Path(args.output, f"{rec_type}.nt")
            db_file = Path(args.output, f"{rec_type}.db")
            failure_report = Path(
                args.output, f"{args.failure_report_prefix}_{rec_type}.jsonl"
            )
            if nt_path.exists():
                log.info("Removing %s", str(nt_path))
                nt_path.unlink(missing_ok=True)
            if db_file.exists():
                log.info("Removing %s", str(db_file))
                db_file.unlink(missing_ok=True)
            if failure_report.exists():
                log.info("Removing %s", str(failure_report))
                failure_report.unlink(missing_ok=True)

    async def run_all() -> None:
        solr_conn = Solr(SOLR_SERVER)

        for rec_type in types_to_serialize:
            log.info("Running serialization for %s", rec_type)

            db_file_path = Path(args.output, f"{rec_type}.db")
            db_name = str(db_file_path)

            start_serialize = timeit.default_timer()
            stats = await process_record_type(
                solr_conn=solr_conn,
                record_type=rec_type,
                country_code=args.country,
                dbname=db_name,
                concurrency=args.concurrency,
                page_size=args.page_size,
                output_path=output_path,
                max_retries=args.max_retries,
                retry_backoff_ms=args.retry_backoff_ms,
                commit_every=args.commit_every,
                failure_report_prefix=args.failure_report_prefix,
            )
            elapsed = timeit.default_timer() - start_serialize
            rate = (stats["seen"] / elapsed) if elapsed else 0.0
            log.info(
                "Total time to serialize %s: %.3fs | seen=%d success=%d failed=%d retried=%d | rate=%.2f docs/s",
                rec_type,
                elapsed,
                stats["seen"],
                stats["succeeded"],
                stats["failed"],
                stats["retried"],
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
        choices=RECORD_TYPES,
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
    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="Maximum retries for transient per-record failures.",
    )
    parser.add_argument(
        "--retry-backoff-ms",
        type=int,
        default=500,
        help="Base backoff in milliseconds for retries.",
    )
    parser.add_argument(
        "--commit-every",
        type=int,
        default=500,
        help="Commit SQLite after this many successful inserts.",
    )
    parser.add_argument(
        "--failure-report-prefix",
        default="failed_records",
        help="Filename prefix for per-type JSONL failure reports.",
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
