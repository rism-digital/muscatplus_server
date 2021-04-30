from typing import Dict, Optional, List

import pysolr

from search_server.helpers.search_request import SearchRequest
from search_server.helpers.solr_connection import SolrConnection
from search_server.resources.search.base_search import BaseSearchResults
from search_server.resources.sources.base_source import BaseSource


def handle_source_list_request(req) -> Optional[Dict]:
    request_compiler = SearchRequest(req)
    request_compiler.filters += ["type:source"]
    request_compiler.sorts += ["main_title_ans asc"]

    solr_params: Dict = request_compiler.compile()
    solr_res: pysolr.Results = SolrConnection.search(**solr_params)

    source_results = SourceResults(solr_res, context={"request": req})

    return source_results.data


class SourceResults(BaseSearchResults):
    def get_items(self, obj: pysolr.Results) -> Optional[List]:
        if obj.hits == 0:
            return None

        return BaseSource(obj.docs, many=True, context={"request": self.context.get("request")}).data
