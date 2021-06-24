from sanic import Blueprint

from search_server.request_handlers import handle_request
from search_server.resources.incipits.incipit import handle_incipits_list_request, handle_incipit_request
from search_server.resources.sources.handlers import (
    handle_source_request,
)


sources_blueprint: Blueprint = Blueprint("sources", url_prefix="/sources")


@sources_blueprint.route("/<source_id:string>/")
async def source(req, source_id: str):
    return await handle_request(req,
                                handle_source_request,
                                source_id=source_id)


@sources_blueprint.route("/<source_id:string>/incipits/")
async def incipits_list(req, source_id: str):
    return await handle_request(req,
                                handle_incipits_list_request,
                                source_id=source_id)


@sources_blueprint.route("/<source_id:string>/incipits/<work_num:string>/")
async def incipit(req, source_id: str, work_num: str):
    return await handle_request(req,
                                handle_incipit_request,
                                source_id=source_id,
                                work_num=work_num)
