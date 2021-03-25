import asyncio
import logging
from typing import Dict, Callable, Optional

import pysolr
import uvloop
import yaml
from sanic import Sanic, request, response

from search_server.exceptions import InvalidQueryException
from search_server.helpers.identifiers import RISM_JSONLD_CONTEXT
from search_server.helpers.semantic_web import to_turtle, to_rdf
from search_server.resources.institutions.institution import handle_institution_request
from search_server.resources.institutions.institution_source import handle_institution_source_request
from search_server.resources.institutions.institutions_list import handle_institutions_list_request
from search_server.resources.people.people_list import handle_people_list_request
from search_server.resources.people.person_source import handle_person_source_request
from search_server.resources.search.search import handle_search_request
from search_server.resources.siglum.sigla import handle_sigla_request
from search_server.resources.sources.full_source import handle_source_request
from search_server.resources.sources.source_creator import handle_creator_request
from search_server.resources.sources.source_exemplar import handle_holding_request
from search_server.resources.sources.source_incipit import handle_incipit_request, handle_incipits_list_request
from search_server.resources.people.person import handle_person_request
from search_server.resources.sources.source_list import handle_source_list_request
from search_server.resources.sources.source_materialgroup import (
    handle_materialgroups_list_request,
    handle_materialgroups_request
)
from search_server.resources.sources.source_relationship import (
    handle_relationships_request,
    handle_relationships_list_request
)

from search_server.helpers.languages import load_translations
from search_server.resources.subjects.subject import handle_subject_request
from search_server.resources.subjects.subject_source import handle_subject_source_request

config: Dict = yaml.safe_load(open('configuration.yml', 'r'))
app = Sanic("search_server")

# Make the configuration globally available in the app instance.
app.config.update(config)

debug_mode: bool = config['common']['debug']
context_uri: bool = config['common']['context_uri']

# Indent levels can make a big difference in download size, but at the expense of making
# the output readable. Set to indent only in Debug mode.
JSON_INDENT: int = 0

if debug_mode:
    LOGLEVEL = logging.DEBUG
    JSON_INDENT = 4
else:
    LOGLEVEL = logging.WARNING
    asyncio.set_event_loop(uvloop.new_event_loop())

logging.basicConfig(format="[%(asctime)s] [%(levelname)8s] %(message)s (%(filename)s:%(lineno)s)",
                    level=LOGLEVEL)

log = logging.getLogger("mp_server")

translations: Optional[Dict] = load_translations("locales/")
if not translations:
    log.critical("No translations can be loaded.")

app.translations = translations
app.context_uri = context_uri


@app.middleware('response')
async def add_cors(req, resp):
    resp.headers['access-control-allow-origin'] = "*"


async def _handle_request(req: request.Request, handler: Callable, **kwargs) -> response.HTTPResponse:
    """
    Takes in a request object and a function for handling the request. This function should return
    a Dictionary object for the result of the request, or None if the requested object was not found.

    IDs for the objects being requested, as parsed from the path, should be sent as the keyword arguments.

    Returns a JSON response back to the user if successful, or an error if not.

    :param req: A Sanic request object
    :param handler: A function for handling the request
    :param kwargs: A set of options to be passed to the
    :return: A JSON Response, or an error if not successful.
    """
    accept: Optional[str] = req.headers.get("Accept")

    data_obj: Optional[Dict] = handler(req, **kwargs)

    if not data_obj:
        return response.text(
            "The requested resource was not found",
            status=404
        )

    response_headers: Dict = {}

    if accept and "text/turtle" in accept:
        log.debug("Sending Turtle")

        turtle_resp: str = to_turtle(data_obj)
        response_headers["Content-Type"] = "text/turtle; charset=utf-8"

        return response.text(
            turtle_resp,
            headers=response_headers
        )
    elif accept and "application/n-quads" in accept:
        log.debug("Sending RDF")
        rdf_resp: str = to_rdf(data_obj)
        response_headers["Content-Type"] = "application/n-quads; charset=utf-8"

        return response.text(
            rdf_resp,
            headers=response_headers
        )
    else:
        log.debug("Sending JSON-LD")
        # The default return type is JSON-LD
        response_headers["Content-Type"] = "application/ld+json; charset=utf-8"

        return response.json(
            data_obj,
            headers=response_headers,
            escape_forward_slashes=False,
            indent=JSON_INDENT
        )


async def _handle_search_request(req: request.Request, handler: Callable, **kwargs) -> response.HTTPResponse:
    accept: Optional[str] = req.headers.get("Accept")

    # Check whether we can respond with the correct content type. Note that
    # this server does not handle HTML responses; these are handled before
    # the request reaches this server.
    # if accept and (("application/ld+json" not in accept) or ("application/json" not in accept)):
    #     return response.text("Supported content types for search interfaces are 'application/json' and application/ld+json'",
    #                          status=406)

    try:
        data_obj: Dict = handler(req, **kwargs)
    except InvalidQueryException as e:
        return response.text(f"Invalid search query. {e}", status=400)
    except pysolr.SolrError as e:
        error_message: str = f"Error sending search to Solr. {e}"
        log.exception(error_message)
        return response.text(error_message, status=500)

    if not data_obj:
        return response.text("The requested resource was not found",
                             status=404)

    response_headers: Dict = {
        "Content-Type": "application/ld+json; charset=utf-8"
    }

    return response.json(
        data_obj,
        headers=response_headers,
        escape_forward_slashes=False,
        indent=JSON_INDENT
    )


