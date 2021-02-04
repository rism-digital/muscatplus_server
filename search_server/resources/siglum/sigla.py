from typing import Dict, Optional, List

import pysolr

from search_server.helpers.search_request import SearchRequest
from search_server.helpers.solr_connection import SolrConnection
from search_server.resources.institutions.institution import Institution
from search_server.resources.search.base_search import BaseSearchResults


def handle_sigla_request(req) -> Dict:
    request_compiler = SearchRequest(req)
    request_compiler.filters += ["type:institution",
                                 "siglum_s:[* TO *]"]

    solr_params = request_compiler.compile()
    solr_res: pysolr.Results = SolrConnection.search(**solr_params)

    sigla_results = SiglaResults(solr_res, context={"request": req})
    return sigla_results.data


class SiglaResults(BaseSearchResults):
    def get_items(self, obj: pysolr.Results) -> Optional[List]:
        if obj.hits == 0:
            return None

        return Institution(obj.docs,
                           many=True,
                           context={"request": self.context.get("request")}).data
