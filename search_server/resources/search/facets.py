import logging
import re
import urllib.parse
from re import Pattern
from typing import Optional, List, Dict

from small_asc.client import Results

from search_server.helpers.search_request import (
    filters_for_mode, alias_config_map, FacetTypeValues, FacetBehaviourValues, FacetSortValues, FacetModeValues
)

log = logging.getLogger("mp_server")
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

    # The notation search is treated slightly differently than the other facets
    # The purpose of the facet is to activate the keyboard interface in the search UI.
    if current_mode == "incipits" and facet_config_map.get("notation"):
        facet_cfg: dict = {
            "label": {"none": ["Notation"]},
            "alias": "notation",
            "type": _get_facet_type("notation")

        }
        facet_cfg.update(_create_notation_facet())
        facets["notation"] = facet_cfg

    # Facets contain values that are returned from a Solr search
    for alias, res in facet_result.items():
        # Skip these sections of the facet results since
        # we handle them separately.
        if alias in ('count', 'mode'):
            continue

        facet_type: str = facet_config_map[alias]['type']

        # Uses set logic to check whether the keys in the result
        # are equal to just the set of 'count'. This indicates that
        # there is not enough information coming from solr to construct
        # a facet response. This happens, for example, when Solr
        # does not respond with a value for the facet because all
        # values have been filtered out.
        if res.keys() == {"count"}:
            continue

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

            fcfg: dict = facet_config_map[alias]
            cfg.update(_create_select_facet(alias, res, req, fcfg, transl))

        facets[alias] = cfg

    return facets


def _get_facet_type(val) -> str:
    if val == FacetTypeValues.RANGE:
        return "rism:RangeFacet"
    elif val == FacetTypeValues.TOGGLE:
        return "rism:ToggleFacet"
    elif val == FacetTypeValues.SELECT:
        return "rism:SelectFacet"
    elif val == FacetTypeValues.NOTATION:
        return "rism:NotationFacet"
    else:
        return "rism:Facet"


def _create_notation_facet() -> Dict:
    return {
        "clef": "ic",
        "keysig": "ik",
        "timesig": "it"
    }


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


def _create_select_facet(alias, res: dict, req, cfg: dict, all_translations: dict) -> Dict:
    value_buckets = res["buckets"]
    translations: dict = cfg.get("values", {})

    default_behaviour: str = cfg.get("default_behaviour", FacetBehaviourValues.INTERSECTION)
    current_behaviour: str = default_behaviour
    incoming_facet_behaviour: list = req.args.getlist("fb", [])
    for arg in incoming_facet_behaviour:
        arg_name, arg_value = arg.split(":")
        if arg_name == alias:
            current_behaviour = arg_value

    default_sort: str = cfg.get("default_sort", FacetSortValues.COUNT)
    current_sort: str = default_sort
    incoming_facet_sort: list = req.args.getlist("fs", [])
    for arg in incoming_facet_sort:
        arg_name, arg_value = arg.split(":")
        if arg_name == alias:
            current_sort = arg_value

    default_mode: str = cfg.get("default_mode", FacetModeValues.CHECK)
    current_mode: str = default_mode
    incoming_facet_mode: list = req.args.getlist("fm", [])
    for arg in incoming_facet_mode:
        arg_name, arg_value = arg.split(":")
        if arg_name == alias:
            current_mode = arg_value

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

    # TODO: Translate these fields!
    selector_fields = {
        "items": items,
        "sorts": {
            "label": {"none": ["Facet Sort"]},
            "items": [{
                "label": {"none": ["Count"]},
                "value": FacetSortValues.COUNT
            }, {
                "label": {"none": ["Alphabetical"]},
                "value": FacetSortValues.ALPHA
            }],
            "default": default_sort,
            "current": current_sort
        },
        "behaviours": {
            "label": {"none": ["Behaviour"]},
            "items": [{
                    "label": {"none": ["And"]},
                    "value": FacetBehaviourValues.INTERSECTION
                }, {
                    "label": {"none": ["Or"]},
                    "value": FacetBehaviourValues.UNION
            }],
            "default": default_behaviour,
            "current": current_behaviour
        }
    }

    return selector_fields
