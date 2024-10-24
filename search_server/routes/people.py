from sanic import Blueprint, response

from search_server.request_handlers import handle_request, handle_search
from search_server.resources.people.person import handle_person_request
from search_server.resources.people.person_search import (
    handle_person_probe_request,
    handle_person_search_request,
)

people_blueprint: Blueprint = Blueprint("people", url_prefix="/people")


@people_blueprint.route("/")
async def get_people(req):
    return response.text("Not implemented", status=501)


@people_blueprint.route("/<person_id:str>/")
async def person(req, person_id: str):
    """
    Retrieves a specific person record, identified by `person_id`.

    For example, `/people/20000365`.
    """
    return await handle_request(req, handle_person_request, person_id=person_id)


@people_blueprint.route("/<person_id:str>/sources/")
async def person_sources(req, person_id: str):
    """
    Query the sources attached to this person. Supports all search options for sources.
    """
    return await handle_search(req, handle_person_search_request, person_id=person_id)


@people_blueprint.route("/<person_id:str>/probe/")
async def person_probe(req, person_id: str):
    return await handle_search(req, handle_person_probe_request, person_id=person_id)


@people_blueprint.route("/<person_id:str>/relationships/")
async def relationships(req, person_id: str):
    return response.text("Not implemented", status=501)


@people_blueprint.route("/<person_id:str>/relationships/<relationship_id:str>")
async def relationship(req, person_id: str, relationship_id: str):
    return response.text("Not implemented", status=501)


@people_blueprint.route("/<person_id:str>/digital-objects/")
async def digital_object_list(req, person_id):
    return response.text("Not implemented", status=501)


@people_blueprint.route("/<person_id:str>/digital-objects/<dobject_id:str>")
async def digital_object(req, person_id: str, dobject_id: str):
    return response.text("Not implemented", status=501)
