import logging
import re
import urllib.parse
from re import Pattern
from typing import Optional, List, Dict

from search_server.helpers.search_request import (
    filters_for_mode, filter_type_map, filter_label_map,
)

from small_asc.client import Results

log = logging.getLogger(__name__)
RANGE_PARSING_REGEX: Pattern = re.compile(r'\[(?P<start>-?\d{,4})\s?TO\s?(?P<end>-?\d{,4})\]')


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

        # Uses set logic to check whether the keys in the result
        # are equal to just the set of 'count'. This indicates that
        # there is not enough information coming from solr to construct
        # a facet response.
        if res.keys() == {"count"}:
            continue

        facet_type = facet_type_map[alias]
        translation_key: str = facet_label_map[alias]
        translation: Optional[dict] = transl.get(translation_key)
        label: dict
        if translation:
            label = translation
        else:
            label = {"none": [translation_key]}

        cfg: Dict = {
            "alias": alias,
            "label": label,
            "type": _get_facet_type(facet_type)
        }

        if facet_type == "range":
            cfg.update(_create_range_facet(alias, res, req))
        elif facet_type == "toggle":
            cfg.update(_create_toggle_facet(res))
        elif facet_type == "select":
            if 'buckets' not in res:
                continue

            cfg.update(_create_select_facet(res))

        facets[alias] = cfg

    return facets


def _get_facet_type(val) -> str:
    if val == "range":
        return "rism:RangeFacet"
    elif val == "toggle":
        return "rism:ToggleFacet"
    elif val == "select":
        return "rism:SelectFacet"
    else:
        return "rism:Facet"


def _create_range_facet(alias, res, req) -> Dict:
    min_val = res["min"]
    max_val = res["max"]
    incoming_args: list = req.args.getlist("fq", [])

    # present these values as the min/max values
    # unless there is a query argument that tells us otherwise.
    lower: int = min_val
    upper: int = max_val

    for arg in incoming_args:
        arg_name, arg_value = arg.split(":")
        if arg_name != alias:
            continue

        if match := RANGE_PARSING_REGEX.search(arg_value):
            lower = int(match.group("start"))
            upper = int(match.group("end"))

    range_fields: dict = {
        "range": {
            "lower": {
                "label": {"none": ["Lower"]},
                "value": lower
            },
            "upper": {
                "label": {"none": ["Upper"]},
                "value": upper
            },
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


def _create_toggle_facet(res) -> Dict:
    toggle_fields: dict = {
        "value": "true"
    }
    return toggle_fields


def _create_select_facet(res) -> Dict:
    value_buckets = res["buckets"]

    items: List = []
    for bucket in value_buckets:
        value: str
        if isinstance(bucket['val'], bool):
            value = str(bucket['val']).lower()
        else:
            value = urllib.parse.quote_plus(str(bucket['val']))

        items.append({
            "value": value,
            "label": {"none": [str(bucket["val"])]},
            "count": bucket['count']
        })

    selector_fields = {
        "items": items,
        "behaviours": {
            "label": {"none": ["Behaviour"]},  # TODO: Translate these fields!
            "items": [{
                    "label": {"none": ["Intersection"]},
                    "value": "intersection"
                }, {
                    "label": {"none": ["Union"]},
                    "value": "union"
            }]
        }
    }

    return selector_fields
