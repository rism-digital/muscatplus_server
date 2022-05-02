import re
from typing import Pattern

ID_SUB: Pattern = re.compile(r"source_|person_|holding_|institution_|subject_|related_|place_|festival_|mg_")

EXTERNAL_IDS: dict = {
    "viaf": {"label": "Virtual Internet Authority File (VIAF)", "ident": "https://viaf.org/viaf/{ident}"},
    "dnb": {"label": "Deutsche Nationalbibliothek (GND)", "ident": "http://d-nb.info/gnd/{ident}"},
    "wkp": {"label": "Wikidata", "ident": "https://www.wikidata.org/wiki/{ident}"},
    "isil": {"label": "International Standard Identifier for Libraries and Related Organizations (ISIL)",
             "ident": "https://ld.zdb-services.de/resource/organisations/{ident}"},
    "bne": {"label": "Biblioteca Nacional de España", "ident": "{ident}"},
    "bnf": {"label": "Bibliothèque Nationale de France", "ident": "{ident}"},
    "iccu": {"label": "Istituto Centrale per il Catalogo Unico", "ident": "{ident}"},
    "isni": {"label": "International Standard Name Identifier", "ident": "https://isni.org/isni/{ident}"},
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

# Maps a solr field name to one or more Linked Data data types.
FieldDataType = dict[str, list[str]]


SOLR_FIELD_DATA_TYPES: FieldDataType = {
    "source_title_s": ["dcterms:title"],
    "variant_title_s": ["dcterms:alternate"],
    "additional_titles_json": ["dcterms:alternate"],
    "description_summary_sm": ["dcterms:description"],
    "language_text_sm": ["dcterms:language"],
    "language_libretto_sm": ["dcterms:language"],
    "language_original_sm": ["dcterms:language"],
    "rism_id": ["dterms:identifier", "pmo:RismNumber"],
    "opus_numbers_sm": ["dcterms:identifier", "pmo:OpusNumberStatement"],
    "material_group_types_sm": ["dcterms:type"],
    "material_group_types": ["dcterms:type"],
    "dramatic_roles_json": ["pmo:MediumOfPerformance"],
    "scoring_json": ["pmo:MediumOfPerformance"]
}


RISM_JSONLD_CONTEXT: dict = {
    "@context": {
        "@version": 1.1,
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rism": "https://rism.online/api/v1#",
        "rismdata": "https://rism.online/api/datatypes-v1#",
        "pmo": "http://performedmusicontology.org/ontology/",
        "relators": "http://id.loc.gov/vocabulary/relators/",
        "dcterms": "http://purl.org/dc/terms/",
        "as": "http://www.w3.org/ns/activitystreams#",
        "hydra": "http://www.w3.org/ns/hydra/core#",
        "geojson": "https://purl.org/geojson/vocab#",
        "schemaorg": "https://schema.org/",
        "type": "@type",
        "id": "@id",
        "none": "@none",
        "label": {
            "@id": "rdfs:label",
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
        "contents": "@nest",
        "relationships": {
            "@id": "rism:Relationships",
            "@context": {
                "role": {
                    "@id": "schemaorg:Role",
                    "@type": "@vocab"
                },
                "relatedTo": {
                    "@id": "schemaorg:agent"
                }
            }
        },
        "creator": {
            "@id": "rism:Creator",
            "@type": "@id",
            "@nest": "contents",
            "@context": {
                "role": {
                    "@id": "schemaorg:Role",
                    "@type": "@vocab"
                },
                "relatedTo": {
                    "@id": "schemaorg:agent"
                }
            }
        },
        "summary": {
            "@id": "rism:Summary",
            "@type": "@id"
        },
        "items": {
            "@id": "rdfs:List",
            "@type": "@id",
            "@container": "@list"
        },
    }
}
