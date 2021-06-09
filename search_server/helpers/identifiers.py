import re
from typing import Pattern, Dict

ID_SUB: Pattern = re.compile(r"source_|person_|holding_|institution_|subject_|related_|place_|festival_")

EXTERNAL_IDS: Dict = {
    "viaf": {"label": "Virtual Internet Authority File (VIAF)", "ident": "https://viaf.org/viaf/{ident}"},
    "dnb": {"label": "Deutsche Nationalbibliothek (GND)", "ident": "http://d-nb.info/gnd/{ident}"},
    "wkp": {"label": "Wikidata", "ident": "https://www.wikidata.org/wiki/{ident}"},
    "isil": {"label": "International Standard Identifier for Libraries and Related Organizations (ISIL)",
             "ident": "https://ld.zdb-services.de/resource/organisations/{ident}"},
    "bne": {"label": "Biblioteca Nacional de España", "ident": "{ident}"},
    "bnf": {"label": "Bibliothèque Nationale de France", "ident": "{ident}"},
    "iccu": {"label": "Istituto Centrale per il Catalogo Unico", "ident": "{ident}"},
    "isni": {"label": "International Standard Name Identifier", "ident": "{ident}"},
    "lc": {"label": "Library of Congress", "ident": "{ident}"},
    "nlp": {"label": "Biblioteka Narodowa", "ident": "{ident}"},
    "nkc": {"label": "Národní knihovna České republiky", "ident": "{ident}"},
    "swnl": {"label": "Schweizerische Nationalbibliothek", "ident": "{ident}"},
    "moc": {"label": "MARC Organization Code", "ident": "{ident}"},
    "orcid": {"label": "Open Researcher and Contributor ID (ORCiD)", "ident": "https://orcid.org/{ident}"},
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
