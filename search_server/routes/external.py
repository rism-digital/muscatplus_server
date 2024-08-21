from sanic import Blueprint, response

from search_server.request_handlers import handle_request
from search_server.resources.external.external import handle_external_request

external_blueprint: Blueprint = Blueprint("external", url_prefix="/external")


@external_blueprint.route("/<project:str>/<resource_type:str>/<ext_id:str>/")
async def external(req, project: str, resource_type: str, ext_id: str):
    return await handle_request(
        req,
        handle_external_request,
        project=project,
        resource_type=resource_type,
        ext_id=ext_id,
    )


@external_blueprint.route(
    "/<project:str>/source/<source_id:str>/holding/<institution_id:str>"
)
def external_holding(req, project: str, source_id: str, institution_id: str):
    return response.text("Not implemented", status=501)
