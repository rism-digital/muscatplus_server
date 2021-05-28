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
        cfg: Dict = req.app.ctx.config
        transl: Dict = req.app.ctx.translations

        facet_results: Optional[Dict] = obj.raw_response.get('facets')
        if not facet_results:
            return None

        mode_facet: Optional[Dict] = facet_results.get("mode")
        # if, for some reason, we don't have a mode facet we return gracefully.
        if not mode_facet:
            return None

        mode_buckets: List = mode_facet.get("buckets", [])
        mode_items: List = []
        mode_config: Dict = cfg['search']['modes']
        # Put the returned modes into a dictionary so we can look up the buckets by the key. The format is
        # {type: count}, where 'type' is the value from the Solr type field, and 'count' is the number of
        # records returned.
        mode_results: Dict = {f"{mode['val']}": mode['count'] for mode in mode_buckets}

        # This will ensure the modes are returned in the order they're listed in the configuration file. Otherwise
        #  they are returned by the order of results.
        for mode, config in mode_config.items():
            record_type = config['record_type']
            if record_type not in mode_results:
                continue

            translation_key: str = config['display_name']

            mode_items.append({
                "value": mode,
                "label": transl.get(translation_key),
                "count": mode_results[record_type]
            })

        return {
            "alias": "mode",
            "label": {"none": ["Result type"]},  # TODO: Translate!
            "type": "rism:Facet",
            "items": mode_items
        }

    @abstractmethod
    def get_items(self, obj: pysolr.Results) -> Optional[List]:
        pass
