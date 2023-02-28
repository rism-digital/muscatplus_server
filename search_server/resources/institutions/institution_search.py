import logging
from typing import Optional

from small_asc.client import Results, SolrError

from search_server.exceptions import InvalidQueryException
from search_server.helpers.search_request import SearchRequest
from search_server.resources.search.base_search import BaseSearchResults, serialize_response
from search_server.resources.search.search_results import SourceSearchResult


log = logging.getLogger("mp_server")


def _prepare_query(req, institution_id: str, probe: bool = False) -> Optional[dict]:
    try:
        request_compiler = SearchRequest(req, probe=probe)
        request_compiler.filters += ["type:source",
                                     f"holding_institutions_ids:institution_{institution_id} OR related_institutions_ids:institution_{institution_id}"]

        solr_params = request_compiler.compile()
    except InvalidQueryException as e:
        log.exception("Invalid query: %s", e)
        return None

    return solr_params


async def handle_institution_search_request(req, institution_id: str) -> dict:
    try:
        solr_params: Optional[dict] = _prepare_query(req, institution_id)
    except InvalidQueryException:
        raise

    try:
        result_data: dict = await serialize_response(req, solr_params, InstitutionResults)
    except SolrError:
        raise

    return result_data


async def handle_institution_probe_request(req, institution_id: str) -> dict:
    try:
        solr_params: Optional[dict] = _prepare_query(req, institution_id, probe=True)
    except InvalidQueryException:
        raise

    try:
        result_data: dict = await serialize_response(req, solr_params, InstitutionResults)
    except SolrError:
        raise

    return result_data


class InstitutionResults(BaseSearchResults):
    def get_modes(self, obj: Results) -> Optional[dict]:
        return None

    async def get_items(self, obj: Results) -> Optional[list]:
        if obj.hits == 0:
            return None

        return SourceSearchResult(obj.docs,
                                  many=True,
                                  context={"request": self.context.get("request")}).data


