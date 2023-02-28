import logging

import orjson
import rdflib

log = logging.getLogger("mp_server")


def _to_graph_object(data: dict) -> rdflib.Graph:
    """
    Takes a serialized JSON-LD object and runs it through rdflib to produce an abstract graph. This can
    then be sent to different format serializers for returning the data via a request. Applies the namespaces
    defined in the JSON-LD context to the graph so that it can properly namespace all the prefixed strings.

    :param data: A dictionary coming from one of the JSON-LD serializers
    :return: An rdflib.Graph object.
    """
    json_serialized: str = orjson.dumps(data).decode("utf8")
    g = rdflib.Graph().parse(data=json_serialized, format="application/ld+json")

    return g


def to_turtle(data: dict) -> str:
    log.debug("Creating graph from data")
    graph_object: rdflib.Graph = _to_graph_object(data)
    log.debug("Created graph object")
    turtle: str = graph_object.serialize(format="turtle")

    return turtle


def to_expanded_jsonld(data: dict) -> str:
    graph_object: rdflib.Graph = _to_graph_object(data)
    expanded_ld: str = graph_object.serialize(format="json-ld")

    return expanded_ld
