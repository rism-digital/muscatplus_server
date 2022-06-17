import logging
from typing import Optional

from small_asc.client import Results, SolrError

from search_server.exceptions import InvalidQueryException
from search_server.helpers.search_request import SearchRequest
from search_server.resources.search.base_search import serialize_response
from search_server.resources.search.search_results import BaseSearchResults, SourceSearchResult

log = logging.getLogger(__name__)


def _prepare_query(req, person_id: str, probe: bool = False) -> dict:
    try:
        request_compiler = SearchRequest(req, probe=probe)
        request_compiler.filters += ["type:source",
                                     f"creator_id:person_{person_id} OR related_people_ids:person_{person_id}"]
        solr_params = request_compiler.compile()
    except InvalidQueryException as e:
        log.exception("Invalid query: %s", e)
        raise

    return solr_params


async def handle_person_search_request(req, person_id: str) -> dict:
    try:
        solr_params: Optional[dict] = _prepare_query(req, person_id)
    except InvalidQueryException:
        raise

    try:
        result_data: dict = serialize_response(req, solr_params, PersonResults)
    except SolrError:
        raise

    return result_data


async def handle_person_probe_request(req, person_id: str) -> dict:
    try:
        solr_params: Optional[dict] = _prepare_query(req, person_id, probe=True)
    except InvalidQueryException:
        raise

    try:
        result_data:dict = serialize_response(req, solr_params, PersonResults)
    except SolrError:
        raise

    return result_data


class PersonResults(BaseSearchResults):
    def get_modes(self, obj: Results) -> Optional[dict]:
        return None

    def get_items(self, obj: Results) -> Optional[list]:
        if obj.hits == 0:
            return None

        return SourceSearchResult(obj.docs,
                                  many=True,
                                  context={"request": self.context.get("request")}).data
