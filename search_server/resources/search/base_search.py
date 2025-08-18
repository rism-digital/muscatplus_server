import logging
from abc import abstractmethod

import ypres
from small_asc.client import JsonAPIRequest, Results, SolrError

from search_server.helpers.solr_connection import execute_query
from search_server.resources.search.facets import get_facets
from search_server.resources.search.pagination import Pagination
from search_server.resources.search.sorting import get_sorting

log = logging.getLogger("mp_server")


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
    total_items = ypres.IntField(attr="hits", label="totalItems")
    view = ypres.MethodField()
    items = ypres.MethodField()
    facets = ypres.MethodField()
    modes = ypres.MethodField()
    sorts = ypres.MethodField()
    query_fields = ypres.MethodField(label="queryFields")
    page_sizes = ypres.MethodField(label="pageSizes")

    def get_sid(self, obj: Results) -> str:
        """
        Simply reflects the incoming URL wholesale.
        """
        req = self.context["request"]
        return req.url

    def get_view(self, obj: Results) -> dict | None:
        # is_probe: bool = self.context.get("probe_request", False)
        # if is_probe:
        #     return None

        return Pagination(obj, context={"request": self.context["request"]}).serialized

    def get_facets(self, obj: Results) -> dict | None:
        is_probe: bool = self.context.get("probe_request", False)
        if is_probe:
            return None

        return get_facets(self.context["request"], obj)

    def get_sorts(self, obj: Results) -> dict | None:
        is_probe: bool = self.context.get("probe_request", False)
        if is_probe:
            return None

        is_contents: bool = self.context.get("is_contents", False)
        return get_sorting(self.context["request"], is_contents)

    def get_page_sizes(self, obj: Results) -> list[str] | None:
        is_probe: bool = self.context.get("probe_request", False)
        if is_probe:
            return None

        req = self.context["request"]
        cfg: dict = req.app.ctx.config
        pgsizes: list[str] = [str(p) for p in cfg["search"]["page_sizes"]]

        return pgsizes

    def get_query_fields(self, obj: Results) -> list | None:
        req = self.context["request"]
        cfg: dict = req.app.ctx.config
        transl: dict = req.ctx.translations

        current_mode: str = req.args.get("mode", cfg["search"]["default_mode"])
        qfields: list = cfg["search"]["modes"][current_mode].get("q_fields", [])

        query_fields: list = []

        for qfield in qfields:
            q_translation_key: str = qfield["label"]
            q_translation: dict | None = transl.get(q_translation_key)
            q_label: dict = q_translation or {"none": [q_translation_key]}
            query_fields.append(
                {
                    "label": q_label,
                    "alias": qfield["alias"],
                }
            )

        return query_fields or None

    @abstractmethod
    def get_modes(self, obj: Results) -> dict | None:
        return None

    @abstractmethod
    async def get_items(self, obj: Results) -> list | None:
        return None


async def serialize_response(
    req,
    solr_params: JsonAPIRequest,
    serializer_cls: type[BaseSearchResults],
    extra_context: dict | None = None,
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

    # A dedicated solr handler is available, "/probe" for handling simple probe requests that
    # do not need fulltext searches. However, if a fulltext search is provided then the
    # probe request will be routed to the full search handler. This is toggled by the lack of a
    # "query" key in the solr request, or if the solr request is set to "*:*".
    is_probe = bool(extra_context and "probe_request" in extra_context)
    is_probe &= bool(
        solr_params and ("query" not in solr_params or solr_params["query"] == "*:*")
    )
    is_search = bool(extra_context and "search_request" in extra_context)

    handler = None
    if is_probe:
        handler = "/probe"
    elif is_search:
        log.debug("Using the search handler")
        handler = "/search"

    try:
        solr_res: Results | None = await execute_query(solr_params, handler=handler)
    except SolrError:
        raise

    ctx: dict = {"request": req}

    if extra_context:
        ctx.update(extra_context)

    return await serializer_cls(solr_res, context=ctx).serialized
