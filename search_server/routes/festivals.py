from sanic import Blueprint

from search_server.request_handlers import handle_request
from search_server.resources.liturgical_festivals.liturgical_festival import handle_festival_request

festivals_blueprint: Blueprint = Blueprint("festivals", url_prefix="/festivals")


@festivals_blueprint.route("/<festival_id:string>/")
async def festival(req, festival_id: str):
    return await handle_request(req,
                                handle_festival_request,
                                festival_id=festival_id)
