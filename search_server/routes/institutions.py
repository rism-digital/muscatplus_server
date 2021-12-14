from sanic import Blueprint

from search_server.request_handlers import handle_request, handle_search
from search_server.resources.institutions.institution import handle_institution_request
from search_server.resources.institutions.institution_search import handle_institution_search_request

institutions_blueprint: Blueprint = Blueprint("institutions", url_prefix="/institutions")


@institutions_blueprint.route("/")
async def institution_list(req):
    pass

@institutions_blueprint.route("/<institution_id:string>")
async def institution(req, institution_id: str):
    return await handle_request(req,
                                handle_institution_request,
                                institution_id=institution_id)


@institutions_blueprint.route("/<institution_id:string>/sources/")
async def institution_sources(req, institution_id: str):
    return await handle_search(req,
                               handle_institution_search_request,
                               institution_id=institution_id)


@institutions_blueprint.route("/<institution_id:string>/people/")
async def institution_people_relationships_list(req, institution_id: str):
    pass


@institutions_blueprint.route("/<institution_id:string>/people/<relationship_id:string>")
async def institution_person_relationship(req, institution_id: str, relationship_id: str):
    pass


@institutions_blueprint.route("/<institution_id:string>/places/")
async def institution_places_relationships_list(req, institution_id: str):
    pass


@institutions_blueprint.route("/<institution_id:string>/places/<relationship_id:string>")
async def institution_place_relationship(req, institution_id: str, relationship_id: str):
    pass


@institutions_blueprint.route("/<institution_id:string>/institutions/")
async def institution_institutions_relationships_list(req, institution_id: str):
    pass


@institutions_blueprint.route("/<institution_id:string>/institutions/<relationship_id:string>")
async def institution_institution_relationship(req, institution_id: str, relationship_id: str):
    pass
