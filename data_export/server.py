import re
from typing import Pattern

import sentry_sdk
import yaml
from jinja2 import Environment, PackageLoader, select_autoescape
from sanic import Sanic, response
from small_asc.client import Solr, Results
import math

app = Sanic("mp_dataexport")
config: dict = yaml.safe_load(open('configuration.yml', 'r'))
debug_mode: bool = config["common"]["debug"]

if debug_mode is False:
    from sentry_sdk.integrations.sanic import SanicIntegration
    sentry_sdk.init(
        dsn=config["sentry"]["dsn"],
        integrations=[SanicIntegration()],
        environment=config["sentry"]["environment"]
    )

solr_url = config['solr']['server']
SolrConnection: Solr = Solr(solr_url)

template_env = Environment(
    loader=PackageLoader('data_export', 'templates'),
    autoescape=select_autoescape(['xml']),
    enable_async=True
)

sitemap_root_template = template_env.get_template("sitemaps/root.xml.j2")
sitemap_template = template_env.get_template("sitemaps/sitemap.xml.j2")

ID_SUB: Pattern = re.compile(r"source_|person_|institution_")


def get_site(req) -> str:
    """
    Takes a request object, parses it out, and returns the base URL for the site.
    Works even behind a proxy by looking at the X-Forwarded headers.

    Does NOT add a trailing slash.

    :param req: A Sanic request object
    :return: A templated string
    """
    fwd_scheme_header = req.headers.get('X-Forwarded-Proto')
    fwd_host_header = req.headers.get('X-Forwarded-Host')

    scheme: str = fwd_scheme_header if fwd_scheme_header else req.scheme
    server: str = fwd_host_header if fwd_host_header else req.host

    return f"{scheme}://{server}"


@app.route("/sources/<source_id:str>/")
def source(req, source_id: str) -> response.HTTPResponse:
    return response.text("Hello Twitter.")


@app.route("/sitemap.xml")
async def sitemap_root(req):
    site: str = get_site(req)
    page_size: int = config["sitemap"]["pagesize"]

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

    rendered_template = await sitemap_root_template.render_async(**tmpl_vars)

    return response.text(rendered_template, content_type="application/xml")


@app.route("/sitemap-page.xml")
async def sitemap_page(req):
    page_num_param: str = req.args.get("pg", "1")
    try:
        page_num: int = int(page_num_param)
    except ValueError as e:
        page_num = 1

    if page_num < 1:
        page_num = 1

    page_size: int = config["sitemap"]["pagesize"]
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

    rendered_template = await sitemap_template.render_async(**tmpl_vars)

    return response.text(rendered_template, content_type="application/xml")
