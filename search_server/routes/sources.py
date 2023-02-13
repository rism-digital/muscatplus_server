from typing import Optional

from sanic import Blueprint, response

from search_server.request_handlers import handle_request, handle_search
from search_server.resources.incipits.incipit import (
    handle_incipits_list_request,
    handle_incipit_request,
    handle_mei_download
)
from search_server.resources.sources.contents_search import (
    handle_contents_search_request,
    handle_contents_probe_request
)
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

        Also accepts "application/mei+xml" as an accept type and returns an MEI encoding
        of the incipit.

    """
    accept: Optional[str] = req.headers.get("Accept")
    print(accept)

    if accept and "application/mei+xml" in accept:
        # Handle the request differently if the Accept type is MEI
        resp: Optional[dict] = await handle_mei_download(req, source_id=source_id, work_num=work_num)
        if not resp:
            return response.text("The requested resource could not be found", status=404)
        return response.text(resp["content"], headers=resp["headers"])

    return await handle_request(req,
                                handle_incipit_request,
                                source_id=source_id,
                                work_num=work_num)


@sources_blueprint.route("/<source_id:str>/incipits/<work_num:str>/mei")
async def incipit_encoding(req, source_id: str, work_num: str):
    """
    Retrieve an individual incipit encoded as MEI, based on the suffix.
    It is also possible to pass an `Accept:` header for a content-negotiated
    response to the main incipit retrieve function, so we use the same handler
    for both.
    """
    resp: Optional[dict] = await handle_mei_download(req, source_id=source_id, work_num=work_num)
    if not resp:
        return response.text("The requested resource could not be found", status=404)

    return response.text(resp["content"], headers=resp["headers"])


@sources_blueprint.route("/<source_id:str>/contents/")
async def contents(req, source_id: str):
    """
    Performs a search query for searches against the items in this source. All queries valid for
    general source searches are valid as query arguments for this endpoint, except that the mode
    cannot be changed from `sources`.
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
    return response.text("Not implemented", status=501)


@sources_blueprint.route("/<source_id:str>/material-groups/")
async def material_groups_list(req, source_id: str):
    return response.text("Not implemented", status=501)


@sources_blueprint.route("/<source_id:str>/material-groups/<mg_id:str>/")
async def material_group(req, source_id: str, mg_id: str):
    return response.text("Not implemented", status=501)


@sources_blueprint.route("/<source_id:str>/material-groups/<mg_id:str>/relationships/")
async def material_group_relationships(req, source_id: str, mg_id: str):
    return response.text("Not implemented", status=501)


@sources_blueprint.route("/<source_id:str>/digital-objects/")
async def digital_object_list(req, source_id: str):
    return response.text("Not implemented", status=501)


@sources_blueprint.route("/<source_id:str>/digital-objects/<dobject_id:str>")
async def digital_object(req, source_id: str, digital_object_id: str):
    return response.text("Not implemented", status=501)

