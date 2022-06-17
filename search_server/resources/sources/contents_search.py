from search_server.exceptions import InvalidQueryException

from search_server.helpers.search_request import SearchRequest
from search_server.resources.search.base_search import serialize_response
from search_server.resources.search.search_results import SearchResults


async def handle_contents_search_request(req, source_id: str) -> dict:
    this_id: str = f"source_{source_id}"

    try:
        request_compiler: SearchRequest = SearchRequest(req)
        request_compiler.filters += ["type:source",
                                     "is_contents_record_b:true",
                                     f"source_membership_id:{this_id}",
                                     f"!id:{this_id}"]
        solr_params: dict = request_compiler.compile()
    except InvalidQueryException as e:
        raise

    extra_context: dict = {"direct_request": True}

    return serialize_response(req, solr_params, SearchResults, extra_context)


async def handle_contents_probe_request(req, source_id: str) -> dict:
    this_id: str = f"source_{source_id}"

    try:
        request_compiler: SearchRequest = SearchRequest(req, probe=True)
        request_compiler.filters += ["type:source",
                                     "is_contents_record_b:true",
                                     f"source_membership_id:{this_id}",
                                     f"!id:{this_id}"]
        solr_params: dict = request_compiler.compile()
    except InvalidQueryException as e:
        raise

    extra_context: dict = {"direct_request": True}

    return serialize_response(req, solr_params, SearchResults, extra_context)
