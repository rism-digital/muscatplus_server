import re
from typing import Pattern, Optional

ID_SUB: Pattern = re.compile(r"source_|person_|holding_|institution_|subject_|related_|place_|festival_|mg_|dobject_|work_")
PROJECT_ID_SUB: Pattern = re.compile(r"diamm_source_|diamm_person_|diamm_holding_|diamm_institution_|diamm_organization_|diamm_archive_")


PROJECT_IDENTIFIERS = {
    "diamm": "https://www.diamm.ac.uk/",
    "cantus": "https://cantusdatabase.org/",
    "rism": "https://rism.online/"
}

EXTERNAL_IDS: dict = {
    "viaf": {"label": "Virtual Internet Authority File (VIAF)",
             "ident": "https://viaf.org/viaf/{ident}"},
    "dnb": {"label": "Deutsche Nationalbibliothek (GND)",
            "ident": "http://d-nb.info/gnd/{ident}"},
    "wkp": {"label": "Wikidata",
            "ident": "https://www.wikidata.org/wiki/{ident}"},
    "isil": {"label": "International Standard Identifier for Libraries and Related Organizations (ISIL)",
             "ident": "https://ld.zdb-services.de/resource/organisations/{ident}"},
    "bne": {"label": "Biblioteca Nacional de España"},
    "bnf": {"label": "Bibliothèque Nationale de France"},
    "iccu": {"label": "Istituto Centrale per il Catalogo Unico"},  # No stable URI for authorities
    "isni": {"label": "International Standard Name Identifier",
             "ident": "https://isni.org/isni/{ident}"},
    "lc": {"label": "Library of Congress",
           "ident": "http://id.loc.gov/authorities/names/{ident}"},
    "nlp": {"label": "Biblioteka Narodowa"},
    "nkc": {"label": "Národní knihovna České republiky"},
    "swnl": {"label": "Schweizerische Nationalbibliothek"},
    "moc": {"label": "MARC Organization Code"},  # No URI possible.
    "orcid": {"label": "Open Researcher and Contributor ID (ORCiD)",
              "ident": "https://orcid.org/{ident}"},
    "diamm": {"label": "Digital Image Archive of Medieval Music",
              "ident": "https://www.diamm.ac.uk/{ident}"},
    "cantus": {"label": "Cantus: A Database for Latin Ecclesiastical Chant",
               "ident": "https://cantusdatabase.org/{ident}"}
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


def get_site(req) -> str:
    """
    Takes a request object, parses it out, and returns the base URL for the site.
    Works even behind a proxy by looking at the X-Forwarded headers. Similar to the
    get_identifier function but returns the base protocol (http|https) and the server
    as a string, rather than passing them to Sanic for full templating.

    Does NOT add a trailing slash.

    :param req: A Sanic request object
    :return: A templated string
    """
    fwd_scheme_header = req.headers.get('X-Forwarded-Proto')
    fwd_host_header = req.headers.get('X-Forwarded-Host')

    scheme: str = fwd_scheme_header if fwd_scheme_header else req.scheme
    server: str = fwd_host_header if fwd_host_header else req.host

    return f"{scheme}://{server}"


def get_url_from_type(req, record_type: str, record_id: str) -> Optional[str]:
    site: str = get_site(req)
    url: str

    if record_type == "source":
        url = f"{site}/sources/{record_id}"
    elif record_type == "person":
        url = f"{site}/people/{record_id}"
    elif record_type == "institution":
        url = f"{site}/institutions/{record_id}"
    else:
        return None

    return url


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
    "rism_id": ["dcterms:identifier", "pmo:RismNumber"],
    "opus_numbers_sm": ["dcterms:identifier", "pmo:OpusNumberStatement"],
    "material_source_types_sm": ["dcterms:type"],
    "material_source_types": ["dcterms:type"],
    "dramatic_roles_json": ["pmo:MediumOfPerformance"],
    "scoring_json": ["pmo:MediumOfPerformance"]
}

