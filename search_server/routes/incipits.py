from sanic import Blueprint

incipits_blueprint: Blueprint = Blueprint("incipits", url_prefix="/incipits")


@incipits_blueprint.route("/<incipit_id:string>")
async def incipit(req, incipit_id: str):
    pass
