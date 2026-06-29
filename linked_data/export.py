import argparse
import asyncio
import logging.config
import multiprocessing as mp
import queue
import secrets
import sys
import timeit
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parent.parent))

import orjson
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
    RISM_JSONLD_PLACE_CONTEXT,
    RISM_JSONLD_PUBLICATION_CONTEXT,
    RISM_JSONLD_SOURCE_CONTEXT,
    RISM_JSONLD_WORK_CONTEXT,
)
from search_server.helpers.languages import filter_languages, load_translations
from search_server.helpers.linked_data import (
    to_ntriples as to_ntriples_pyoxigraph,
    to_turtle as to_turtle_pyoxigraph,
)
from search_server.resources.institutions.institution import Institution
from search_server.resources.people.person import Person
from search_server.resources.places.place import Place
from search_server.resources.publications.publication import Publication
from search_server.resources.sources.full_source import FullSource
from search_server.resources.works.full_work import FullWork
from search_server.server import app

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

with open(SCRIPT_DIR / "logging.yml") as lg:
    log_config: dict[str, Any] = yaml.safe_load(lg)
logging.config.dictConfig(log_config)
log = logging.getLogger("ld_export")

with open(PROJECT_ROOT / "configuration.yml") as cf:
    config: dict[str, Any] = yaml.safe_load(cf)

SOLR_SERVER: str = config["solr"]["server"]


class MockRoute:
    def __init__(self) -> None:
        self.name = ""


headers: Header = Header(
    {
        "X-Forwarded-Proto": "https",
        "X-Forwarded-Host": "rism.online",
    }
)
translations: dict = load_translations(str(PROJECT_ROOT / "locales")) or {}
filt_translations: dict = filter_languages(
    {"en", "fr", "de", "it", "pl", "pt", "es"}, translations
)

req = Request(bytes("/foo", "ascii"), headers, "", "GET", TransportProtocol(), app)
req.ctx.translations = filt_translations
req.route = MockRoute()  # type: ignore

serializer_map: dict[str, Any] = {
    "source": FullSource,
    "person": Person,
    "institution": Institution,
    "work": FullWork,
    "publication": Publication,
    "place": Place,
}

CONTEXTS: dict[str, Any] = {
    "source": RISM_JSONLD_SOURCE_CONTEXT,
    "person": RISM_JSONLD_PERSON_CONTEXT,
    "institution": RISM_JSONLD_INSTITUTION_CONTEXT,
    "work": RISM_JSONLD_WORK_CONTEXT,
    "publication": RISM_JSONLD_PUBLICATION_CONTEXT,
    "place": RISM_JSONLD_PLACE_CONTEXT,
}

RECORD_TYPES: list[str] = list(serializer_map.keys())
DEFAULT_SOLR_SORT = "id asc"
RANDOM_SEED_MAX = 2**31 - 1

JSON_FIELD_SUFFIX = "_json"
JSON_MULTI_FIELD_SUFFIX = "_jsonm"
JSON_FIELD_SUFFIXES = (JSON_FIELD_SUFFIX, JSON_MULTI_FIELD_SUFFIX)
OUTPUT_FORMATS = ("nt", "ttl")


@dataclass
class StageTimings:
    json_expand_seconds: float = 0.0
    serialize_seconds: float = 0.0
    convert_seconds: float = 0.0
    write_seconds: float = 0.0


@dataclass
class WorkerManifest:
    record_type: str
    worker_id: int
    shard_tmp_path: str
    shard_path: str
    failure_report_path: str
    records_seen: int
    records_succeeded: int
    records_failed: int
    elapsed_seconds: float
    docs_per_second: float
    timings: dict[str, float]
    completed: bool


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def failure_payload(
    doc_id: Any,
    doc_type: Any,
    stage: str,
    err: Exception,
    worker_id: int | None = None,
) -> dict[str, Any]:
    return {
        "id": doc_id,
        "type": doc_type,
        "stage": stage,
        "worker_id": worker_id,
        "error_class": err.__class__.__name__,
        "error_message": str(err),
        "timestamp": utc_timestamp(),
    }


