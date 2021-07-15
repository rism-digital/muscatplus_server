import logging
import re
import urllib.parse
from re import Pattern
from typing import Optional, List, Dict

from small_asc.client import Results

from search_server.helpers.search_request import (
    filters_for_mode, alias_config_map,
)

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
    facet_config_map: Dict = alias_config_map(filters)

    facets: dict = {}

    for alias, res in facet_result.items():
        # Skip these sections of the facet results since
        # we handle them separately.
        if alias in ('count', 'mode'):
            continue

        # Uses set logic to check whether the keys in the result
        # are equal to just the set of 'count'. This indicates that
        # there is not enough information coming from solr to construct
        # a facet response. This happens, for example, when Solr
        # does not respond with a value for the facet because all
        # values have been filtered out.
        if res.keys() == {"count"}:
            continue

        facet_type: str = facet_config_map[alias]['type']

        # Translate the label of the facet. If we don't find a translation
        # available, simply wrap the supplied label up in a language
        # map. This lets us supply a label for a facet (in english) that doesn't
        # yet have a translation available.
        translation_key: str = facet_config_map[alias]['label']
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

            value_translations: dict = facet_config_map[alias].get("values", {})
            cfg.update(_create_select_facet(res, value_translations, transl))

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


def _create_select_facet(res: dict, translations: dict, all_translations: dict) -> Dict:
    value_buckets = res["buckets"]

    items: List = []
    for bucket in value_buckets:
        solr_value = bucket['val']
        value: str

        if isinstance(solr_value, bool):
            value = str(solr_value).lower()
        else:
            value = urllib.parse.quote_plus(str(solr_value))

        label: dict
        default_label: dict = {"none": [str(solr_value)]}

        if solr_value in translations:
            # Get the entry for 'solr_value' from the translations
            # dictionary; if it doesn't exist, return the default label.
            label = all_translations.get(solr_value, default_label)
        else:
            label = default_label

        items.append({
            "value": value,
            "label": label,
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
