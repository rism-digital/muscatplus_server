from sanic import request


def strip_prefix(ident: str) -> str:
    # Returns the last component of a solr document identifier,
    # the actual ID number.
    return ident.split("_")[-1]


PROJECT_IDENTIFIERS = {
    "diamm": "https://www.diamm.ac.uk/",
    "cantus": "https://cantusdatabase.org/",
    "rism": "https://rism.online/",
}

EXTERNAL_IDS: dict = {
    "viaf": {
        "label": "Virtual Internet Authority File (VIAF)",
        "ident": "https://viaf.org/viaf/{ident}",
    },
    "dnb": {
        "label": "Deutsche Nationalbibliothek (GND)",
        "ident": "https://d-nb.info/gnd/{ident}",
    },
    "wkp": {"label": "Wikidata", "ident": "https://www.wikidata.org/wiki/{ident}"},
    "isil": {
        "label": "International Standard Identifier for Libraries and Related Organizations (ISIL)"
    },
    "bne": {"label": "Biblioteca Nacional de España"},
    "bnf": {
        "label": "Bibliothèque Nationale de France",
        "ident": "https://ark.bnf.fr/{ident}",
    },
    "iccu": {
        "label": "Istituto Centrale per il Catalogo Unico"
    },  # No stable URI for authorities
    "isni": {
        "label": "International Standard Name Identifier",
        "ident": "https://isni.org/isni/{ident}",
    },
    "lc": {
        "label": "Library of Congress",
        "ident": "http://id.loc.gov/authorities/names/{ident}",
    },
    "nlp": {"label": "Biblioteka Narodowa"},
    "nkc": {"label": "Národní knihovna České republiky"},
    "swnl": {"label": "Schweizerische Nationalbibliothek"},
    "moc": {"label": "MARC Organization Code"},  # No URI possible.
    "orcid": {
        "label": "Open Researcher and Contributor ID (ORCiD)",
        "ident": "https://orcid.org/{ident}",
    },
    "diamm": {
        "label": "Digital Image Archive of Medieval Music",
        "ident": "https://www.diamm.ac.uk/{ident}",
    },
    "cantus": {
        "label": "Cantus: A Database for Latin Ecclesiastical Chant",
        "ident": "https://cantusdatabase.org/{ident}",
    },
    "cmo": {
        "label": "Corpus Musicae Ottomanicae (CMO)",
        "ident": "https://corpus-musicae-ottomanicae.de/receive/{ident}",
    },
}


def get_identifier(req: request.Request, viewname: str, **kwargs) -> str:  # noqa: F821
    """
    Takes a request object, parses it out, and returns a templated identifier suitable
    for use in an "id" field, including the incoming request information on host and scheme (http/https).

    :param req: A Sanic request object
    :param viewname: A string of the view for which we will retrieve the URL. Matches the function name in server.py.
    :param kwargs: A set of keywords matching the template formatting variables
    :return: A templated string
    """
    fwd_scheme_header = req.headers.get("X-Forwarded-Proto")
    fwd_host_header = req.headers.get("X-Forwarded-Host")

    scheme: str = fwd_scheme_header if fwd_scheme_header else req.scheme
    server: str = fwd_host_header if fwd_host_header else req.host

    return req.app.url_for(
        viewname, _external=True, _scheme=scheme, _server=server, **kwargs
    )


def get_site(req: request.Request) -> str:
    """
    Takes a request object, parses it out, and returns the base URL for the site.
    Works even behind a proxy by looking at the X-Forwarded headers. Similar to the
    get_identifier function but returns the base protocol (http|https) and the server
    as a string, rather than passing them to Sanic for full templating.

    Does NOT add a trailing slash.

    :param req: A Sanic request object
    :return: A templated string
    """
    fwd_scheme_header = req.headers.get("X-Forwarded-Proto")
    fwd_host_header = req.headers.get("X-Forwarded-Host")

    scheme: str = fwd_scheme_header if fwd_scheme_header else req.scheme
    server: str = fwd_host_header if fwd_host_header else req.host

    return f"{scheme}://{server}"


def get_url_from_type(
    req: request.Request, record_type: str, record_id: str
) -> str | None:
    site: str = get_site(req)

    match record_type:
        case "source":
            return f"{site}/sources/{record_id}"
        case "person":
            return f"{site}/people/{record_id}"
        case "institution":
            return f"{site}/institutions/{record_id}"
        case "work":
            return f"{site}/works/{record_id}"
        case _:
            return None


# Maps a solr field name to one or more Linked Data data types.
FieldDataType = dict[str, list[str]]


SOLR_FIELD_DATA_TYPES: FieldDataType = {
    "standard_title_s": ["dcterms:title", "rism:StandardizedTitle"],
    "source_title_sm": ["dcterms:title"],
    "variant_titles_sm": ["dcterms:alternate"],
    "additional_titles_json": ["dcterms:alternate"],
    "description_summary_sm": ["dcterms:description"],
    "language_text_sm": ["dcterms:language"],
    "language_original_sm": ["dcterms:language"],
    "rism_id": ["dcterms:identifier", "pmo:RismNumber"],
    "opus_numbers_sm": ["dcterms:identifier", "pmo:OpusNumberStatement"],
    "material_source_types_sm": ["dcterms:type"],
    "material_source_types": ["dcterms:type"],
    "dramatic_roles_json": ["pmo:MediumOfPerformance"],
    "scoring_json": ["pmo:MediumOfPerformance"],
}

RISM_RELATIONSHIP_BASE = "https://rism.online/vocabulary/relationship/"
LOC_RELATOR_BASE = "http://id.loc.gov/vocabulary/relators/"
RDAU_BASE = "http://rdaregistry.info/Elements/u/"
