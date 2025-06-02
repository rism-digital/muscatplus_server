import logging

from small_asc.client import JsonAPIRequest, SolrError

from search_server.exceptions import InvalidQueryException
from search_server.helpers.search_request import SearchRequest
from search_server.resources.people.person import Person
from search_server.resources.people.person_search import PersonResults
from search_server.resources.search.base_search import serialize_response
from shared_helpers.solr_connection import SolrConnection

log = logging.getLogger("mp_server")

async def handle_person_request(req, person_id: str) -> dict | None:
    person_record = await SolrConnection.get(f"person_{person_id}")

    if not person_record:
        return None

    return await Person(
        person_record, context={"request": req, "direct_request": True}
    ).serialized



def _prepare_query(req, person_id: str, probe: bool = False) -> tuple[JsonAPIRequest, dict | None]:
    try:
        request_compiler = SearchRequest(req, probe=probe)
        request_compiler.filters += [
            "type:source",
            f"creator_id:person_{person_id} OR related_people_ids:person_{person_id}",
        ]
        solr_params: JsonAPIRequest = request_compiler.compile()
    except InvalidQueryException as e:
        log.exception("Invalid query: %s", e)
        raise

    return solr_params, request_compiler.query_report


async def handle_person_search_request(req, person_id: str) -> dict:
    try:
        solr_params, query_report = _prepare_query(req, person_id)
    except InvalidQueryException:
        raise

    extra_context: dict = {"direct_request": True,
                           "query_validation": query_report}

    try:
        result_data: dict = await serialize_response(
            req, solr_params, PersonResults, extra_context  # type: ignore
        )
    except SolrError:
        raise

    return result_data


async def handle_person_probe_request(req, person_id: str) -> dict:
    try:
        solr_params, query_report = _prepare_query(req, person_id, probe=True)
    except InvalidQueryException:
        raise

    extra_context: dict = {
        "direct_request": True,
        "probe_request": True,
        "query_validation": query_report,
    }

    try:
        result_data: dict = await serialize_response(
            req, solr_params, PersonResults, extra_context  # type: ignore
        )
    except SolrError:
        raise

    return result_data

