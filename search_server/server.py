import asyncio
import logging
from typing import Dict, Optional

import uvloop
import yaml
from sanic import Sanic, response

from search_server.helpers.identifiers import RISM_JSONLD_CONTEXT
from search_server.helpers.languages import load_translations
from search_server.request_handlers import handle_search_request
from search_server.resources.search.search import handle_search_request
from search_server.resources.siglum.sigla import handle_sigla_request
from search_server.routes.festivals import festivals_blueprint
from search_server.routes.incipits import incipits_blueprint
from search_server.routes.institutions import institutions_blueprint
from search_server.routes.people import people_blueprint
from search_server.routes.places import places_blueprint
from search_server.routes.sources import sources_blueprint
from search_server.routes.subjects import subjects_blueprint

config: Dict = yaml.safe_load(open('configuration.yml', 'r'))
app = Sanic("search_server")

# register routes with their blueprints
app.blueprint(sources_blueprint)
app.blueprint(people_blueprint)
app.blueprint(places_blueprint)
app.blueprint(institutions_blueprint)
app.blueprint(subjects_blueprint)
app.blueprint(incipits_blueprint)
app.blueprint(festivals_blueprint)

# Make the configuration globally available in the app instance.
app.config.update(config)

debug_mode: bool = config['common']['debug']
context_uri: bool = config['common']['context_uri']

if debug_mode:
    LOGLEVEL = logging.DEBUG
else:
    LOGLEVEL = logging.WARNING
    asyncio.set_event_loop(uvloop.new_event_loop())

logging.basicConfig(format="[%(asctime)s] [%(levelname)8s] %(message)s (%(filename)s:%(lineno)s)",
                    level=LOGLEVEL)

log = logging.getLogger("mp_server")

translations: Optional[Dict] = load_translations("locales/")
if not translations:
    log.critical("No translations can be loaded.")

app.translations = translations
app.context_uri = context_uri


@app.middleware('response')
async def add_cors(req, resp):
    resp.headers['access-control-allow-origin'] = "*"


@app.route("/")
async def root(req):
    return response.json({"message": "Hello World"})


@app.route("/api/v1/context.json")
async def context(req) -> response.HTTPResponse:
    return response.json(RISM_JSONLD_CONTEXT)


@app.route("/sigla/")
async def sigla(req):
    return await handle_search_request(req, handle_sigla_request)


@app.route("/search/")
async def search(req):
    return await handle_search_request(req)
