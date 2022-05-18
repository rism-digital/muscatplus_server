import os.path
import tempfile

from sanic import Blueprint, response

from data_export_server.resources.opengraph import OpenGraph, OpenGraphSvg
from shared_helpers.resvg import render_svg
from shared_helpers.solr_connection import SolrConnection

opengraph_blueprint: Blueprint = Blueprint("opengraph", url_prefix="/og")


class SocialNetworks:
    TWITTER = "tw"
    FACEBOOK = "fb"


SOLR_FIELDS: list = [
    "id",
    "type",
    "main_title_s",
    "creator_name_s",
    "material_group_types_sm",
    "source_member_composers_sm",
    "num_holdings_i",
    "total_sources_i",
    "total_holdings_i",
    "shelfmark_s",
    "siglum_s",
    "institution_name_s",
    "name_s",
    "department_s",
    "city_s",
    "date_statement_s",
    "date_statements_sm"
]


async def render_og_tmpl(req, record_obj: dict) -> str:
    # The front-end server should have set this header. If it arrives here and it is
    # not set, then assume it's facebook.
    socialnetwork: str = req.headers.get("X-RO-Social", SocialNetworks.FACEBOOK)
    tmpl_vars: dict = OpenGraph(record_obj, context={"request": req}).data

    tmpl_vars.update({
        "socialnetwork": socialnetwork
    })
    source_tmpl = req.app.ctx.template_env.get_template("opengraph/card.html.j2")
    rendered_template = await source_tmpl.render_async(**tmpl_vars)

    return rendered_template


@opengraph_blueprint.route("/sources/<source_id:str>")
async def og_source(req, source_id: str) -> response.HTTPResponse:
    source_record: dict = SolrConnection.get(f"source_{source_id}", fields=SOLR_FIELDS, handler="/fetch")

    if not source_record:
        return response.text("Not Found.", status=404)

    resp: str = await render_og_tmpl(req, source_record)

    return response.html(resp)


@opengraph_blueprint.route("/people/<person_id:str>")
async def og_person(req, person_id: str):
    person_record: dict = SolrConnection.get(f"person_{person_id}", fields=SOLR_FIELDS, handler="/fetch")

    if not person_record:
        return response.text("Not Found.", status=404)

    resp: str = await render_og_tmpl(req, person_record)

    return response.html(resp)


@opengraph_blueprint.route("/institutions/<institution_id:str>")
async def og_institution(req, institution_id: str):
    institution_record: dict = SolrConnection.get(f"institution_{institution_id}", fields=SOLR_FIELDS, handler="/fetch")

    if not institution_record:
        return response.text("Not Found.", status=404)

    resp: str = await render_og_tmpl(req, institution_record)

    return response.html(resp)


@opengraph_blueprint.route("/img/<image_name:str>/")
async def og_image(req, image_name: str):
    cfg = req.app.ctx.config

    # If we've reached this point the frontend cache has passed it along,
    # indicating it doesn't have the file cached. We need to create it and
    # then send it. This means:
    #  1. Load the SVG template
    #  2. Load the Solr record
    #  3. Template the data from the Solr record to the SVG
    #  4. Create a tempfile to hold the png data
    #  5. Pass the SVG data to the `resvg` binary to create the PNG
    #  6. Save the PNG data to the tempfile
    #  7. Respond to the request with the PNG data.
    #  8. Delete the tempfile
    record_id: str = image_name.removesuffix(".png")
    record: dict = SolrConnection.get(record_id, fields=SOLR_FIELDS, handler="/fetch")

    tmpl_data: dict = OpenGraphSvg(record, context={"request": req}).data

    svg_tmpl = req.app.ctx.template_env.get_template("opengraph/card_image_template.svg.j2")
    rendered_svg: str = await svg_tmpl.render_async(**tmpl_data)

    # Create the temporary image file
    fd, tmpfile = tempfile.mkstemp()

    render_success: bool = render_svg(rendered_svg, tmpfile, cfg["social"]["resvg"], cfg["social"]["font_path"])
    if not render_success:
        return response.text("Failure to create image", status=500)

    # The tempfile should have the PNG data in it now.
    with os.fdopen(fd, 'rb') as t:
        pngdata = t.read()

    # we need to manually remove the temporary file.
    os.unlink(tmpfile)

    return response.raw(pngdata, content_type="image/png")