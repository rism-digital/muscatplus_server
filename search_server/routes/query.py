from sanic import Blueprint

from search_server.request_handlers import handle_search
from search_server.resources.search.probe import handle_probe_request
from search_server.resources.search.search import handle_search_request
from search_server.resources.suggest.suggest import handle_suggest_request

query_blueprint: Blueprint = Blueprint("query")


# The main search interface request handler.
@query_blueprint.route("/search/")
async def search(req):
    return await handle_search(req, handle_search_request)


# The Suggest request is available on specific fields (configured as query fields).
# This uses the Solr TermComponent interface to suggest terms for use in an autocomplete
# lookup.
@query_blueprint.route("/suggest/")
async def suggest(req):
    return await handle_suggest_request(req)


# A Probe request will perform a search, so it has all of the functionality
# of the /search/ handler. The only difference is that it will not return any
# actual results. It will return the total number of results, and any facets or
# modes that would be active for a given search query.
@query_blueprint.route("/probe/")
async def probe(req):
    return await handle_search(req, handle_probe_request)