@app.route("/")
async def root(req):
    return response.json({"message": "Hello World"})


@app.route("/api/v1/context.json")
async def context(req) -> response.HTTPResponse:
    return response.json(RISM_JSONLD_CONTEXT)


@app.route("/sources/")
async def source_list(req):
    return await _handle_search_request(req,
                                        handle_source_list_request)


@app.route("/sources/<source_id:string>/")
async def source(req, source_id: str):
    return await _handle_request(req,
                                 handle_source_request,
                                 source_id=source_id)


@app.route("/sources/<source_id:string>/incipits/")
async def incipits_list(req, source_id: str):
    return await _handle_request(req,
                                 handle_incipits_list_request,
                                 source_id=source_id)


@app.route("/sources/<source_id:string>/incipits/<work_num:string>/")
async def incipit(req, source_id: str, work_num: str):
    return await _handle_request(req,
                                 handle_incipit_request,
                                 source_id=source_id,
                                 work_num=work_num)


@app.route("/sources/<source_id:string>/materialgroups/")
async def materialgroups_list(req, source_id: str):
    return await _handle_request(req,
                                 handle_materialgroups_list_request,
                                 source_id=source_id)


@app.route("/sources/<source_id:string>/materialgroups/<materialgroup_id:string>/")
async def materialgroup(req, source_id: str, materialgroup_id: str):
    return await _handle_request(req,
                                 handle_materialgroups_request,
                                 source_id=source_id,
                                 materialgroup_id=materialgroup_id)


@app.route("/sources/<source_id:string>/relationships/")
async def relationships_list(req, source_id: str):
    return await _handle_request(req,
                                 handle_relationships_list_request,
                                 source_id=source_id)


@app.route("/sources/<source_id:string>/relationships/<relationship_id:string>/")
async def relationship(req, source_id: str, relationship_id: str):
    return await _handle_request(req,
                                 handle_relationships_request,
                                 source_id=source_id,
                                 relationship_id=relationship_id)


@app.route("/sources/<source_id:string>/creator")
async def creator(req, source_id: str):
    return await _handle_request(req,
                                 handle_creator_request,
                                 source_id=source_id)


@app.route("/sources/<source_id:string>/holdings/")
async def holding_list(req, source_id: str):
    pass


@app.route("/sources/<source_id:string>/holdings/<holding_id:string>/")
async def holding(req, source_id: str, holding_id: str):
    return await _handle_request(req,
                                 handle_holding_request,
                                 source_id=source_id,
                                 holding_id=holding_id)


@app.route("/people/")
async def get_people(req):
    return await _handle_search_request(req,
                                        handle_people_list_request)


@app.route("/people/<person_id:string>/")
async def person(req, person_id: str):
    return await _handle_request(req,
                                 handle_person_request,
                                 person_id=person_id)


@app.route("/people/<person_id:string>/sources/")
async def person_sources(req, person_id: str):
    return await _handle_search_request(req,
                                        handle_person_source_request,
                                        person_id=person_id)


@app.route("/people/<person_id:string>/relationships/")
async def person_relationships_list(req, person_id: str):
    pass


@app.route("/people/<person_id:string>/relationships/<related_id:string>")
async def person_person_relationship(req, person_id: str, related_id: str):
    pass


@app.route("/people/<person_id:string>/places/")
async def person_place_relationships_list(req, person_id: str):
    pass


@app.route("/people/<person_id:string>/places/<related_id:string>")
async def person_place_relationship(req, person_id: str, related_id: str):
    pass


@app.route("/subjects/")
async def subject_list(req):
    pass


@app.route("/subjects/<subject_id:string>/")
async def subject(req, subject_id: str):
    return await _handle_request(req,
                                 handle_subject_request,
                                 subject_id=subject_id)


@app.route("/subjects/<subject_id:string>/sources/")
async def subject_sources(req, subject_id: str):
    return await _handle_search_request(req,
                                        handle_subject_source_request,
                                        subject_id=subject_id)


@app.route("/institutions/")
async def institution_list(req):
    return await _handle_search_request(req,
                                        handle_institutions_list_request)


@app.route("/institutions/<institution_id:string>")
async def institution(req, institution_id: str):
    return await _handle_request(req,
                                 handle_institution_request,
                                 institution_id=institution_id)


@app.route("/institutions/<institution_id:string>/sources/")
async def institution_sources(req, institution_id: str):
    return await _handle_search_request(req,
                                        handle_institution_source_request,
                                        institution_id=institution_id)

@app.route("/sigla/")
async def sigla(req):
    return await _handle_search_request(req, handle_sigla_request)


@app.route("/search/")
async def search(req):
    return await handle_search_request(req)
