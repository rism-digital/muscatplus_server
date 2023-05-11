import re
from typing import Optional

from sanic import Blueprint, response
from small_asc.client import Results

from shared_helpers.identifiers import ID_SUB
from shared_helpers.solr_connection import SolrConnection

sigla_blueprint: Blueprint = Blueprint("sigla", url_prefix="/sigla")


async def handle_institution_sigla_request(req, siglum: str) -> Optional[str]:
    fq: list = ["type:institution", f"siglum_s:{siglum}"]
    institution_record: Results = await SolrConnection.search({"query": "*:*",
                                                               "filter": fq,
                                                               "fields": ["id"]})

    if institution_record.hits == 0:
        return None

    institution_record_id: str = institution_record.docs[0]["id"]
    institution_id = re.sub(ID_SUB, "", institution_record_id)
    return f"/institutions/{institution_id}"


@sigla_blueprint.route("/<siglum:str>")
async def siglum_redirect(req, siglum: str):
    resp: Optional[str] = await handle_institution_sigla_request(req, siglum)
    if resp:
        return response.redirect(resp, status=303)
    else:
        return response.text(f"An institution with the siglum {siglum} was not found.", status=404)