def expand_json_fields(doc: dict[str, Any]) -> tuple[dict[str, Any], float]:
    expand_started_at = timeit.default_timer()
    expanded_fields: dict[str, Any] | None = None

    for key, value in doc.items():
        if not key.endswith(JSON_FIELD_SUFFIXES):
            continue

        val = parse_json_field(key, value)
        if val is None:
            continue

        if expanded_fields is None:
            expanded_fields = {}
        expanded_fields[key] = val

    expand_elapsed_seconds = timeit.default_timer() - expand_started_at
    if expanded_fields is None:
        return doc, expand_elapsed_seconds
    return {**doc, **expanded_fields}, expand_elapsed_seconds


def parse_json_field(field_name: str, field_value: Any) -> Any | None:
    if field_value is None:
        return None

    if field_name.endswith(JSON_MULTI_FIELD_SUFFIX):
        return parse_json_multi_field(field_name, field_value)

    if not isinstance(field_value, str | bytes | bytearray):
        log.error("Field '%s' must be a JSON string before expansion.", field_name)
        return None

    try:
        return orjson.loads(field_value)
    except orjson.JSONDecodeError:
        log.error("Field '%s' contains invalid JSON.", field_name)
        return None


def parse_json_multi_field(field_name: str, field_value: Any) -> list[Any] | None:
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


def shard_extension(output_format: str) -> str:
    if output_format not in OUTPUT_FORMATS:
        raise ValueError(f"Unsupported RDF output format: {output_format}")
    return output_format


def shard_tmp_path(
    output_path: Path, record_type: str, worker_id: int, output_format: str
) -> Path:
    extension = shard_extension(output_format)
    return output_path / record_type / f"part-{worker_id:05d}.{extension}.tmp"


def shard_final_path(
    output_path: Path, record_type: str, worker_id: int, output_format: str
) -> Path:
    extension = shard_extension(output_format)
    return output_path / record_type / f"part-{worker_id:05d}.{extension}"


def failure_report_path(output_path: Path, record_type: str, worker_id: int) -> Path:
    return output_path / record_type / f"failed-records-{worker_id:05d}.jsonl"


def record_type_context(record_type: str) -> dict[str, Any]:
    return {"@context": CONTEXTS.get(record_type, RISM_JSONLD_DEFAULT_CONTEXT)}


async def serialize_doc(
    doc: dict[str, Any],
    serializer_cls: Any,
    ctx_val: dict[str, Any],
    session: Client,
    output_format: str,
) -> tuple[str, StageTimings]:
    timings = StageTimings()

    expanded_doc, timings.json_expand_seconds = expand_json_fields(doc)

    serialize_started_at = timeit.default_timer()
    serialized = await serializer_cls(
        expanded_doc,
        context={"request": req, "direct_request": True, "client": session},
    ).serialized
    timings.serialize_seconds = timeit.default_timer() - serialize_started_at

    convert_started_at = timeit.default_timer()
    payload = {"@context": ctx_val["@context"], **serialized}
    if output_format == "nt":
        rdf_output = to_ntriples_pyoxigraph(payload)
    elif output_format == "ttl":
        rdf_output = to_turtle_pyoxigraph(payload)
    else:
        raise ValueError(f"Unsupported RDF output format: {output_format}")
    timings.convert_seconds = timeit.default_timer() - convert_started_at

    if not rdf_output:
        format_name = "Turtle" if output_format == "ttl" else "N-Triples"
        raise ValueError(f"No {format_name} output")

    return rdf_output, timings


