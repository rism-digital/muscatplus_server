from sanic import Blueprint, response

from search_server.request_handlers import handle_request, handle_search
from search_server.resources.institutions.geojson import handle_institution_geojson_request
from search_server.resources.institutions.institution import handle_institution_request
from search_server.resources.institutions.institution_search import (
    handle_institution_search_request,
    handle_institution_probe_request
)

institutions_blueprint: Blueprint = Blueprint("institutions", url_prefix="/institutions")


@institutions_blueprint.route("/")
async def institution_list(req):
    return response.text("Not implemented", status=501)


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
    """
        Query the sources attached to this institution. Supports all search options for sources.
    """
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
    return response.text("Not implemented", status=501)


@institutions_blueprint.route("/<institution_id:str>/relationships/<relationship_id:str>")
async def relationship(req, institution_id: str, relationship_id: str):
    return response.text("Not implemented", status=501)


@institutions_blueprint.route("/<institution_id:str>/digital-objects/")
async def digital_object_list(req, institution_id: str):
    return response.text("Not implemented", status=501)


@institutions_blueprint.route("/<institution_id:str>/digital-objects/<dobject_id:str>")
async def digital_object(req, institution_id: str, dobject_id: str):
    return response.text("Not implemented", status=501)


@institutions_blueprint.route("/<institution_id:str>/location.geojson")
async def geo_coordinates(req, institution_id: str):
    return await handle_request(req,
                                handle_institution_geojson_request,
                                suppress_context=True,
                                institution_id=institution_id)
