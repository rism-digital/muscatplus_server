import logging
from typing import Optional

from small_asc.client import Results

from search_server.helpers.search_request import SearchRequest
from search_server.helpers.solr_connection import SolrConnection
from search_server.resources.search.base_search import BaseSearchResults
from search_server.resources.search.search_results import SourceSearchResult

log = logging.getLogger(__name__)


async def handle_institution_search_request(req, institution_id: str) -> dict:
    request_compiler = SearchRequest(req)
    request_compiler.filters += ["type:source",
                                 f"holding_institutions_ids:institution_{institution_id} OR related_institutions_ids:institution_{institution_id}"]

    solr_params = request_compiler.compile()
    solr_res: Results = SolrConnection.search(solr_params)

    return InstitutionResults(solr_res, context={"request": req}).data


class InstitutionResults(BaseSearchResults):
    def get_modes(self, obj: Results) -> Optional[dict]:
        return None

    def get_items(self, obj: Results) -> Optional[list]:
        if obj.hits == 0:
            return None

        return SourceSearchResult(obj.docs,
                                  many=True,
                                  context={"request": self.context.get("request")}).data
