from search_server.exceptions import InvalidQueryException
from search_server.helpers.search_request import SearchRequest
from search_server.resources.search.base_search import serialize_response
from search_server.resources.search.search_results import SearchResults
from shared_helpers.solr_connection import is_composite


async def _get_normal_results(req, source_id: str) -> dict:
    try:
        request_compiler: SearchRequest = SearchRequest(req, is_contents=True)
        request_compiler.filters += [
            "type:source",
            "is_contents_record_b:true",
            f"source_membership_id:{source_id}",
            f"!id:{source_id}",
        ]
        solr_params: dict = request_compiler.compile()
    except InvalidQueryException:
        raise

    extra_context: dict = {"direct_request": True, "is_contents": True}

    return await serialize_response(req, solr_params, SearchResults, extra_context)


async def _get_composite_results(req, source_id: str) -> dict:
    try:
        request_compiler: SearchRequest = SearchRequest(req, is_contents=True)
        request_compiler.filters += [
            "type:source OR type:holding",
            f"source_membership_id:{source_id} OR composite_parent_id:{source_id}",
            f"!id:{source_id}",
        ]

        # NB: The sort parameter is handled internally from the configuration
        # so we don't need to manually set it here.
        solr_params: dict = request_compiler.compile()
    except InvalidQueryException:
        raise

    extra_context: dict = {
        "direct_request": True,
        "is_composite": True,
        "is_contents": True,
    }

    return await serialize_response(req, solr_params, SearchResults, extra_context)


async def handle_contents_search_request(req, source_id: str) -> dict:
    this_id: str = f"source_{source_id}"
    # Since we don't know if this source is a composite source or not,
    # we first do a quick check.
    is_comp: bool = await is_composite(this_id)

    # There are two paths for a source: The "normal" path, and the path
    # to take if the source is a composite volume, since composites need
    # special handling.
    if not is_comp:
        return await _get_normal_results(req, this_id)
    else:
        return await _get_composite_results(req, this_id)


async def handle_contents_probe_request(req, source_id: str) -> dict:
    this_id: str = f"source_{source_id}"

    try:
        request_compiler: SearchRequest = SearchRequest(req, probe=True)
        request_compiler.filters += [
            "type:source",
            "is_contents_record_b:true",
            f"source_membership_id:{this_id}",
            f"!id:{this_id}",
        ]
        solr_params: dict = request_compiler.compile()
    except InvalidQueryException:
        raise

    extra_context: dict = {"direct_request": True}

    return await serialize_response(req, solr_params, SearchResults, extra_context)
