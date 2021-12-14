import logging

from sanic import response
from small_asc.client import Results, SolrError

from search_server.exceptions import InvalidQueryException
from search_server.helpers.search_request import SearchRequest
from search_server.helpers.solr_connection import SolrConnection
from search_server.resources.search.search_results import SearchResults

log = logging.getLogger(__name__)


async def handle_search_request(req) -> response.HTTPResponse:
    try:
        request_compiler: SearchRequest = SearchRequest(req)
        solr_params: dict = request_compiler.compile()
    except InvalidQueryException as e:
        return response.text(f"Invalid search query. {e}", status=400)

    try:
        solr_res: Results = SolrConnection.search(solr_params)
    except SolrError:
        error_message: str = "Error parsing search parameters"
        log.exception(error_message)
        return response.text(f"Search error", status=500)

    search_results: dict = SearchResults(solr_res,
                                         context={"request": req,
                                                  "query_pae_features": request_compiler.pae_features,
                                                  "direct_request": True}).data

    response_headers: dict = {
        "Content-Type": "application/ld+json; charset=utf-8"
    }

    return response.json(
        search_results,
        headers=response_headers,
        escape_forward_slashes=False,
        indent=(4 if req.app.ctx.config['common']['debug'] else 0)
    )
