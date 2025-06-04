from sanic import Blueprint, response

from search_server.request_handlers import handle_request, handle_search
from search_server.resources.incipits.incipit import (
    handle_mei_download,
    handle_png_download,
)
from search_server.resources.works.handlers import (
    handle_work_request,
    handle_work_search,
)

works_blueprint: Blueprint = Blueprint("works", url_prefix="/works")


@works_blueprint.route("/<work_id:str>/")
async def work(req, work_id: str):
    return await handle_request(req, handle_work_request, work_id=work_id)


@works_blueprint.route("/<work_id:str>/sources/")
async def work_sources(req, work_id: str):
    return await handle_search(req, handle_work_search, work_id=work_id)


@works_blueprint.route("/<work_id:str>/incipits/")
async def incipits_list(req, work_id: str) -> response.HTTPResponse:
    return response.json({"message": "Not implemented"}, status=501)


@works_blueprint.route("/<work_id:str>/incipits/<work_num:str>/")
async def incipit(req, work_id: str, work_num: str) -> response.HTTPResponse:
    return response.json({"message": "Not Implemented"}, status=501)


@works_blueprint.route("/<work_id:str>/incipits/<work_num:str>/mei")
async def incipit_mei_encoding(req, work_id: str, work_num: str):
    """
    Retrieve an individual incipit encoded as MEI, based on the suffix.
    It is also possible to pass an `Accept:` header for a content-negotiated
    response to the main incipit retrieve function, so we use the same handler
    for both.
    """
    resp: dict | None = await handle_mei_download(
        req, record_id=work_id, record_type="work", work_num=work_num
    )
    if not resp:
        return response.json({"message": "The requested resource could not be found"}, status=404)

    return response.text(resp["content"], headers=resp["headers"])


@works_blueprint.route("/<work_id:str>/incipits/<work_num:str>/png")
async def incipit_png_rendering(req, work_id: str, work_num: str):
    """
    Retrieve an individual incipit encoded as MEI, based on the suffix.
    It is also possible to pass an `Accept:` header for a content-negotiated
    response to the main incipit retrieve function, so we use the same handler
    for both.
    """
    resp: dict | None = await handle_png_download(
        req, record_id=work_id, record_type="work", work_num=work_num
    )
    if not resp:
        return response.json({"message": "The requested resource could not be found"}, status=404)

    return response.raw(resp["content"], headers=resp["headers"])