async def run_worker_async(
    worker_id: int,
    record_type: str,
    input_queue: mp.Queue,
    result_queue: mp.Queue,
    output_path: Path,
    concurrency: int,
    flush_every: int,
    output_format: str,
) -> None:
    serializer_cls = serializer_map[record_type]
    ctx_val = record_type_context(record_type)
    tmp_path = shard_tmp_path(output_path, record_type, worker_id, output_format)
    final_path = shard_final_path(output_path, record_type, worker_id, output_format)
    failures_path = failure_report_path(output_path, record_type, worker_id)

    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    if tmp_path.exists():
        tmp_path.unlink()
    if final_path.exists():
        final_path.unlink()
    if failures_path.exists():
        failures_path.unlink()

    start_time = timeit.default_timer()
    seen = 0
    succeeded = 0
    failed = 0
    since_flush = 0
    timings = StageTimings()

    async with (
        ClientBuilder()
        .max_connections(max(concurrency, 1))
        .pool_max_idle_per_host(max(concurrency, 1))
        .pool_idle_timeout(timedelta(seconds=30))
        .timeout(timedelta(seconds=20))
        .connect_timeout(timedelta(seconds=10))
        .read_timeout(timedelta(seconds=20))
        .build()
    ) as session:
        sem = asyncio.Semaphore(max(concurrency, 1))
        pending: set[asyncio.Task] = set()

        async def process_one(
            doc: dict[str, Any],
        ) -> tuple[str, StageTimings, dict[str, Any] | None]:
            async with sem:
                try:
                    rdf_output, doc_timings = await serialize_doc(
                        doc, serializer_cls, ctx_val, session, output_format
                    )
                    return rdf_output, doc_timings, None
                except Exception as err:
                    payload = failure_payload(
                        doc.get("id"),
                        doc.get("type"),
                        "serialize",
                        err,
                        worker_id=worker_id,
                    )
                    return "", StageTimings(), payload

        async def drain_completed(
            tasks: Iterable[asyncio.Task],
            rdf_out: Any,
            failure_out: Any,
        ) -> None:
            nonlocal succeeded, failed, since_flush, timings
            for task in tasks:
                rdf_output, doc_timings, failure = task.result()
                if failure:
                    failed += 1
                    failure_out.write(orjson.dumps(failure).decode("utf-8"))
                    failure_out.write("\n")
                    continue

                write_start = timeit.default_timer()
                rdf_out.write(rdf_output)
                if not rdf_output.endswith("\n"):
                    rdf_out.write("\n")
                timings.write_seconds += timeit.default_timer() - write_start

                timings.json_expand_seconds += doc_timings.json_expand_seconds
                timings.serialize_seconds += doc_timings.serialize_seconds
                timings.convert_seconds += doc_timings.convert_seconds
                succeeded += 1
                since_flush += 1

                if since_flush >= flush_every:
                    rdf_out.flush()
                    failure_out.flush()
                    since_flush = 0

        with (
            open(tmp_path, "w", encoding="utf-8") as rdf_out,
            open(failures_path, "w", encoding="utf-8") as failure_out,
        ):
            while True:
                batch = await asyncio.to_thread(input_queue.get)
                if batch is None:
                    break

                for doc in batch:
                    seen += 1
                    pending.add(asyncio.create_task(process_one(doc)))

                    if len(pending) >= concurrency:
                        done, pending = await asyncio.wait(
                            pending, return_when=asyncio.FIRST_COMPLETED
                        )
                        await drain_completed(done, rdf_out, failure_out)

            if pending:
                done, _ = await asyncio.wait(pending)
                await drain_completed(done, rdf_out, failure_out)

            rdf_out.flush()
            failure_out.flush()

    tmp_path.replace(final_path)

    worker_elapsed_seconds = timeit.default_timer() - start_time
    manifest = WorkerManifest(
        record_type=record_type,
        worker_id=worker_id,
        shard_tmp_path=str(tmp_path),
        shard_path=str(final_path),
        failure_report_path=str(failures_path),
        records_seen=seen,
        records_succeeded=succeeded,
        records_failed=failed,
        elapsed_seconds=worker_elapsed_seconds,
        docs_per_second=seen / worker_elapsed_seconds
        if worker_elapsed_seconds
        else 0.0,
        timings=asdict(timings),
        completed=True,
    )
    result_queue.put(asdict(manifest))


def worker_entrypoint(
    worker_id: int,
    record_type: str,
    input_queue: mp.Queue,
    result_queue: mp.Queue,
    output_path: str,
    concurrency: int,
    flush_every: int,
    output_format: str,
) -> None:
    try:
        asyncio.run(
            run_worker_async(
                worker_id=worker_id,
                record_type=record_type,
                input_queue=input_queue,
                result_queue=result_queue,
                output_path=Path(output_path),
                concurrency=concurrency,
                flush_every=flush_every,
                output_format=output_format,
            )
        )
    except Exception as err:
        result_queue.put(
            {
                "record_type": record_type,
                "worker_id": worker_id,
                "completed": False,
                "error": failure_payload(None, record_type, "worker", err, worker_id),
            }
        )


