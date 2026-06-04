from typing import Any

import orjson
from pyoxigraph import RdfFormat, parse, serialize
from pyprttl import PrttlError, format_turtle
from sanic.log import logger

TURTLE_PREFIXES = {
    "dcterms": "http://purl.org/dc/terms/",
    "geo": "http://www.w3.org/2003/01/geo/wgs84_pos#",
    "geojson": "https://purl.org/geojson/vocab#",
    "pmo": "http://performedmusicontology.org/ontology/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdau": "http://rdaregistry.info/Elements/u/",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "relators": "http://id.loc.gov/vocabulary/relators/",
    "rism": "https://rism.online/api/v1#",
    "schemaorg": "https://schema.org/",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
}


def _parse_jsonld(data: dict[str, Any]):
    """
    Parse JSON-LD into deduplicated RDF quads.

    PyOxigraph streams parsed quads and may surface duplicate quads from repeated
    JSON-LD values. Returning a set keeps output graph semantics stable across
    Turtle, JSON-LD, and N-Triples serialization.
    """
    json_serialized = orjson.dumps(data)
    return set(
        parse(
            input=json_serialized,
            format=RdfFormat.JSON_LD,
            without_named_graphs=True,
            lenient=True,
        )
    )


def _serialize(data: dict[str, Any], rdf_format: RdfFormat) -> str | None:
    logger.debug("Creating RDF output from JSON-LD")
    prefixes = TURTLE_PREFIXES if rdf_format == RdfFormat.TURTLE else None
    output = serialize(_parse_jsonld(data), format=rdf_format, prefixes=prefixes)
    return output.decode("utf-8") if isinstance(output, bytes | bytearray) else output


def to_turtle(data: dict[str, Any]) -> str | None:
    turtle = _serialize(data, RdfFormat.TURTLE)
    try:
        return format_turtle(turtle)
    except PrttlError:
        logger.exception("Turtle pretty-printing failed; returning raw Turtle output")
        return turtle


def to_expanded_jsonld(data: dict[str, Any]) -> str:
    return _serialize(data, RdfFormat.JSON_LD) or ""


def to_ntriples(data: dict[str, Any]) -> str:
    return _serialize(data, RdfFormat.N_TRIPLES) or ""
