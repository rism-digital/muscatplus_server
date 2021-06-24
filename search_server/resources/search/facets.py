import logging
import urllib.parse
from typing import Optional, List, Dict

from search_server.helpers.search_request import (
    filters_for_mode, filter_type_map, filter_label_map,
)

from small_asc.client import Results

log = logging.getLogger(__name__)


def get_facets(req, obj: Results) -> Optional[Dict]:
    facet_result: Optional[Dict] = obj.raw_response.get('facets')
    if not facet_result:
        return None

    cfg: Dict = req.app.ctx.config
    transl: Dict = req.app.ctx.translations

    current_mode: str = req.args.get("mode", cfg["search"]["default_mode"])
    filters = filters_for_mode(cfg, current_mode)
    facet_type_map: Dict = filter_type_map(filters)
    facet_label_map: Dict = filter_label_map(filters)

    facets: dict = {}

    for alias, res in facet_result.items():
        # Skip these sections of the facet results since
        # we handle them separately.
        if alias in ('count', 'mode'):
            continue

        facet_type = facet_type_map[alias]
        translation_key: str = facet_label_map[alias]

        cfg: Dict = {
            "alias": alias,
            "label": transl.get(translation_key),
            "type": _get_facet_type(facet_type)
        }

        if facet_type == "range":
            cfg.update(_create_range_facet(res))
        elif facet_type in ("selector", "filter", "toggle"):
            if 'buckets' not in res:
                continue

            cfg.update(_create_bucket_facet(res))

        facets[alias] = cfg

    return facets


def _get_facet_type(val) -> str:
    if val == "range":
        return "rism:RangeFacet"
    elif val == "toggle":
        return "rism:ToggleFacet"
    elif val == "selector":
        return "rism:SelectorFacet"
    elif val == "filter":
        return "rism:FilterFacet"
    else:
        return "rism:Facet"


def _create_range_facet(res) -> Dict:
    min_val = res["min"]
    max_val = res["max"]

    range_fields: dict = {
        "range": {
            "min": {
                "label": {"none": ["Minimum"]},
                "value": min_val
            },
            "max": {
                "label": {"none": ["Maximum"]},
                "value": max_val
            },
        }
    }
    return range_fields


def _create_bucket_facet(res) -> Dict:
    value_buckets = res["buckets"]

    items: List = []
    for bucket in value_buckets:
        value: str = urllib.parse.quote_plus(str(bucket['val']))

        items.append({
            "value": value,
            "label": {"none": [str(bucket["val"])]},
            "count": bucket['count']
        })

    selector_fields = {
        "items": items
    }

    return selector_fields


# def get_items(self, obj: Results) -> Optional[List]:
#     facet_result: Optional[Dict] = obj.raw_response.get('facets')
#     if not facet_result:
#         return None
#
#     req = self.context.get("request")
#     cfg: Dict = req.app.ctx.config
#     current_mode: str = req.args.get("mode", cfg["search"]["default_mode"])  # if no incoming mode, use the default
#     filters = filters_for_mode(cfg, current_mode)
#
#     # Get a lookup table for the alias / display so that we don't have to do this in the loop below.
#     facet_display_config: Dict = display_name_alias_map(filters)
#     facet_value_displayname_map: Dict = display_value_alias_map(filters)
#
#
#     facets: List[Dict] = []
#
#     for alias, res in facet_result.items():
#         # Ignore the 'count' field in the solr result. Also skip the 'mode' facet since we handle that
#         # in a separate block.
#         if alias in ("count", "mode"):
#             continue
#
#         items: List = []
#         for bucket in res["buckets"]:
#             displayName: str
#             if alias in facet_value_displayname_map and (d := facet_value_displayname_map[alias].get(str(bucket['val']))):
#                 display_name = d  # ignore warning
#             else:
#                 display_name = bucket['val']
#
#             items.append({
#                 "value": urllib.parse.quote_plus(str(bucket['val'])),
#                 "label": {"none": [display_name]},
#                 "count": bucket['count']
#             })
#
#         # If we don't have a list of values, don't show the facet.
#         if not items:
#             continue
#
#         f = {
#             "alias": alias,
#             "label": {"none": [facet_display_config[alias]]},
#             "items": items,
#             "type": "rism:Facet"
#         }
#         facets.append(f)
#
#     return facets
