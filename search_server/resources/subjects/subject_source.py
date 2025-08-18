import logging

from small_asc.client import JsonAPIRequest, Results

from search_server.helpers.search_request import SearchRequest
from search_server.helpers.solr_connection import SolrConnection
from search_server.resources.search.base_search import BaseSearchResults
from search_server.resources.sources.base_source import BaseSource

log = logging.getLogger("mp_server")


async def handle_subject_source_request(req, subject_id: str) -> dict:
    request_compiler = SearchRequest(req)
    request_compiler.filters += ["type:source", f"subject_ids:subject_{subject_id}"]

    solr_params: JsonAPIRequest = request_compiler.compile()
    solr_res: Results = await SolrConnection.search({**solr_params})

    return await SubjectResults(solr_res, context={"request": req}).serialized


class SubjectResults(BaseSearchResults):
    def get_modes(self, _) -> None:
        pass

    async def get_items(self, obj: Results) -> list | None:
        if obj.hits == 0:
            return None

        return await BaseSource(
            obj.docs, many=True, context={"request": self.context["request"]}
        ).serialized_many
