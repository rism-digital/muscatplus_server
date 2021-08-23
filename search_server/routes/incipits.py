from sanic import Blueprint

from search_server.resources.incipits.render import handle_incipit_render

incipits_blueprint: Blueprint = Blueprint("incipits", url_prefix="/incipits")


@incipits_blueprint.route("/<incipit_id:string>")
async def incipit(req, incipit_id: str):
    pass


@incipits_blueprint.route("/render")
async def incipit_render(req):
    return await handle_incipit_render(req)
