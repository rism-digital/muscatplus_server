from typing import Optional
import logging
import rdflib
import ujson

from shared_helpers.identifiers import RISM_JSONLD_CONTEXT

log = logging.getLogger(__name__)


def _to_graph_object(data: dict) -> rdflib.Graph:
    """
    Takes a serialized JSON-LD object and runs it through rdflib to produce an abstract graph. This can
    then be sent to different format serializers for returning the data via a request. Applies the namespaces
    defined in the JSON-LD context to the graph so that it can properly namespace all the prefixed strings.

    :param data: A dictionary coming from one of the JSON-LD serializers
    :return: An rdflib.Graph object.
    """
    json_serialized: str = ujson.dumps(data)
    g = rdflib.Graph().parse(data=json_serialized, format="json-ld")

    for pfx in ["rdf", "rdfs", "rism", "rismdata", "relators", "dcterms", "as", "hydra", "geojson", "schemaorg", "pmo"]:
        ns: Optional[str] = RISM_JSONLD_CONTEXT["@context"].get(pfx)
        if not ns:
            continue
        g.namespace_manager.bind(pfx, rdflib.URIRef(ns))

    return g


def to_turtle(data: dict) -> str:
    graph_object: rdflib.Graph = _to_graph_object(data)
    turtle: str = graph_object.serialize(format="turtle")

    return turtle


def to_expanded_jsonld(data: dict) -> str:
    graph_object: rdflib.Graph = _to_graph_object(data)
    expanded_ld: str = graph_object.serialize(format="json-ld")

    return expanded_ld
