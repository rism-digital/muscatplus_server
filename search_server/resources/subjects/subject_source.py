import logging
from typing import Optional

from small_asc.client import Results

from search_server.helpers.search_request import SearchRequest
from search_server.resources.search.base_search import BaseSearchResults
from search_server.resources.sources.base_source import BaseSource
from shared_helpers.solr_connection import SolrConnection

log = logging.getLogger("mp_server")


async def handle_subject_source_request(req, subject_id: str) -> dict:
    request_compiler = SearchRequest(req)
    request_compiler.filters += ["type:source", f"subject_ids:subject_{subject_id}"]

    solr_params: dict = request_compiler.compile()
    solr_res: Results = await SolrConnection.search({**solr_params})

    return await SubjectResults(solr_res, context={"request": req}).data


class SubjectResults(BaseSearchResults):
    async def get_items(self, obj: Results) -> Optional[list]:
        if obj.hits == 0:
            return None

        return await BaseSource(
            obj.docs, many=True, context={"request": self.context.get("request")}
        ).data
