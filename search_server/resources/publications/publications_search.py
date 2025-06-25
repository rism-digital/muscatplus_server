import ypres
from small_asc.client import Results

from search_server.resources.search.base_search import BaseSearchResults
from search_server.resources.search.search_results import WorkSearchResult


class WorkResults(BaseSearchResults):
    query_validation = ypres.MethodField(label="queryValidation")  # noqa: F821

    def get_query_validation(self, obj: Results) -> dict | None:
        if "query_validation" not in self.context:
            return None

        return self.context["query_validation"]

    def get_modes(self, obj: Results) -> dict | None:
        return None

    def get_facets(self, obj: Results) -> dict | None:
        return {}

    def get_sorts(self, obj: Results) -> dict | None:
        return {"options": [], "default": ""}

    def get_query_fields(self, obj: Results) -> list | None:
        return None

    async def get_items(self, obj: Results) -> list | None:
        if obj.hits == 0:
            return None

        return WorkSearchResult(
            obj.docs, many=True, context={"request": self.context["request"]}
        ).serialized_many
