from typing import Dict, List, Optional

import pysolr

from search_server.helpers.search_request import SearchRequest
from search_server.helpers.solr_connection import SolrConnection
from search_server.resources.search.base_search import BaseSearchResults
from search_server.resources.sources.base_source import BaseSource


def handle_institution_source_request(req, institution_id: str) -> Dict:
    request_compiler = SearchRequest(req)
    request_compiler.filters += ["type:source",
                                 f"holding_institution_ids:institution_{institution_id}"]

    solr_params = request_compiler.compile()
    solr_res: pysolr.Results = SolrConnection.search(**solr_params)

    institution_source_results = InstitutionResults(solr_res, context={"request": req})

    return institution_source_results.data


class InstitutionResults(BaseSearchResults):
    def get_items(self, obj: pysolr.Results) -> Optional[List]:
        if obj.hits == 0:
            return None

        return BaseSource(obj.docs,
                          many=True,
                          context={"request": self.context.get("request")}).data
