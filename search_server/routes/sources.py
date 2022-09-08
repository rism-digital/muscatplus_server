from sanic import Blueprint

from search_server.request_handlers import handle_request, handle_search
from search_server.resources.incipits.incipit import handle_incipits_list_request, handle_incipit_request
from search_server.resources.sources.contents_search import handle_contents_search_request, \
    handle_contents_probe_request
from search_server.resources.sources.handlers import (
    handle_source_request,
)


sources_blueprint: Blueprint = Blueprint("sources", url_prefix="/sources")


@sources_blueprint.route("/<source_id:str>/")
async def source(req, source_id: str):
    """
    Retrieves a specific source, identified by the source_id.

    For example, `/source/990041209`.
    """
    return await handle_request(req,
                                handle_source_request,
                                source_id=source_id)


@sources_blueprint.route("/<source_id:str>/incipits/")
async def incipits_list(req, source_id: str):
    return await handle_request(req,
                                handle_incipits_list_request,
                                source_id=source_id)


@sources_blueprint.route("/<source_id:str>/incipits/<work_num:str>/")
async def incipit(req, source_id: str, work_num: str):
    """
        Retrieves an individual incipit. Requires both the source ID and a work ID.

    """
    return await handle_request(req,
                                handle_incipit_request,
                                source_id=source_id,
                                work_num=work_num)


@sources_blueprint.route("/<source_id:str>/contents/")
async def contents(req, source_id: str):
    """
    Performs a search query for searches against the items in this source. All queries valid for
    general source searches are valid as query arguments for this endpoint.
    """
    return await handle_search(req,
                               handle_contents_search_request,
                               source_id=source_id)


@sources_blueprint.route("/<source_id:str>/probe/")
async def probe(req, source_id: str):
    """
    Performs a probe query for searches against the items in this source. See the documentation for the
    `/probe` route documentation for more details.
    """
    return await handle_search(req,
                               handle_contents_probe_request,
                               source_id=source_id)


@sources_blueprint.route("/<source_id:str>/relationships/")
async def relationships(req, source_id: str):
    pass


@sources_blueprint.route("/<source_id:str>/material-groups/")
async def material_groups_list(req, source_id: str):
    pass


@sources_blueprint.route("/<source_id:str>/material-groups/<mg_id:str>/")
async def material_group(req, source_id: str, mg_id: str):
    pass


@sources_blueprint.route("/<source_id:str>/material-groups/<mg_id:str>/relationships/")
async def material_group_relationships(req, source_id: str, mg_id: str):
    pass

