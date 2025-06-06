
import orjson
from sanic import response
from small_asc.client import JsonAPIRequest, Results

from search_server.helpers.vrv import (
    create_pae_from_request,
    render_mei,
    render_pae,
    render_png,
    validate_pae,
)
from search_server.resources.incipits.incipit import Incipit, IncipitsSection
from shared_helpers.solr_connection import SolrConnection, SolrResult


async def _fetch_incipit(record_id: str, record_type: str, work_num: str) -> SolrResult | None:
    filters = ["type:incipit", f"work_num_s:{work_num}", "parent_type_s:source"]

    # For future use -- should only be source record type now.
    if record_type == "work":
        filters.append(f"work_id:work_{record_id}")
    else:
        filters.append(f"source_id:source_{record_id}")

    json_request: JsonAPIRequest = {
        "query": "*:*",
        "filter": filters,
        "sort": "work_num_ans asc",
        "limit": 1,
    }
    record: Results = await SolrConnection.search(json_request)

    if record.hits == 0:
        return None

    return record.docs[0]


async def handle_incipits_list_request(req, source_id: str) -> dict | None:
    json_request: JsonAPIRequest = {
        "query": "*:*",
        "filter": ["type:source",
                   f"id:source_{source_id}",
                   "has_incipits_b:true"],
    }

    record: Results = await SolrConnection.search(json_request)

    if record.hits == 0:
        return None

    return await IncipitsSection(
        record.docs[0], context={"request": req, "direct_request": True}
    ).serialized


async def handle_incipit_request(req, record_id: str, record_type: str, work_num: str) -> dict | None:
    incipit_record: SolrResult | None = await _fetch_incipit(record_id, record_type, work_num)

    if not incipit_record:
        return None

    return await Incipit(
        incipit_record,
        context={
            "request": req,
            "direct_request": True
        }
    ).serialized


async def handle_mei_download(req, record_id: str, record_type: str, work_num: str) -> dict | None:
    """
    Handle MEI file download for a given incipit. Returns a dictionary containing the
    attachment filename and the MEI content sent in the body of the response.
    """
    incipit_record: SolrResult | None = await _fetch_incipit(record_id, record_type, work_num)

    if not incipit_record:
        return None

    if "music_incipit_s" not in incipit_record:
        return None

    filename: str = f"rism-{record_type}-{record_id}-{work_num}.mei"
    response_headers: dict = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Content-Type": "application/mei+xml",
    }

    mei_content: str | None = render_mei(req, incipit_record)
    if not mei_content:
        return None

    return {"headers": response_headers, "content": mei_content}


async def handle_png_download(req, record_id: str, record_type: str, work_num: str) -> dict | None:
    incipit_record: SolrResult | None = await _fetch_incipit(record_id, record_type, work_num)

    if not incipit_record:
        return None

    if "original_pae_sni" not in incipit_record:
        return None

    filename: str = f"rism-{record_type}-{record_id}-{work_num}.png"
    response_headers: dict = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Content-Type": "image/png",
    }

    png_content: bytes | None = render_png(req, incipit_record["original_pae_sni"])
    if not png_content:
        return None

    return {"headers": response_headers, "content": png_content}


async def handle_incipit_render(req) -> response.HTTPResponse:
    """Takes an incoming string and runs it through Verovio to render as notation. Requests use the `?n=` query
    parameter as required notation input.

    Other optional parameters that may be used include:
     - ic: clef (default: G-2)
     - it: time signature (default: 4/4)
     - ik: key signature (default: no sharps, no flats -- key of C major)

    (This is the same as the request parameters for the incipit search)

    Returns SVG in the body of the response
    """
    pae: str = create_pae_from_request(req)

    # Generate random IDs to avoid ID collisions on the page.
    rendered_pae: tuple | None = render_pae(pae, use_crc=False, enlarged=True)
    if not rendered_pae:
        return response.json(
            {"message": "There was a problem rendering the Plaine and Easie notation"}, status=500
        )

    svg, _ = rendered_pae
    return response.text(svg, content_type="image/svg+xml;charset=utf8")


async def handle_incipit_validate(req) -> response.HTTPResponse:
    data_obj: dict = validate_pae(req)

    return response.json(
        data_obj,
        content_type="application/json; charset=utf-8",
        option=orjson.OPT_INDENT_2 if req.app.ctx.config["common"]["debug"] else 0,
    )
