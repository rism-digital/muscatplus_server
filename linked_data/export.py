import argparse
import asyncio
import logging.config
import shutil
import timeit
from pathlib import Path

import aiofiles
import rdflib
import uvloop
from orjson import orjson
from sanic.compat import Header
from sanic.models.protocol_types import TransportProtocol
from sanic.request import Request
from small_asc.client import Solr
from alive_progress import alive_bar

from search_server.resources.institutions.institution import Institution
from search_server.resources.people.person import Person
from search_server.resources.sources.full_source import FullSource
from search_server.server import app
from shared_helpers.jsonld import RISM_JSONLD_SOURCE_CONTEXT, RISM_JSONLD_PERSON_CONTEXT, RISM_JSONLD_DEFAULT_CONTEXT
from shared_helpers.languages import load_translations, filter_languages

# Prevent other loggers from logging
logging.config.dictConfig({'disable_existing_loggers': True, 'version': 1})
log = logging.getLogger("ld_export")
log.setLevel(logging.INFO)


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


def to_turtle(data: dict) -> str:
    log.debug("Creating graph from data")
    # json_serialized: str = orjson.dumps(data).decode("utf8")
    json_serialized: str = orjson.dumps(data)
    graph_object: rdflib.Graph = rdflib.Graph().parse(data=json_serialized, format="application/ld+json")
    turtle: str = graph_object.serialize(format="turtle")

    return turtle


# Mock route for the request
class Route:
    def __init__(self):
        self.name = ""


async def main(args: argparse.Namespace) -> bool:
    log.debug("Starting export")
    start = timeit.default_timer()

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

    # Fake a sanic request object. We patch a bunch of things to the request to add exactly what the request
    # needs to serialize the output. This includes the URL, of which the path part gets ignored -- the important
    # bit is in the headers!
    req = Request(bytes("/foo", "ascii"), headers, "", "GET", TransportProtocol(), app)
    req.ctx.translations = filt_translations
    req.route = route

    if args.empty:
        log.info("Emptying output directory %s", args.output)
        shutil.rmtree(args.output)

    num_records: int = 0
    outp: bool = True
    inc: list
    if not args.include:
        inc = ["sources", "institutions", "people"]
    else:
        inc = args.include

    log.debug("Processing record types: %s", inc)

    for resource_type in inc:
        log.info("Processing %s", resource_type)
        if resource_type in args.exclude:
            continue

        if resource_type == "institutions":
            record_type = "institution"
            ctx = RISM_JSONLD_DEFAULT_CONTEXT
            serializer = Institution
        elif resource_type == "people":
            record_type = "person"
            ctx = RISM_JSONLD_PERSON_CONTEXT
            serializer = Person
        elif resource_type == "sources":
            record_type = "source"
            ctx = RISM_JSONLD_SOURCE_CONTEXT
            serializer = FullSource
        else:
            log.debug("Could not determine serializer, so we are skipping resource type %s", resource_type)
            continue

        s = Solr("http://localhost:8983/solr/muscatplus_live")
        fq = [f"type:{record_type}"]

        if args.country_code and resource_type == "sources":
            log.info("Restricting to country %s", args.country_code)
            fq.append(f"country_code_s:{args.country_code}")
        elif args.country_code and resource_type == "institutions":
            fq.append(f"country_codes_sm:{args.country_code}")

        sort = "id asc"
        res = await s.search({"query": "*:*", "filter": fq, "sort": sort, "limit": 500}, cursor=True)
        num_records += res.hits
        ctx_val = {"@context": ctx}

        with alive_bar(res.hits, title=f"Exporting {resource_type}", title_length=25) as bar:
            async for sdoc in res:
                sid = sdoc['rism_id']
                serialized = await serializer(sdoc, context={"request": req,
                                                             "direct_request": True}).data

                # Add the context value to the resulting dictionary so that we can serialize it
                serialized.update(ctx_val)

                # Writes the output to a balanced directory structure, so that no single directory has too many
                # files. Uses the last three digits of the
                balanced_dir: str = f"{sid[-3:]:>03}"
                outpath: Path = Path(args.output, f"{resource_type}", balanced_dir)
                if not outpath.exists():
                    outpath.mkdir(parents=True)

                turtle: str = await asyncio.get_running_loop().run_in_executor(None, to_turtle, serialized)

                async with aiofiles.open(str(Path(outpath, f"{sid}.ttl")), mode="w") as ttlout:
                    await ttlout.write(turtle)

                bar()

        elapsed_for_resource_type: float = timeit.default_timer() - start
        log.info(f"Processing rate for {resource_type}: {res.hits / elapsed_for_resource_type} docs/s")
        outp |= True

    end = timeit.default_timer()
    elapsed: float = end - start

    hours, remainder = divmod(elapsed, 60 * 60)
    minutes, seconds = divmod(remainder, 60)
    log.info(f"Total time to download: {int(hours):02}:{int(minutes):02}:{round(seconds):02} (Total: {elapsed}s)")
    log.info(f"Total processing rate: {num_records / elapsed} docs/s")

    return outp

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", "-o", default="../ttl", type=Path, help="Where to write the output. Default is '../ttl'. ")
    parser.add_argument("--empty", "-m", action="store_true")
    parser.add_argument("--country-code", "-c")
    parser.add_argument("--include", "-i", action="extend", nargs="*", default=[])
    parser.add_argument("--exclude", "-e", action="extend", nargs="*", default=[])
    parser.add_argument("--base-uri", "-u", default="rism.online")

    input_args: argparse.Namespace = parser.parse_args()

    asyncio.run(main(input_args))
