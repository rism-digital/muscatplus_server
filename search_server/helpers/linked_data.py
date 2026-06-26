from typing import Any

import orjson
from pyoxigraph import DefaultGraph, NamedNode, Quad, RdfFormat, parse, serialize
from pyprttl import PrttlError, format_turtle
from sanic.log import logger

from search_server.helpers.identifiers import RISM_RELATIONSHIP_BASE

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
    "rismrel": RISM_RELATIONSHIP_BASE,
    "schemaorg": "https://schema.org/",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
}

RISM_RELATIONSHIPS = NamedNode("https://rism.online/api/v1#relationships")
RISM_HAS_RELATIONSHIP = NamedNode("https://rism.online/api/v1#hasRelationship")
RISM_HAS_ROLE = NamedNode("https://rism.online/api/v1#hasRole")
DCTERMS_RELATION = NamedNode("http://purl.org/dc/terms/relation")


def _materialize_relationship_predicates(quads: set[Quad]) -> set[Quad]:
    # Preserve the existing n-ary relationship section model and also derive
    # direct subject-predicate-object triples from relationship statements so
    # RDF consumers can query either form.
    subject_by_section: dict[object, set[NamedNode]] = {}
    statement_by_section: dict[object, set[object]] = {}
    role_by_statement: dict[object, set[NamedNode]] = {}
    object_by_statement: dict[object, set[NamedNode]] = {}

    for quad in quads:
        if quad.predicate == RISM_RELATIONSHIPS and isinstance(quad.subject, NamedNode):
            subject_by_section.setdefault(quad.object, set()).add(quad.subject)
        elif quad.predicate == RISM_HAS_RELATIONSHIP:
            statement_by_section.setdefault(quad.subject, set()).add(quad.object)
        elif quad.predicate == RISM_HAS_ROLE and isinstance(quad.object, NamedNode):
            role_by_statement.setdefault(quad.subject, set()).add(quad.object)
        elif quad.predicate == DCTERMS_RELATION and isinstance(quad.object, NamedNode):
            object_by_statement.setdefault(quad.subject, set()).add(quad.object)

    if not subject_by_section:
        return quads

    derived_quads: set[Quad] = set()
    default_graph = DefaultGraph()

    for section, subjects in subject_by_section.items():
        statements = statement_by_section.get(section)
        if not statements:
            continue

        for statement in statements:
            roles = role_by_statement.get(statement)
            objects = object_by_statement.get(statement)
            if not roles or not objects:
                continue

            for subject in subjects:
                for role in roles:
                    for obj in objects:
                        derived_quads.add(Quad(subject, role, obj, default_graph))

    return quads | derived_quads


def _parse_jsonld(data: dict[str, Any]):
    """
    Parse JSON-LD into deduplicated RDF quads.

    PyOxigraph streams parsed quads and may surface duplicate quads from repeated
    JSON-LD values. Returning a set keeps output graph semantics stable across
    Turtle, JSON-LD, and N-Triples serialization.
    """
    json_serialized = orjson.dumps(data)
    raw_quads = set(
        parse(
            input=json_serialized,
            format=RdfFormat.JSON_LD,
            without_named_graphs=True,
            lenient=True,
        )
    )
    return _materialize_relationship_predicates(raw_quads)


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
    except BaseException:
        logger.exception("Turtle pretty-printing panicked; returning raw Turtle output")
        return turtle


def to_expanded_jsonld(data: dict[str, Any]) -> str:
    return _serialize(data, RdfFormat.JSON_LD) or ""


def to_ntriples(data: dict[str, Any]) -> str:
    return _serialize(data, RdfFormat.N_TRIPLES) or ""
