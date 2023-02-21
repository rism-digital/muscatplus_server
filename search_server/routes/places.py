from sanic import Blueprint, response

from search_server.request_handlers import handle_request
from search_server.resources.places.place import handle_place_request

places_blueprint: Blueprint = Blueprint("places", url_prefix="/places")


@places_blueprint.route("/")
async def place_list(req):
    return response.text("Not implemented", status=501)


@places_blueprint.route("/<place_id:str>/")
async def place(req, place_id: str):
    return await handle_request(req,
                                handle_place_request,
                                place_id=place_id)


@places_blueprint.route("/<place_id:str>/relationships/<relationship_id:str>")
async def relationship(req, place_id: str, relationship_id: str):
    return response.text("Not implemented", status=501)
