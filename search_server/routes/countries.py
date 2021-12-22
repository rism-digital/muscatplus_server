from sanic import Blueprint

from search_server.request_handlers import handle_request
from search_server.resources.countries.country import handle_country_request, handle_country_list_request

countries_blueprint: Blueprint = Blueprint("countries", url_prefix="/countries")


@countries_blueprint.route("/<country_id:string>/")
async def country(req, country_id: str):
    return await handle_request(req,
                                handle_country_request,
                                festival_id=country_id)


@countries_blueprint.route("/list/")
async def country_list(req):
    return await handle_request(req,
                                handle_country_list_request)
