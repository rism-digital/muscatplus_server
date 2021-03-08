import re
from typing import Pattern, Dict, Union, Optional

ID_SUB: Pattern = re.compile(r"source_|person_|holding_|institution_|subject_|related_")

EXTERNAL_IDS: Dict = {
    "viaf": "https://viaf.org/viaf/{ident}",
    "dnb": "http://d-nb.info/gnd/{ident}",
    "wkp": "https://www.wikidata.org/wiki/{ident}",
    "isil": "https://ld.zdb-services.de/resource/organisations/{ident}"
}


def get_identifier(request: "sanic.request.Request", viewname: str, **kwargs) -> str:
    """
    Takes a request object, parses it out, and returns a templated identifier suitable
    for use in an "id" field, including the incoming request information on host and scheme (http/https).

    :param request: A Sanic request object
    :param viewname: A string of the view for which we will retrieve the URL. Matches the function name in server.py.
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
    "cre": "records.composer_author",  # A special case, where the cre relator code is used to label the 100 main entry field.
    "dpt": "records.depositor",
    "lyr": "records.lyricist",
    "fmo": "records.former_owner",
    "scr": "records.copyist",
    "arr": "records.arranger",
    "edt": "records.editor",
    "dte": "records.dedicatee",
    "pbl": "records.publisher",
    "cmp": "records.composer",
    "oth": "records.other",
    "prf": "records.performer"
}

QUALIFIER_LABELS = {
    None: "records.unknown",
    "Ascertained": "records.ascertained",
    "Verified": "records.verified",
    "Conjectural": "records.conjectural",
    "Alleged": "records.alleged",
    "Doubtful": "records.doubtful",
    "Misattributed": "records.misattributed"
}

# A type that represents the fact that the JSON-LD context can be given either by URI or an embedded context object.
JSONLDContext = Union[str, Dict]


def get_jsonld_context(request) -> JSONLDContext:
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
    "@context": {
        "@version": 1.1,
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rism": "https://rism.online/api/v1#",
        "rismdata": "https://rism.online/api/datatypes-v1#",
        "relators": "http://id.loc.gov/vocabulary/relators/",
        "dcterms": "http://purl.org/dc/terms/",
        "as": "http://www.w3.org/ns/activitystreams#",
        "hydra": "http://www.w3.org/ns/hydra/core#",
        "geojson": "https://purl.org/geojson/vocab#",
        "type": "@type",
        "id": "@id",
        "none": "@none",
        "rism:SourceRelationship": {
            "@id": "rism:SourceRelationship",

        },
        "label": {
            "@id": "rdfs:label",
            "@container": [
                "@language",
                "@set"
            ]
        },
        "roleLabel": {
            "@id": "rdfs:label",
            "@container": [
                "@language",
                "@set"
            ]
        },
        "qualifier": {
            "@id": "rismdata",
            "@type": "@id"
        },
        "qualifierLabel": {
            "@id": "rdf:label",
            "@container": [
                "@language",
                "@set"
            ]
        },
        "value": {
            "@id": "rdf:value",
            "@container": [
                "@language",
                "@set"
            ]
        },
        "partOf": {
            "@id": "dcterms:isPartOf",
            "@type": "@id",
            "@container": "@set"
        },
        "summary": {
            "@type": "@id",
            "@id": "rism:Summary"
        },
        "creator": {
            "@id": "rism:SourceRelationship",
            "@type": "@id",
            "@context": {
                "role": {
                    "@id": "relators",
                    "@type": "@id"
                },
                "relatedTo": {
                    "@type": "@id",
                    "@id": "dcterms:creator"
                }
            }
        },
        "related": {
            "@id": "rism:RelationshipList",
            "@type": "@id",
            "@context": {
                "items": {
                    "@container": "@list",
                    "@id": "rism:SourceRelationship",
                    "@type": "@id",
                    "@context": {
                        "role": {
                            "@id": "relators",
                            "@type": "@id"
                        },
                        "relatedTo": {
                            "@type": "@id",
                            "@id": "dcterms:contributor"
                        }
                    }
                }
            }
        },
        "items": {
            "@type": "@id",
            "@id": "as:items",
            "@container": "@list"
        },
        "relatedTo": {
            "@type": "@id",
            "@id": "dcterms:contributor"
        },
        "location": {
            "@id": "rism:location",
            "@context": {
                "coordinates": {
                    "@container": "@list",
                    "@id": "geojson:coordinates"
                }
            }
        }
    }
}
