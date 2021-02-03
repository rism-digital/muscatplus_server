import logging
from typing import Optional, List, Dict

import pysolr

from search_server.helpers.search_request import SearchRequest
from search_server.helpers.solr_connection import SolrConnection
from search_server.resources.people.person_source_relationship import PersonSourceRelationship
from search_server.resources.search.search_results import BaseSearchResults

log = logging.getLogger(__name__)


def handle_person_source_request(req, person_id: str) -> Dict:
    request_compiler = SearchRequest(req)
    request_compiler.filters += ["type:source_person_relationship",
                                 f"person_id:person_{person_id}"]

    solr_params = request_compiler.compile()
    solr_res: pysolr.Results = SolrConnection.search(**solr_params)

    person_source_results = PersonResults(solr_res, context={"request": req})

    return person_source_results.data


class PersonResults(BaseSearchResults):
    def get_items(self, obj: pysolr.Results) -> Optional[List]:
        if obj.hits == 0:
            return None

        return PersonSourceRelationship(obj.docs, many=True, context={"request": self.context.get("request")}).data
