import logging
from typing import Optional

import sentry_sdk
import yaml
from sanic import Sanic, response
from sentry_sdk.integrations.sanic import SanicIntegration

from search_server.helpers.identifiers import RISM_JSONLD_CONTEXT
from search_server.helpers.languages import load_translations
from search_server.resources.front.front import handle_front_request
from search_server.routes.countries import countries_blueprint
from search_server.routes.festivals import festivals_blueprint
from search_server.routes.incipits import incipits_blueprint
from search_server.routes.institutions import institutions_blueprint
from search_server.routes.people import people_blueprint
from search_server.routes.places import places_blueprint
from search_server.routes.query import query_blueprint
from search_server.routes.sources import sources_blueprint
from search_server.routes.subjects import subjects_blueprint

config: dict = yaml.safe_load(open('configuration.yml', 'r'))
debug_mode: bool = config['common']['debug']

sentry_sdk.init(
    dsn=config["sentry"]["dsn"],
    integrations=[SanicIntegration()],
    environment=config["sentry"]["environment"]
)

# When debug mode is False, also disable the access log, and vice-versa (Debug mode also enables access_logs)
app = Sanic("mp_server")


# a workaround for Sanic path handling; can be removed if the handling is changed.
def nonempty_str(value: str) -> str:
    if not value:
        raise ValueError
    return value


# Registers a string route handler that will *not* match on an empty string.
app.router.register_pattern(
    "nestr",
    nonempty_str,
    r"^[^/]+$"  # noqa
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
app.blueprint(query_blueprint)

app.config.FORWARDED_SECRET = config['common']['secret']
app.config.KEEP_ALIVE_TIMEOUT = 75  # matches nginx default keepalive

if debug_mode:
    LOGLEVEL = logging.DEBUG
else:
    LOGLEVEL = logging.WARNING

logging.basicConfig(format="[%(asctime)s] [%(levelname)8s] %(message)s (%(filename)s:%(lineno)s)",
                    level=LOGLEVEL)

log = logging.getLogger(__name__)

translations: Optional[dict] = load_translations("locales/")
if not translations:
    log.critical("No translations can be loaded.")

app.ctx.translations = translations

context_uri: bool = config['common']['context_uri']
app.ctx.context_uri = context_uri

# Make the application configuration object available in the app context
app.ctx.config = config


@app.route("/")
async def front(req):
    return await handle_front_request(req)


@app.route("/api/v1/context.json")
async def context(req) -> response.HTTPResponse:
    return response.json(RISM_JSONLD_CONTEXT)
