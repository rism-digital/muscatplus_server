from sanic import Blueprint

from search_server.request_handlers import handle_search_request, handle_request
from search_server.resources.people.people_list import handle_people_list_request
from search_server.resources.people.person import handle_person_request
from search_server.resources.people.person_source import handle_person_source_request

people_blueprint: Blueprint = Blueprint("people", url_prefix="/people")


@people_blueprint.route("/")
async def get_people(req):
    return await handle_search_request(req,
                                       handle_people_list_request)


@people_blueprint.route("/<person_id:string>/")
async def person(req, person_id: str):
    return await handle_request(req,
                                handle_person_request,
                                person_id=person_id)


@people_blueprint.route("/<person_id:string>/sources/")
async def person_sources(req, person_id: str):
    return await handle_search_request(req,
                                       handle_person_source_request,
                                       person_id=person_id)


@people_blueprint.route("/<person_id:string>/people/")
async def person_people_relationships_list(req, person_id: str):
    pass


@people_blueprint.route("/<person_id:string>/people/<relationship_id:string>")
async def person_person_relationship(req, person_id: str, relationship_id: str):
    pass


@people_blueprint.route("/<person_id:string>/places/")
async def person_places_relationships_list(req, person_id: str):
    pass


@people_blueprint.route("/<person_id:string>/places/<relationship_id:string>")
async def person_place_relationship(req, person_id: str, relationship_id: str):
    pass


@people_blueprint.route("/<person_id:string>/institutions/")
async def person_institutions_relationships_list(req, person_id: str):
    pass


@people_blueprint.route("/<person_id:string>/institutions/<relationship_id:string>")
async def person_institution_relationship(req, person_id: str, relationship_id: str):
    pass
