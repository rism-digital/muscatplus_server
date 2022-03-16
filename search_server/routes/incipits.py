from sanic import Blueprint

from search_server.resources.incipits.render import handle_incipit_render, handle_incipit_validate

incipits_blueprint: Blueprint = Blueprint("incipits", url_prefix="/incipits")


@incipits_blueprint.route("/<incipit_id:str>")
async def incipit(req, incipit_id: str):
    pass


@incipits_blueprint.route("/render")
async def incipit_render(req):
    return await handle_incipit_render(req)


@incipits_blueprint.route("/validate")
async def incipit_validate(req):
    return await handle_incipit_validate(req)
