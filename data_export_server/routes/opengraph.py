from sanic import Blueprint, response

from shared_helpers.solr_connection import SolrConnection

opengraph_blueprint: Blueprint = Blueprint("opengraph", url_prefix="/og")


class SocialNetworks:
    TWITTER = "tw"
    FACEBOOK = "fb"


@opengraph_blueprint.route("/sources/<source_id:str>")
async def og_source(req, source_id: str) -> response.HTTPResponse:
    source_record = SolrConnection.get(f"source_{source_id}")

    if not source_record:
        return response.text("Not Found.", status=404)



    # The front-end server should have set this header. If it arrives here and it is
    # not set, then assume it's facebook.
    socialnetwork: str = req.headers.get("X-RO-Social", SocialNetworks.FACEBOOK)

    if socialnetwork == SocialNetworks.TWITTER:
        source_tmpl_name = "twitter/tw_source.html.j2"
    else:
        source_tmpl_name = "facebook/fb_source.html.j2"

    source_tmpl = req.app.ctx.template_env.get_template(source_tmpl_name)
    rendered_template = await source_tmpl.render_async()

    return response.html(rendered_template)


@opengraph_blueprint.route("/people/<person_id:str>")
def og_person(req, person_id: str):
    pass


@opengraph_blueprint.route("/institutions/<institution_id:str>")
def og_institution(req, institution_id: str):
    pass
