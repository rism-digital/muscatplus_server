from sanic import request
from sanic.log import logger
from small_asc.client import JsonAPIRequest, SolrError

from search_server.exceptions import InvalidQueryException
from search_server.helpers.search_request import SearchRequest
from search_server.helpers.solr_connection import SolrConnection
from search_server.resources.search.base_search import serialize_response
from search_server.resources.works.full_work import FullWork
from search_server.resources.works.works_search import (
    WorkSourceResults,
)


async def handle_work_request(req, work_id: str) -> dict | None:
    work_record: dict | None = await SolrConnection.get(f"work_{work_id}")  # type: ignore

    if not work_record:
        return None

    return await FullWork(
        work_record, context={"request": req, "direct_request": True}
    ).serialized


def _prepare_query(
    req, work_id: str, probe: bool = False
) -> tuple[JsonAPIRequest, dict | None]:
    try:
        request_compiler = SearchRequest(req, probe=probe)
        request_compiler.filters += [
            "type:source",
            f"work_ids:work_{work_id}",
        ]
        solr_params: JsonAPIRequest = request_compiler.compile()
    except InvalidQueryException as e:
        logger.exception("Invalid query: %s", e)
        raise

    return solr_params, request_compiler.query_report


async def handle_work_search_request(req: request.Request, work_id: str) -> dict | None:
    try:
        solr_params, query_report = _prepare_query(req, work_id)
    except InvalidQueryException:
        raise

    extra_context: dict = {"direct_request": True, "query_validation": query_report}

    try:
        result_data: dict = await serialize_response(
            req, solr_params, WorkSourceResults, extra_context
        )
    except SolrError:
        raise

    return result_data


async def handle_work_probe_request(req: request.Request, work_id: str) -> dict:
    try:
        solr_params, query_report = _prepare_query(req, work_id, probe=True)
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
            WorkSourceResults,
            extra_context,  # type: ignore
        )
    except SolrError:
        raise

    return result_data
