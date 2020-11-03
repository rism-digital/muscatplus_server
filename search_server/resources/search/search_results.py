from typing import Dict, Optional, List

import pysolr
import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import get_identifier
from search_server.helpers.ld_context import RISM_JSONLD_CONTEXT
from search_server.helpers.serializers import ContextDictSerializer, ContextSerializer
from search_server.resources.search.pagination import Pagination


class SearchResults(ContextSerializer):
    ctx = serpy.MethodField(
        label="@context"
    )
    sid = serpy.MethodField(
        label="id"
    )
    stype = StaticField(
        label="type",
        value="Collection"
    )
    total_items = serpy.MethodField(
        label="totalItems"
    )
    view = serpy.MethodField()
    items = serpy.MethodField()

    def get_ctx(self, obj: pysolr.Results) -> Dict:
        return RISM_JSONLD_CONTEXT

    def get_sid(self, obj: pysolr.Results) -> str:
        req = self.context.get('request')

        return get_identifier(req, "search", **req.args)

    def get_total_items(self, obj: pysolr.Results) -> int:
        return obj.hits

    def get_view(self, obj: pysolr.Results) -> Dict:
        p = Pagination(obj, context={"request": self.context.get('request')})
        return p.data

    def get_items(self, obj: pysolr.Results) -> Optional[List]:
        if obj.hits == 0:
            return None

        return [r.get("title_s") for r in obj.docs]
