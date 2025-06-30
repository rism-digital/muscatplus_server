import logging

import orjson
import yaml
from sanic import Sanic, response
from sanic.exceptions import NotFound, ServerError

from search_server.resources.front.front import handle_front_request
from search_server.routes.api import api_blueprint
from search_server.routes.countries import countries_blueprint
from search_server.routes.external import external_blueprint
from search_server.routes.festivals import festivals_blueprint
from search_server.routes.incipits import incipits_blueprint
from search_server.routes.institutions import institutions_blueprint
from search_server.routes.people import people_blueprint
from search_server.routes.places import places_blueprint
from search_server.routes.publications import publications_blueprint
from search_server.routes.query import query_blueprint
from search_server.routes.sigla import sigla_blueprint
from search_server.routes.sources import sources_blueprint
from search_server.routes.subjects import subjects_blueprint
from search_server.routes.works import works_blueprint
from shared_helpers.languages import (
    SUPPORTED_LANGUAGES,
    filter_languages,
    load_translations,
)
from shared_helpers.solr_connection import SolrConnection

config: dict = yaml.safe_load(open("configuration.yml"))  # noqa: SIM115
debug_mode: bool = config["common"]["debug"]
version_string: str = config["common"]["version"]
release: str = ""

# If we have semver then remove the leading 'v', e.g., 'v1.1.1' -> '1.1.1'
# The full release string would then be 'muscatplus_server@1.1.1'
# Otherwise, use the version string verbatim, e.g., 'muscatplus_server@development'.
release = version_string[1:] if version_string.startswith("v") else version_string

app = Sanic("mp_server", dumps=orjson.dumps)


@app.listener("before_server_start")
async def init_sentry(_):
    if debug_mode:
        return

    import sentry_sdk
    from sentry_sdk.integrations.asyncio import AsyncioIntegration

    sentry_sdk.init(
        dsn=config["sentry"]["api"]["dsn"],
        environment=config["sentry"]["environment"],
        release=f"muscatplus_server@{release}",
        integrations=[AsyncioIntegration()],
    )


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
app.blueprint(publications_blueprint)

app.config.FORWARDED_SECRET = config["common"]["secret"]
app.config.KEEP_ALIVE_TIMEOUT = 75  # matches nginx default keepalive

LOGLEVEL = logging.DEBUG if debug_mode else logging.ERROR

logging.basicConfig(
    format="[%(asctime)s] [%(levelname)8s] %(message)s (%(filename)s:%(lineno)s)",
    level=LOGLEVEL,
)

log = logging.getLogger("mp_server")

translations: dict = load_translations("locales/")
if not translations:
    log.critical("No translations can be loaded.")

app.ctx.translations = translations

context_uri: bool = config["common"]["context_uri"]
app.ctx.context_uri = context_uri

# Make the application configuration object available in the app context
app.ctx.config = config


@app.on_request
def do_language_negotiation(req) -> None:
    """
    This looks for the presence of the X-API-Accept-Language request header, with values
    of one or more language codes or "*". If those language codes map to ones that are
    supported in RISM Online, then the full dictionary of translations is filtered to only
    include the requested languages.

    Serializers will then use the filtered translations dictionary on the request to produce
    the translated values.

    This process is run here so that it only runs once on each request.

    :param req: A Sanic Request object
    :return: None
    """
    lang_header = req.headers.get("X-API-Accept-Language")

    if not lang_header or lang_header == "*":
        log.debug("No language negotiation" if not lang_header else "All languages negotiated")
        accepted = SUPPORTED_LANGUAGES
    else:
        requested = {lang.strip() for lang in lang_header.split(",")}
        accepted = requested & SUPPORTED_LANGUAGES

        if not accepted:
            log.debug("No acceptable language values requested")
            accepted = SUPPORTED_LANGUAGES
        else:
            log.debug("Filtering languages %s", accepted)

    req.ctx.accepted_languages = list(accepted)
    req.ctx.translations = (
        translations if accepted == SUPPORTED_LANGUAGES else filter_languages(accepted, translations)
    )


@app.route("/")
async def front(req):
    return await handle_front_request(req)


@app.route("/about")
async def about(req) -> response.JSONResponse:
    cfg: dict = req.app.ctx.config
    idx_result: dict | None = await SolrConnection.get("rism-online-index-info")  # type: ignore

    # If, for some reason, we don't have a result for the last indexed
    # value, then return Jan 1, 1970.
    if idx_result:
        lastidx = idx_result["indexed"]
        idxversion = idx_result["indexer_version_sni"]
        diamm_records = idx_result.get("diamm_latest_dt")
        cantus_records = idx_result.get("cantus_latest_dt")
    else:
        lastidx = "1970-01-01T00:00:00.000Z"
        idxversion = "unknown"
        diamm_records = "1970-01-01T00:00:00.000Z"
        cantus_records = "1970-01-01T00:00:00.000Z"

    resp: dict = {
        "serverVersion": cfg["common"]["version"],
        "indexerVersion": idxversion,
        "lastIndexed": lastidx,
        "latestFromDIAMM": diamm_records,
        "latestFromCantus": cantus_records,
    }

    return response.json(resp)


@app.exception(NotFound, ServerError)
async def json_error(req, exc) -> response.HTTPResponse:
    return response.json({"message": exc.message})
