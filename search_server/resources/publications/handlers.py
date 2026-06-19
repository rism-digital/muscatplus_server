from sanic import request
from sanic.log import logger
from small_asc.client import JsonAPIRequest, SolrError

from search_server.exceptions import InvalidQueryException
from search_server.helpers.search_request import SearchRequest
from search_server.helpers.solr_connection import SolrConnection
from search_server.resources.publications.publication import Publication
from search_server.resources.publications.publication_list import PublicationList
from search_server.resources.publications.publications_search import WorkResults
from search_server.resources.search.base_search import serialize_response


async def handle_publication_request(req, publication_id: str) -> dict | None:
    publication_record: dict | None = await SolrConnection.get(
        f"publication_{publication_id}"
    )  # type: ignore

    if not publication_record:
        return None

    return await Publication(
        publication_record, context={"request": req, "direct_request": True}
    ).serialized


def _prepare_query(
    req, publication_id: str, probe: bool = False
) -> tuple[JsonAPIRequest, dict | None]:
    try:
        request_compiler = SearchRequest(req, probe=probe)
        request_compiler.filters += [
            "type:work",
            f"catalogue_id:publication_{publication_id} OR secondary_catalogue_ids:publication_{publication_id}",
        ]
        request_compiler.sorts += ["number_page_ans asc"]
        # NB: this value is supposed to be a string!
        solr_params: JsonAPIRequest = request_compiler.compile()

    except InvalidQueryException as e:
        logger.exception("Invalid query: %s", e)
        raise

    return solr_params, request_compiler.query_report


async def handle_publication_search_request(req, publication_id: str) -> dict:
    try:
        solr_params, query_report = _prepare_query(req, publication_id)
    except InvalidQueryException:
        raise

    extra_context: dict = {
        "direct_request": True,
        "query_validation": query_report,
    }

    try:
        result_data: dict = await serialize_response(
            req, solr_params, WorkResults, extra_context
        )
    except SolrError:
        raise

    return result_data


async def handle_publication_list_request(req) -> dict | None:
    return await PublicationList({}, context={"request": req}).serialized


async def handle_publication_probe_request(
    req: request.Request, publication_id: str
) -> dict:
    try:
        solr_params, query_report = _prepare_query(req, publication_id, probe=True)
    except InvalidQueryException:
        raise

    extra_context: dict = {
        "direct_request": True,
        "probe_request": True,
        "query_validation": query_report,
    }

    try:
        result_data: dict = await serialize_response(
            req,
            solr_params,
            WorkResults,
            extra_context,  # type: ignore
        )
    except SolrError:
        raise

    return result_data
