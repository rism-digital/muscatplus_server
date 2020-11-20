import re
from typing import Pattern, Dict, Union

ID_SUB: Pattern = re.compile(r"source_|person_|holding_|institution_|subject_")

EXTERNAL_IDS: Dict = {
    "viaf": "https://viaf.org/viaf/{ident}",
    "dnb": "http://d-nb.info/gnd/{ident}",
    "wkp": "https://www.wikidata.org/wiki/{ident}"
}


def get_identifier(request: "sanic.request.Request", viewname: str, **kwargs) -> str:
    """
    Takes a request object, parses it out, and returns a templated identifier suitable
    for use in an "id" field, including the incoming request information on host and scheme (http/https).

    :param request: A Sanic request object
    :param template: A string containing formatting variables
    :param kwargs: A set of keywords matching the template formatting variables
    :return: A templated string
    """
    fwd_scheme_header = request.headers.get('X-Forwarded-Proto')
    fwd_host_header = request.headers.get('X-Forwarded-Host')

    scheme: str = fwd_scheme_header if fwd_scheme_header else request.scheme
    server: str = fwd_host_header if fwd_host_header else request.host

    return request.app.url_for(viewname, _external=True, _scheme=scheme, _server=server, **kwargs)


# Map between relator codes and the chosen translation string for that relator.
RELATIONSHIP_LABELS = {
    None: "records.unknown",
    "lyr": "records.lyricist",
    "fmo": "records.former_owner",
    "scr": "records.scribe",
    "arr": "records.arranger",
    "edt": "records.editor"
}


def get_jsonld_context(request) -> Union[str, Dict]:
    """
    Returns the configured JSON-LD context string. If the `context_uri` setting is
    set to True in the server configuration file, this will return the URI for the
    "context" handler. If it is set to False, it will return the full JSON-LD Context
    object inline.

    :param request: A Sanic request object, with the 'app.context_uri' setting added to it during applicaton startup.
    :return: Either a string representing the URI to the context object, or the context object itself as a Dictionary.
    """
    if request.app.context_uri:
        return get_identifier(request, "context")

    return RISM_JSONLD_CONTEXT


RISM_JSONLD_CONTEXT: Dict = {
    "@version": 1.1,
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rism": "https://rism.online/api/v1#",
    "rismdata": "https://rism.online/api/datatypes-v1#",
    "relators": "http://id.loc.gov/vocabulary/relators/",
    "dcterms": "http://purl.org/dc/terms/",
    "as": "http://www.w3.org/ns/activitystreams#",
    "hydra": "http://www.w3.org/ns/hydra/core#",
    "type": "@type",
    "id": "@id",
    "PartialCollectionView": "hydra:PartialCollectionView",
    "Collection": "hydra:Collection",
    "totalItems": "hydra:totalItems",
    "member": "hydra:member",
    "view": "hydra:view",
    "next": "hydra:next",
    "previous": "hydra:previous",
    "first": "hydra:first",
    "last": "hydra:last",

    "name": {
        "@id": "rdfs:label",
        "@container": [
            "@language",
            "@set"
        ],
        "@context": {
            "none": "@none"
        }
    },
    "seeAlso": {
        "@type": "@id",
        "@id": "rdfs:seeAlso",
        "@container": "@set"
    },
    "partOf": {
        "@id": "dcterms:partOf",
        "@type": "@id",
        "@container": "@set"
    },
    "profile": {
        "@type": "@vocab",
        "@id": "dcterms:conformsTo"
    },
    "musicIncipit": {
        "@id": "rdf:value",
        "@type": "rismdata:pae"  # a custom datatype IRI may not be recognized by some processors.
    },
    "textIncipit": {
        "@id": "rdf:value"
    },
    "items": {
        "@type": "@id",
        "@id": "as:items",
        "@container": "@list"
    }
}
