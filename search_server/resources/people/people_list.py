from typing import Dict, List, Optional

import pysolr

from search_server.helpers.search_request import SearchRequest
from search_server.helpers.solr_connection import SolrConnection
from search_server.resources.people.base_person import BasePerson
from search_server.resources.search.base_search import BaseSearchResults


def handle_people_list_request(req) -> Dict:
    request_compiler = SearchRequest(req)
    request_compiler.filters += ["type:person"]
    request_compiler.sorts += ["name_ans asc"]

    solr_params: Dict = request_compiler.compile()
    solr_res: pysolr.Results = SolrConnection.search(**solr_params)

    people_results = PeopleResults(solr_res, context={"request": req})

    return people_results.data


class PeopleResults(BaseSearchResults):
    def get_items(self, obj: pysolr.Results) -> Optional[List]:
        if obj.hits == 0:
            return None

        return BasePerson(obj.docs, many=True, context={"request": self.context.get("request")}).data
