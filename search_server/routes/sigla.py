from typing import Optional
from urllib.parse import unquote

from sanic import Blueprint, response

from search_server.resources.siglum.sigla import handle_institution_sigla_request, handle_siglum_search_request

sigla_blueprint: Blueprint = Blueprint("sigla", url_prefix="/sigla")


@sigla_blueprint.route("/<siglum:str>")
async def siglum_redirect(req, siglum: str):
    resp: Optional[str] = await handle_institution_sigla_request(req, siglum)

    if not resp:
        return response.text(f"An institution with the siglum {unquote(siglum)} was not found.", status=404)

    return response.redirect(resp, status=303)


@sigla_blueprint.route("/")
async def siglum_search(req):
    resp: Optional[dict] = await handle_siglum_search_request(req)
    if not resp:
        response.text(f"There was a problem with the search query")

    return response.json(resp)
