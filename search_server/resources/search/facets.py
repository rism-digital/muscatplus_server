from typing import Optional, List, Dict, Tuple
import logging
import urllib.parse

import pysolr
import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.serializers import ContextDictSerializer

log = logging.getLogger(__name__)


class FacetList(ContextDictSerializer):
    ftype = StaticField(
        label="type",
        value="rism:FacetList"
    )
    items = serpy.MethodField()

    def get_items(self, obj: pysolr.Results) -> Optional[List]:
        facet_result: Optional[Dict] = obj.raw_response.get('facets')
        if not facet_result:
            return None

        req = self.context.get("request")
        cfg: Dict = req.app.config
        facet_config = cfg['search']["facet_fields"]
        # Generate a lookup table for the alias / display so that we don't have to do this in the loop below.
        facet_display_config: Dict = {f"{cfg['alias']}": f"{cfg['display_name']}" for cfg in facet_config.values()}
        facet_value_displayname_map: Dict = {f"{cfg['alias']}": cfg['display_value_map'] for cfg in facet_config.values() if cfg.get('display_value_map')}

        facets: List[Dict] = []

        for alias, res in facet_result.items():
            # Ignore the 'count' field in the solr result
            if alias == "count":
                continue

            items: List = []
            for bucket in res["buckets"]:
                displayName: str
                if alias in facet_value_displayname_map and (d := facet_value_displayname_map[alias].get(str(bucket['val']))):
                    display_name = d  # ignore warning
                else:
                    display_name = bucket['val']

                items.append({
                    "value": urllib.parse.quote_plus(str(bucket['val'])),
                    "label": {"none": [display_name]},
                    "count": bucket['count']
                })

            # If we don't have a list of values, don't show the facet.
            if not items:
                continue

            f = {
                "alias": alias,
                "label": {"none": [facet_display_config[alias]]},
                "items": items
            }
            facets.append(f)

        return facets
