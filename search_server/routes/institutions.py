from sanic import Blueprint

from search_server.request_handlers import handle_request, handle_search
from search_server.resources.institutions.institution import handle_institution_request
from search_server.resources.institutions.institution_search import handle_institution_search_request, handle_institution_probe_request

institutions_blueprint: Blueprint = Blueprint("institutions", url_prefix="/institutions")


@institutions_blueprint.route("/")
async def institution_list(req):
    pass


@institutions_blueprint.route("/<institution_id:str>")
async def institution(req, institution_id: str):
    """
    Retrieves a specific institution record, identified by `institution_id`.

    For example, `/institutions/30000004`
    """
    return await handle_request(req,
                                handle_institution_request,
                                institution_id=institution_id)


@institutions_blueprint.route("/<institution_id:str>/sources/")
async def institution_sources(req, institution_id: str):
    return await handle_search(req,
                               handle_institution_search_request,
                               institution_id=institution_id)


@institutions_blueprint.route("/<institution_id:str>/probe/")
async def institution_probe(req, institution_id: str):
    return await handle_search(req,
                               handle_institution_probe_request,
                               institution_id=institution_id)


@institutions_blueprint.route("/<institution_id:str>/relationships/")
async def relationships(req, institution_id: str):
    pass
