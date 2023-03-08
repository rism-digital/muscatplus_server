from sanic import Blueprint, response

from search_server.request_handlers import handle_request
from search_server.resources.works.handlers import handle_work_request

works_blueprint: Blueprint = Blueprint("works", url_prefix="/works")


@works_blueprint.route("/<work_id:str>/")
async def work(req, work_id: str):
    return await handle_request(req,
                                handle_work_request,
                                work_id=work_id)


@works_blueprint.route("/<work_id:str>/sources")
async def work_sources(req, work_id: str):
    return response.text("Not implemented", status=501)
