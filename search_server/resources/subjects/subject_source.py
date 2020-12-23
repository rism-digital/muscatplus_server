import logging
from typing import Optional, List, Dict

import pysolr

from search_server.helpers.search_request import SearchRequest
from search_server.helpers.solr_connection import SolrConnection
from search_server.resources.search.base_search import BaseSearchResults
from search_server.resources.sources.base_source import BaseSource

log = logging.getLogger(__name__)


def handle_subject_source_request(req, subject_id: str) -> Dict:
    request_compiler = SearchRequest(req)
    request_compiler.filters += ["type:source", f"subject_ids:subject_{subject_id}"]

    solr_params: Dict = request_compiler.compile()
    solr_res: pysolr.Results = SolrConnection.search(**solr_params)

    subject_source_results = SubjectResults(solr_res, context={"request": req})

    return subject_source_results.data


class SubjectResults(BaseSearchResults):
    def get_items(self, obj: pysolr.Results) -> Optional[List]:
        if obj.hits == 0:
            return None

        return BaseSource(obj.docs, many=True, context={"request": self.context.get("request")}).data
