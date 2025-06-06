from sanic import Blueprint, response

from search_server.request_handlers import handle_request, handle_search
from search_server.resources.publications.handlers import (
    handle_publication_request,
    handle_publication_search_request,
)

publications_blueprint: Blueprint = Blueprint("publications", url_prefix="/publications")


@publications_blueprint.route("/<publication_id:str>/")
async def publication(req, publication_id: str) -> response.HTTPResponse:
    return await handle_request(req, handle_publication_request, publication_id=publication_id)

@publications_blueprint.route("/")
async def publications_list(req) -> response.HTTPResponse:
    return response.json({"message": "Not implemented"}, status=501)

@publications_blueprint.route("/<publication_id:str>/works/")
async def publication_works(req, publication_id: str) -> response.HTTPResponse:
    return await handle_search(req, handle_publication_search_request, publication_id=publication_id)
