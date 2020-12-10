import logging

import pysolr
from sanic import response

from search_server.exceptions import InvalidQueryException
from search_server.helpers.search_request import SearchRequest
from search_server.helpers.solr_connection import SolrConnection
from search_server.resources.search.search_results import SearchResults

log = logging.getLogger(__name__)


async def handle_search_request(req) -> response.HTTPResponse:
    request_compiler = SearchRequest(req)
    request_compiler.filters += ["type:source OR type:person OR type:institution"]

    try:
        solr_params = request_compiler.compile()
    except InvalidQueryException as e:
        return response.text(f"Invalid search query. {e}", status=400)

    try:
        solr_res: pysolr.Results = SolrConnection.search(**solr_params)
    except pysolr.SolrError:
        error_message: str = "Error parsing search parameters"
        log.exception(error_message)
        return response.text(f"Search error", status=500)

    search_results = SearchResults(solr_res, context={"request": req})

    return response.json(search_results.data)
