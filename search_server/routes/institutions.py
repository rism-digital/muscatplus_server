from sanic import Blueprint

from search_server.request_handlers import handle_search_request, handle_request
from search_server.resources.institutions.institution import handle_institution_request
from search_server.resources.institutions.institution_source import handle_institution_source_request
from search_server.resources.institutions.institutions_list import handle_institutions_list_request

institutions_blueprint: Blueprint = Blueprint("institutions", url_prefix="/institutions")


@institutions_blueprint.route("/")
async def institution_list(req):
    return await handle_search_request(req,
                                        handle_institutions_list_request)


@institutions_blueprint.route("/<institution_id:string>")
async def institution(req, institution_id: str):
    return await handle_request(req,
                                 handle_institution_request,
                                 institution_id=institution_id)


@institutions_blueprint.route("/<institution_id:string>/sources/")
async def institution_sources(req, institution_id: str):
    return await handle_search_request(req,
                                        handle_institution_source_request,
                                        institution_id=institution_id)


@institutions_blueprint.route("/<institution_id:string>/people/")
async def institution_person_relationships_list(req, institution_id: str):
    pass


@institutions_blueprint.route("/<institution_id:string>/people/<related_id:string>")
async def institution_person_relationship(req, institution_id: str, related_id: str):
    pass


@institutions_blueprint.route("/<institution_id:string>/places/")
async def institution_place_relationships_list(req, institution_id: str):
    pass


@institutions_blueprint.route("/<institution_id:string>/places/<related_id:string>")
async def institution_place_relationship(req, institution_id: str, related_id: str):
    pass


@institutions_blueprint.route("/<institution_id:string>/institutions/")
async def institution_institution_relationships_list(req, institution_id: str):
    pass


@institutions_blueprint.route("/<institution_id:string/institutions/<related_id:string>")
async def institution_institution_relationship(req, institution_id: str, related_id: str):
    pass