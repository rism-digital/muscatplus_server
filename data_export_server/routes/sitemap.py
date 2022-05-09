import math
import re

from sanic import Blueprint, response

from small_asc.client import Results
from shared_helpers.identifiers import get_site, ID_SUB
from shared_helpers.solr_connection import SolrConnection

sitemap_blueprint: Blueprint = Blueprint("sitemap")


@sitemap_blueprint.route("sitemap.xml")
async def sitemap_root(req):
    site: str = get_site(req)
    page_size: int = req.app.ctx.config["sitemap"]["pagesize"]

    solr_query = {
        "query": "*:*",
        "filter": ["type:person OR type:source OR type:institution"],
        "limit": 0,
        "params": {"q.op": "OR"},
    }
    res: Results = SolrConnection.search(solr_query, handler="/query")
    num_pages: int = math.ceil(res.hits / page_size)

    tmpl_vars = {
        "sitemap_pages": num_pages,
        "site": site
    }

    sitemap_root_tmpl = req.app.ctx.template_env.get_template("sitemaps/root.xml.j2")
    rendered_template = await sitemap_root_tmpl.render_async(**tmpl_vars)

    return response.text(rendered_template, content_type="application/xml")


@sitemap_blueprint.route("/sitemap-page.xml")
async def sitemap_page(req):
    page_num_param: str = req.args.get("pg", "1")
    try:
        page_num: int = int(page_num_param)
    except ValueError as e:
        page_num = 1

    if page_num < 1:
        page_num = 1

    cfg = req.app.ctx.config

    page_size: int = cfg["sitemap"]["pagesize"]
    offset: int = 0 if page_num == 1 else ((page_num - 1) * page_size)

    solr_query = {
        "query": "*:*",
        "filter": ["type:person OR type:source OR type:institution"],
        "limit": page_size,
        "offset": offset,
        "params": {"q.op": "OR"},
        "fields": ["id", "type", "created", "updated"],
        "sort": "created asc"
    }

    res: Results = SolrConnection.search(solr_query, handler="/query")
    site: str = get_site(req)

    urlentries: list = []
    for result in res:
        restype: str = result.get("type")
        resid: str = re.sub(ID_SUB, "", result.get("id"))

        url: str
        if restype == "source":
            url = f"{site}/sources/{resid}"
        elif restype == "person":
            url = f"{site}/people/{resid}"
        elif restype == "institution":
            url = f"{site}/institutions/{resid}"
        else:
            continue

        urlentries.append({
            "url": url,
            "updated": result.get("updated")
        })

    tmpl_vars = {
        "urlentries": urlentries,
    }

    sitemap_tmpl = req.app.ctx.template_env.get_template("sitemaps/sitemap.xml.j2")
    rendered_template = await sitemap_tmpl.render_async(**tmpl_vars)

    return response.text(rendered_template, content_type="application/xml")
