from abc import abstractmethod
from typing import Optional, Type

import ypres
from small_asc.client import Results, SolrError

from search_server.resources.search.facets import get_facets
from search_server.resources.search.pagination import Pagination
from search_server.resources.search.sorting import get_sorting
from shared_helpers.solr_connection import execute_query


class BaseSearchResults(ypres.AsyncSerializer):
    """
    A Base Search Results serializer. Consumes a Solr response directly, and will manage the pagination
    data structures, but the actual serialization of the results is left to the classes derived from this
    base class. This allows it to be used to provide a standard paginated results interface, but it can serialize
    many different types of results from Solr.

    Implementing classes must implement the `get_items` method.
    """

    sid = ypres.MethodField(label="id")
    stype = ypres.StaticField(label="type", value="Collection")
    total_items = ypres.MethodField(label="totalItems")
    view = ypres.MethodField()
    items = ypres.MethodField()
    facets = ypres.MethodField()
    modes = ypres.MethodField()
    sorts = ypres.MethodField()
    page_sizes = ypres.MethodField(label="pageSizes")

    def get_sid(self, obj: Results) -> str:
        """
        Simply reflects the incoming URL wholesale.
        """
        req = self.context.get("request")
        return req.url

    def get_total_items(self, obj: Results) -> int:
        return obj.hits

    def get_view(self, obj: Results) -> dict:
        return Pagination(obj, context={"request": self.context.get("request")}).data

    def get_facets(self, obj: Results) -> Optional[dict]:
        return get_facets(self.context.get("request"), obj)

    def get_sorts(self, obj: Results) -> Optional[list]:
        is_contents: bool = self.context.get("is_contents", False)
        return get_sorting(self.context.get("request"), is_contents)

    def get_page_sizes(self, obj: Results) -> list[str]:
        req = self.context.get("request")
        cfg: dict = req.app.ctx.config
        pgsizes: list[str] = [str(p) for p in cfg["search"]["page_sizes"]]

        return pgsizes

    @abstractmethod
    def get_modes(self, obj: Results) -> Optional[dict]:
        return None

    @abstractmethod
    async def get_items(self, obj: Results) -> Optional[list]:
        pass


async def serialize_response(
    req,
    solr_params: dict,
    serializer_cls: Type[BaseSearchResults],
    extra_context: Optional[dict] = None,
) -> dict:
    """
    Takes an incoming search request, performs a Solr query, and serializes
    the response to a dict object suitable for sending as JSON-LD.

    :param req: A sanic request object
    :param solr_params: A dictionary representing a Solr query. Should be created by the SearchRequest compiler.
    :param serializer_cls: The class to serialize the results with. Must be a subclass of BaseSearchResults
    :param extra_context: Any extra context to pass to the serializer. (The request object is automatically passed)
    :return: A dictionary of serialized content.
    """
    try:
        solr_res: Optional[Results] = await execute_query(solr_params)
    except SolrError:
        raise

    ctx: dict = {"request": req}

    if extra_context:
        ctx.update(extra_context)

    return await serializer_cls(solr_res, context=ctx).data
