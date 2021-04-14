import logging
from typing import Dict

import pysolr
from sanic import response

from search_server.exceptions import InvalidQueryException
from search_server.helpers.search_request import SearchRequest
from search_server.helpers.solr_connection import SolrConnection
from search_server.resources.search.search_results import SearchResults

log = logging.getLogger(__name__)


async def handle_search_request(req) -> response.HTTPResponse:
    try:
        request_compiler = SearchRequest(req)
    except InvalidQueryException as e:
        return response.text(f"Invalid search query. {e}", status=400)

    solr_params: Dict = request_compiler.compile()

    try:
        solr_res: pysolr.Results = SolrConnection.search(**solr_params)
    except pysolr.SolrError:
        error_message: str = "Error parsing search parameters"
        log.exception(error_message)
        return response.text(f"Search error", status=500)

    search_results: Dict = SearchResults(solr_res, context={"request": req}).data

    return response.json(search_results)
