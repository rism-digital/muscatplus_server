import re
from typing import Pattern, Dict

ID_SUB: Pattern = re.compile(r"source_|person_|holding_|institution_")

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

    # return template.format(scheme=scheme, host=host, **kwargs)


roles: Dict = {
    "prf": "Performer",
    "lyr": "Lyricist",
    "fmo": "Former owner",
    "arr": "Arranger"
}


def humanize_role(rle: str) -> str:
    return roles.get(rle, rle)