def generate_random_seed() -> int:
    return secrets.randbelow(RANDOM_SEED_MAX) + 1


def solr_sort(randomize: bool, random_seed: int | None) -> str:
    if not randomize:
        return DEFAULT_SOLR_SORT
    if random_seed is None:
        raise ValueError("Random Solr sort requires a random seed")
    return f"random_{random_seed} asc,id asc"


def solr_request_limit(page_size: int, limit: int | None) -> int:
    if limit is not None:
        return min(page_size, limit)
    return page_size


async def stream_solr_docs_for_type(
    solr_conn: Solr,
    record_type: str,
    country_code: str | None,
    page_size: int,
    limit: int | None = None,
    randomize: bool = False,
    random_seed: int | None = None,
):
    fq = [f"type:{record_type}", "!project_s:[* TO *]"]
    if record_type == "source" and country_code:
        fq.append(f"country_codes_sm:{country_code.upper()}")

    sort = solr_sort(randomize, random_seed)
    params: JsonAPIRequest = {
        "query": "*:*",
        "filter": fq,
        "sort": sort,
        "limit": solr_request_limit(page_size, limit),
    }
    log.info("Solr query for %s using sort %s", record_type, sort)
    res = await solr_conn.search(params, cursor=True)
    log.info("Solr query for %s received %s results", record_type, res.hits)
    yielded = 0
    async for sdoc in res:
        if limit is not None and yielded >= limit:
            break
        yielded += 1
        yield sdoc


async def export_record_type(
    record_type: str,
    output_path: Path,
    country_code: str | None,
    workers: int,
    page_size: int,
    batch_size: int,
    worker_concurrency: int,
    flush_every: int,
    limit: int | None,
    randomize: bool,
    random_seed: int | None,
    output_format: str,
) -> list[dict[str, Any]]:
    if record_type not in serializer_map:
        raise ValueError(f"Unsupported record type: {record_type}")

    ctx = mp.get_context("spawn")
    result_queue = ctx.Queue()
    worker_queues = [ctx.Queue(maxsize=4) for _ in range(workers)]
    processes = [
        ctx.Process(
            target=worker_entrypoint,
            args=(
                worker_id,
                record_type,
                worker_queues[worker_id],
                result_queue,
                str(output_path),
                worker_concurrency,
                flush_every,
                output_format,
            ),
        )
        for worker_id in range(workers)
    ]

    for process in processes:
        process.start()

    solr_conn = Solr(SOLR_SERVER)
    batches: list[list[dict[str, Any]]] = [[] for _ in range(workers)]
    seen = 0
    record_type_started_at = timeit.default_timer()

    try:
        async for doc in stream_solr_docs_for_type(
            solr_conn,
            record_type,
            country_code,
            page_size,
            limit,
            randomize=randomize,
            random_seed=random_seed,
        ):
            worker_id = seen % workers
            batches[worker_id].append(doc)
            seen += 1

            if len(batches[worker_id]) >= batch_size:
                worker_queues[worker_id].put(batches[worker_id])
                batches[worker_id] = []

            if seen % 10000 == 0:
                queue_elapsed_seconds = timeit.default_timer() - record_type_started_at
                log.info(
                    "[%s] queued=%d | %.2f docs/s",
                    record_type,
                    seen,
                    seen / queue_elapsed_seconds if queue_elapsed_seconds else 0.0,
                )
    finally:
        for worker_id, batch in enumerate(batches):
            if batch:
                worker_queues[worker_id].put(batch)
        for worker_queue in worker_queues:
            worker_queue.put(None)

    manifests = []
    for _ in processes:
        try:
            manifests.append(result_queue.get(timeout=60 * 60))
        except queue.Empty as err:
            raise TimeoutError("Timed out waiting for exporter worker") from err

    for process in processes:
        process.join()
        if process.exitcode != 0:
            raise RuntimeError(
                f"Worker process {process.pid} exited with {process.exitcode}"
            )

    record_type_elapsed_seconds = timeit.default_timer() - record_type_started_at
    log.info(
        "Completed %s queueing/export: queued=%d elapsed=%.2fs rate=%.2f docs/s",
        record_type,
        seen,
        record_type_elapsed_seconds,
        seen / record_type_elapsed_seconds if record_type_elapsed_seconds else 0.0,
    )
    return manifests


