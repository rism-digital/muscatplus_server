from typing import Optional
import logging
from pyld import jsonld
import rdflib

from search_server.helpers.identifiers import RISM_JSONLD_CONTEXT

log = logging.getLogger(__name__)


def to_turtle(data: dict) -> str:
    rdf: str = to_rdf(data)
    g = rdflib.Graph()
    for pfx in ["rdf", "rdfs", "rism", "rismdata", "relators", "dcterms", "as", "hydra", "geojson"]:
        ns: Optional[str] = RISM_JSONLD_CONTEXT["@context"].get(pfx)
        if not ns:
            continue
        g.namespace_manager.bind(pfx, rdflib.URIRef(ns))

    g.parse(data=rdf, format="nquads")
    turtle: str = g.serialize(format="turtle").decode("utf-8")
    log.debug("Returning Turtle!")
    return turtle


def to_rdf(data: dict) -> str:
    log.debug("Creating RDF!")
    del data["@context"]
    rdf: str = jsonld.to_rdf(data, options={"format": "application/n-quads",
                                            "expandContext": RISM_JSONLD_CONTEXT})
    log.debug("Returning RDF!")

    return rdf
