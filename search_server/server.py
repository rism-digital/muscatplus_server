import asyncio
import logging
from typing import Dict, Callable, Optional

import uvloop
import yaml
from sanic import Sanic, request, response

from search_server.helpers.identifiers import RISM_JSONLD_CONTEXT
from search_server.resources.institutions.institution import handle_institution_request
from search_server.resources.search.search import handle_search_request
from search_server.resources.siglum.sigla import handle_sigla_request
from search_server.resources.sources.full_source import handle_source_request
from search_server.resources.sources.source_creator import handle_creator_request
from search_server.resources.sources.source_holding import handle_holding_request
from search_server.resources.sources.source_incipit import handle_incipit_request, handle_incipits_list_request
from search_server.resources.people.person import handle_person_request
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

log = logging.getLogger(__name__)

translations: Optional[Dict] = load_translations("locales/")
if not translations:
    log.error("No translations can be loaded.")

app.translations = translations
app.context_uri = context_uri


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
    data_obj: Optional[Dict] = handler(req, **kwargs)

    if not data_obj:
        return response.text(
            "The requested resource was not found",
            status=404
        )

    return response.json(
        data_obj,
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
def source_list(req):
    pass


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


@app.route("/sources/<source_id:string>/incipits/<incipit_id:string>/")
async def incipit(req, source_id: str, incipit_id: str):
    return await _handle_request(req,
                                 handle_incipit_request,
                                 source_id=source_id,
                                 incipit_id=incipit_id)


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

@app.route("/sources/<source_id:string>/holdings/<holding_id:string>/")
async def holding(req, source_id: str, holding_id: str):
    return await _handle_request(req,
                                 handle_holding_request,
                                 source_id=source_id,
                                 holding_id=holding_id)


@app.route("/people/")
async def get_people(req):
    pass


@app.route("/people/<person_id:string>/")
async def person(req, person_id: str):
    return await _handle_request(req,
                                 handle_person_request,
                                 person_id=person_id)


@app.route("/subjects/")
async def subject_list(req):
    pass


@app.route("/subjects/<subject_id:string>/")
async def subject(req, subject_id: str):
    return await _handle_request(req,
                                 handle_subject_request,
                                 subject_id=subject_id)


@app.route("/institutions/")
async def institution_list(req):
    pass


@app.route("/institutions/<institution_id:string>")
async def institution(req, institution_id: str):
    return await _handle_request(req,
                                 handle_institution_request,
                                 institution_id=institution_id)


@app.route("/sigla/")
async def sigla(req):
    return await _handle_request(req, handle_sigla_request)


@app.route("/search/")
async def search(req):
    return await handle_search_request(req)
