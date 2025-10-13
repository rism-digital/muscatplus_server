import logging

from small_asc.client import JsonAPIRequest, SolrError

from search_server.exceptions import InvalidQueryException
from search_server.helpers.search_request import SearchRequest
from search_server.helpers.solr_connection import SolrConnection
from search_server.resources.institutions.institution import Institution
from search_server.resources.institutions.institution_search import InstitutionResults
from search_server.resources.search.base_search import (
    serialize_response,
)

log = logging.getLogger("mp_server")


async def handle_institution_request(req, institution_id: str) -> dict | None:
    solr_id: str = f"institution_{institution_id}"
    institution_record: dict | None = await SolrConnection.get(solr_id)

    if not institution_record:
        return None

    return await Institution(
        institution_record, context={"request": req, "direct_request": True}
    ).serialized


def _prepare_query(
    req, institution_id: str, probe: bool = False
) -> tuple[JsonAPIRequest, dict | None]:
    try:
        request_compiler = SearchRequest(req, probe=probe)
        request_compiler.filters += [
            "type:source",
            f"holding_institutions_ids:institution_{institution_id} OR related_institutions_ids:institution_{institution_id}",
        ]

        solr_params = request_compiler.compile()
    except InvalidQueryException as e:
        log.exception("Invalid query: %s", e)
        raise

    return solr_params, request_compiler.query_report


async def handle_institution_search_request(req, institution_id: str) -> dict:
    try:
        solr_params, query_report = _prepare_query(req, institution_id)
    except InvalidQueryException:
        raise

    extra_context = {"direct_request": True, "query_validation": query_report}

    try:
        result_data: dict = await serialize_response(
            req,
            solr_params,
            InstitutionResults,
            extra_context,  # type: ignore
        )
    except SolrError:
        raise

    return result_data


async def handle_institution_probe_request(req, institution_id: str) -> dict:
    try:
        solr_params, query_report = _prepare_query(req, institution_id, probe=True)
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
            InstitutionResults,
            extra_context,  # type: ignore
        )
    except SolrError:
        raise

    return result_data
