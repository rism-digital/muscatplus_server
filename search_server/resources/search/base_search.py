from abc import abstractmethod
from typing import Dict, Optional, List

import pysolr
import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.serializers import JSONLDContextSerializer
from search_server.resources.search.facets import FacetList
from search_server.resources.search.pagination import Pagination


class BaseSearchResults(JSONLDContextSerializer):
    """
    A Base Search Results serializer. Consumes a Solr response directly, and will manage the pagination
    data structures, but the actual serialization of the results is left to the classes derived from this
    base class. This allows it to be used to provide a standard paginated results interface, but it can serialize
    many different types of results from Solr.

    Implementing classes must implement the `get_items` method.
    """
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
    facets = serpy.MethodField()
    modes = serpy.MethodField()

    def get_sid(self, obj: pysolr.Results) -> str:
        """
        Simply reflects the incoming URL wholesale.
        """
        req = self.context.get('request')
        return req.url

    def get_total_items(self, obj: pysolr.Results) -> int:
        return obj.hits

    def get_view(self, obj: pysolr.Results) -> Dict:
        p = Pagination(obj, context={"request": self.context.get('request')})
        return p.data

    def get_facets(self, obj: pysolr.Results) -> Optional[Dict]:
        facets: Dict = FacetList(obj, context={"request": self.context.get("request")}).data
        if facets and facets.get("items"):
            return facets
        return None

    def get_modes(self, obj: pysolr.Results) -> Optional[Dict]:
        req = self.context.get("request")
        cfg: Dict = req.app.config

        modes = cfg["search"]["modes"]

        return {
            "alias": "mode",
            "label": {"none": ["Mode"]},  # TODO: Translate!
            "type": "rism:Facet",
            "items": [{"value": k, "label": {"none": [v['display_name']]}} for k, v in modes.items()]
        }

    @abstractmethod
    def get_items(self, obj: pysolr.Results) -> Optional[List]:
        pass
