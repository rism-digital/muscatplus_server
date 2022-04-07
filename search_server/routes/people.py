from sanic import Blueprint

from search_server.request_handlers import handle_request, handle_search
from search_server.resources.people.person import handle_person_request
from search_server.resources.people.person_search import handle_person_search_request, handle_person_probe_request

people_blueprint: Blueprint = Blueprint("people", url_prefix="/people")


@people_blueprint.route("/")
async def get_people(req):
    pass


@people_blueprint.route("/<person_id:str>/")
async def person(req, person_id: str):
    return await handle_request(req,
                                handle_person_request,
                                person_id=person_id)


@people_blueprint.route("/<person_id:str>/sources/")
async def person_sources(req, person_id: str):
    return await handle_search(req,
                               handle_person_search_request,
                               person_id=person_id)


@people_blueprint.route("/<person_id:str>/probe/")
async def person_probe(req, person_id: str):
    return await handle_search(req,
                               handle_person_probe_request,
                               person_id=person_id)


@people_blueprint.route("/<person_id:str>/people/")
async def person_people_relationships_list(req, person_id: str):
    pass


@people_blueprint.route("/<person_id:str>/people/<relationship_id:str>")
async def person_person_relationship(req, person_id: str, relationship_id: str):
    pass


@people_blueprint.route("/<person_id:str>/places/")
async def person_places_relationships_list(req, person_id: str):
    pass


@people_blueprint.route("/<person_id:str>/places/<relationship_id:str>")
async def person_place_relationship(req, person_id: str, relationship_id: str):
    pass


@people_blueprint.route("/<person_id:str>/institutions/")
async def person_institutions_relationships_list(req, person_id: str):
    pass


@people_blueprint.route("/<person_id:str>/institutions/<relationship_id:str>")
async def person_institution_relationship(req, person_id: str, relationship_id: str):
    pass