def write_manifest(output_path: Path, manifests: list[dict[str, Any]]) -> None:
    output_path.mkdir(parents=True, exist_ok=True)
    manifest_path = output_path / "manifest.json"
    payload = {
        "created": utc_timestamp(),
        "manifests": manifests,
        "totals": {
            "records_seen": sum(int(m.get("records_seen", 0)) for m in manifests),
            "records_succeeded": sum(
                int(m.get("records_succeeded", 0)) for m in manifests
            ),
            "records_failed": sum(int(m.get("records_failed", 0)) for m in manifests),
        },
    }
    manifest_path.write_text(
        orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode("utf-8"),
        encoding="utf-8",
    )


def clean_output_for_types(
    output_path: Path, record_types: Iterable[str], output_format: str
) -> None:
    extension = shard_extension(output_format)
    for record_type in record_types:
        record_dir = output_path / record_type
        if not record_dir.exists():
            continue
        for path in record_dir.glob(f"part-*.{extension}*"):
            path.unlink()
        for path in record_dir.glob("failed-records-*.jsonl"):
            path.unlink()


def main(args: argparse.Namespace) -> bool:
    output_path: Path = args.output
    output_path.mkdir(parents=True, exist_ok=True)
    record_types = RECORD_TYPES if not args.include else args.include
    random_seed = generate_random_seed() if args.random else None

    if args.empty:
        clean_output_for_types(output_path, record_types, args.format)

    all_manifests: list[dict[str, Any]] = []

    async def run_all() -> None:
        for record_type in record_types:
            log.info("Starting %s export with %d workers", record_type, args.workers)
            manifests = await export_record_type(
                record_type=record_type,
                output_path=output_path,
                country_code=args.country,
                workers=args.workers,
                page_size=args.page_size,
                batch_size=args.batch_size,
                worker_concurrency=args.worker_concurrency,
                flush_every=args.flush_every,
                limit=args.limit,
                randomize=args.random,
                random_seed=random_seed,
                output_format=args.format,
            )
            all_manifests.extend(manifests)
            write_manifest(output_path, all_manifests)

    asyncio.run(run_all())
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-o", "--output", default="../ttl-new", type=Path, help="Output directory"
    )
    parser.add_argument(
        "-e",
        "--empty",
        dest="empty",
        action="store_true",
        help="Empty generated shard files before starting",
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
    parser.add_argument("--workers", type=int, default=4, help="Worker processes")
    parser.add_argument(
        "--worker-concurrency",
        type=int,
        default=4,
        help="Concurrent serializer tasks inside each worker process",
    )
    parser.add_argument("--page-size", type=int, default=1000, help="Solr page size")
    parser.add_argument(
        "--limit",
        type=int,
        help="Stop after this many Solr documents per record type.",
    )
    parser.add_argument(
        "--random",
        action="store_true",
        help="Sort each Solr record-type query in random order before applying --limit.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of Solr documents sent to a worker at a time",
    )
    parser.add_argument(
        "--flush-every",
        type=int,
        default=500,
        help="Flush shard and failure files after this many successful writes",
    )
    parser.add_argument(
        "--profile-export",
        action="store_true",
        help="Reserved for compatibility; profile timings are always written to the manifest.",
    )
    parser.add_argument(
        "--format",
        choices=OUTPUT_FORMATS,
        default="nt",
        help="RDF output format for exported shards.",
    )
    return parser


if __name__ == "__main__":
    parser = build_parser()

    incoming_args = parser.parse_args()

    if incoming_args.verbose:
        log.setLevel(logging.DEBUG)
    elif incoming_args.quiet:
        log.setLevel(logging.WARNING)
    else:
        log.setLevel(logging.INFO)

    script_started_at = timeit.default_timer()
    main(incoming_args)
    script_elapsed_seconds = timeit.default_timer() - script_started_at
    hours, remainder = divmod(script_elapsed_seconds, 60 * 60)
    minutes, seconds = divmod(remainder, 60)
    log.info(
        "Total time to run: %02d:%02d:%02d (Total: %.3fs)",
        int(hours),
        int(minutes),
        round(seconds),
        script_elapsed_seconds,
    )
