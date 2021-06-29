import logging
from typing import Optional, List, Dict

from small_asc.client import Results
from search_server.helpers.search_request import SearchRequest
from search_server.helpers.solr_connection import SolrConnection
from search_server.resources.search.search_results import BaseSearchResults, SourceSearchResult

log = logging.getLogger(__name__)


async def handle_person_search_request(req, person_id: str) -> Dict:
    request_compiler = SearchRequest(req)
    request_compiler.filters += ["type:source",
                                 f"creator_id:person_{person_id} OR related_people_ids:person_{person_id}"]

    solr_params = request_compiler.compile()
    solr_res: Results = SolrConnection.search(solr_params)

    person_source_results = PersonResults(solr_res, context={"request": req})

    return person_source_results.data


class PersonResults(BaseSearchResults):
    def get_modes(self, obj: Results) -> Optional[Dict]:
        return None

    def get_items(self, obj: Results) -> Optional[List]:
        if obj.hits == 0:
            return None

        return SourceSearchResult(obj.docs,
                                  many=True,
                                  context={"request": self.context.get("request")}).data
