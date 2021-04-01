from sanic import Blueprint

places_blueprint: Blueprint = Blueprint("places", url_prefix="/places")


@places_blueprint.route("/")
async def place_list(req):
    pass


@places_blueprint.route("/<place_id:string>/")
async def place(req, place_id: str):
    pass