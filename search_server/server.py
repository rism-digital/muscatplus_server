import logging
from typing import Optional

import orjson
import sentry_sdk
import yaml
from sanic import Sanic, response
from small_asc.client import Results

from search_server.resources.front.front import handle_front_request
from search_server.routes.api import api_blueprint
from search_server.routes.countries import countries_blueprint
from search_server.routes.external import external_blueprint
from search_server.routes.festivals import festivals_blueprint
from search_server.routes.incipits import incipits_blueprint
from search_server.routes.institutions import institutions_blueprint
from search_server.routes.people import people_blueprint
from search_server.routes.places import places_blueprint
from search_server.routes.query import query_blueprint
from search_server.routes.sigla import sigla_blueprint
from search_server.routes.sources import sources_blueprint
from search_server.routes.subjects import subjects_blueprint
from search_server.routes.works import works_blueprint
from shared_helpers.languages import load_translations, negotiate_languages
from shared_helpers.solr_connection import SolrConnection

config: dict = yaml.safe_load(open("configuration.yml"))  # noqa: SIM115
debug_mode: bool = config["common"]["debug"]
version_string: str = config["common"]["version"]
release: str = ""

# If we have semver then remove the leading 'v', e.g., 'v1.1.1' -> '1.1.1'
# The full release string would then be 'muscatplus_server@1.1.1'
# Otherwise, use the version string verbatim, e.g., 'muscatplus_server@development'.
release = version_string[1:] if version_string.startswith("v") else version_string

if debug_mode is False:
    from sentry_sdk.integrations.sanic import SanicIntegration

    sentry_sdk.init(
        dsn=config["sentry"]["api"]["dsn"],
        integrations=[SanicIntegration()],
        environment=config["sentry"]["environment"],
        release=f"muscatplus_server@{release}",
    )

app = Sanic("mp_server", dumps=orjson.dumps)

# register routes with their blueprints
app.blueprint(sources_blueprint)
app.blueprint(people_blueprint)
app.blueprint(places_blueprint)
app.blueprint(institutions_blueprint)
app.blueprint(subjects_blueprint)
app.blueprint(incipits_blueprint)
app.blueprint(festivals_blueprint)
app.blueprint(countries_blueprint)
app.blueprint(works_blueprint)
app.blueprint(query_blueprint)
app.blueprint(api_blueprint)
app.blueprint(external_blueprint)
app.blueprint(sigla_blueprint)

app.config.FORWARDED_SECRET = config["common"]["secret"]
app.config.KEEP_ALIVE_TIMEOUT = 75  # matches nginx default keepalive

LOGLEVEL = logging.DEBUG if debug_mode else logging.ERROR

logging.basicConfig(
    format="[%(asctime)s] [%(levelname)8s] %(message)s (%(filename)s:%(lineno)s)",
    level=LOGLEVEL,
)

log = logging.getLogger("mp_server")

translations: Optional[dict] = load_translations("locales/")
if not translations:
    log.critical("No translations can be loaded.")

app.ctx.translations = translations

context_uri: bool = config["common"]["context_uri"]
app.ctx.context_uri = context_uri

# Make the application configuration object available in the app context
app.ctx.config = config


@app.on_request
def do_language_negotiation(req):
    """
    Performs language negotiation on every request. This looks for the presence of the
    X-API-Accept-Language request header, with values of one or more language codes or "*".
    If those language codes map to ones that are supported in RISM Online, then the full
    dictionary of translations is filtered to only include the requested languages.

    Serializers will then use the filtered translations dictionary on the request to produce
    the translated values.

    This process is run here so that it only runs once on each request.

    :param req: A Sanic Request object
    :return: None
    """
    req.ctx.translations = negotiate_languages(req, translations)


@app.route("/")
async def front(req):
    return await handle_front_request(req)


@app.route("/about")
async def about(req):
    cfg: dict = req.app.ctx.config
    sort: str = "indexed desc"
    idx_results: Results = await SolrConnection.search(
        {
            "query": "*:*",
            "filter": ["type:indexer"],
            "sort": sort,
            "limit": 1,
            "fields": ["indexed", "indexer_version_sni"],
        }
    )

    # If, for some reason, we don't have a result for the last indexed
    # value, then return Jan 1, 1970.
    if idx_results.hits > 0:
        lastidx = idx_results.docs[0]["indexed"]
        idxversion = idx_results.docs[0]["indexer_version_sni"]
    else:
        lastidx = "1970-01-01T00:00:00.000Z"
        idxversion = "unknown"

    resp: dict = {
        "serverVersion": cfg["common"]["version"],
        "indexerVersion": idxversion,
        "lastIndexed": lastidx,
    }

    return response.json(resp)
