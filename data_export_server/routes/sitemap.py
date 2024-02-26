import math
import re
from typing import Optional

from sanic import Blueprint, response

from small_asc.client import Results
from shared_helpers.identifiers import get_site, ID_SUB, get_url_from_type
from shared_helpers.solr_connection import SolrConnection

sitemap_blueprint: Blueprint = Blueprint("sitemap")


@sitemap_blueprint.route("sitemap.xml")
async def sitemap_root(req):
    site: str = get_site(req)
    page_size: int = req.app.ctx.config["sitemap"]["pagesize"]

    solr_query = {
        "query": "*:*",
        "filter": ["type:person OR type:source OR type:institution", "!project_s:[* TO *]"],
        "limit": 0
    }
    res: Results = await SolrConnection.search(solr_query, handler="/query")
    num_pages: int = math.ceil(res.hits / page_size)

    tmpl_vars = {
        "sitemap_pages": num_pages,
        "site": site
    }

    sitemap_root_tmpl = req.app.ctx.template_env.get_template("sitemaps/root.xml.j2")
    rendered_template = sitemap_root_tmpl.render(**tmpl_vars)

    return response.text(rendered_template, content_type="application/xml")


@sitemap_blueprint.route(r"/<page_num:sitemap-page-(?P<page_num>\d+)\.xml>")
async def sitemap_page(req, page_num: str):
    try:
        pnum: int = int(page_num)
    except ValueError as e:
        pnum = 1

    if pnum < 1:
        pnum = 1

    cfg = req.app.ctx.config

    page_size: int = cfg["sitemap"]["pagesize"]
    offset: int = 0 if pnum == 1 else ((pnum - 1) * page_size)

    solr_query = {
        "query": "*:*",
        "filter": ["type:person OR type:source OR type:institution", "!project_s:[* TO *]"],
        "limit": page_size,
        "offset": offset,
        "fields": ["id", "type", "created", "updated"],
        "sort": "created asc"
    }

    res: Results = await SolrConnection.search(solr_query, handler="/query")

    urlentries: list = []
    for result in res.docs:
        restype: str = result["type"]
        resid: str = re.sub(ID_SUB, "", result["id"])

        url: Optional[str] = get_url_from_type(req, restype, resid)
        if not url:
            continue

        urlentries.append({
            "url": url,
            "updated": result.get("updated")
        })

    tmpl_vars = {
        "urlentries": urlentries,
    }

    sitemap_tmpl = req.app.ctx.template_env.get_template("sitemaps/sitemap.xml.j2")
    rendered_template = sitemap_tmpl.render(**tmpl_vars)

    return response.text(rendered_template, content_type="application/xml")
