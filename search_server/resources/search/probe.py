import logging

from search_server.exceptions import InvalidQueryException
from search_server.helpers.search_request import SearchRequest
from search_server.resources.search.base_search import serialize_response
from search_server.resources.search.search_results import SearchResults

log = logging.getLogger("mp_server")


async def handle_probe_request(req) -> dict:
    try:
        request_compiler: SearchRequest = SearchRequest(req, probe=True)
        solr_params: dict = request_compiler.compile()
    except InvalidQueryException:
        raise

    extra_context: dict = {
        "query_pae_features": request_compiler.pae_features,
        "direct_request": True,
        "probe_request": True,
        "query_validation": request_compiler.query_report,
    }

    return await serialize_response(req, solr_params, SearchResults, extra_context)
