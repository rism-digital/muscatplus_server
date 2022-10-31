from sanic import Blueprint, response

# Holdings are tied to sources quite closely; the URI pattern is the same, but with an additional section
# to the URL identifier.
holdings_blueprint: Blueprint = Blueprint("holdings", url_prefix="/sources")


@holdings_blueprint.route("/<source_id:str>/holdings/<holding_id:str>/")
async def holding(req, source_id:str, holding_id: str):
    return response.text("Not implemented", status=501)


@holdings_blueprint.route("/<source_id:str>/holdings/<holding_id:str>/relationships/")
async def relationships(req, source_id: str, holding_id: str):
    return response.text("Not implemented", status=501)
