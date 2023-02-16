import logging
import re
import urllib.parse
from re import Pattern
from typing import Optional

from small_asc.client import Results

from shared_helpers.identifiers import get_identifier
from search_server.helpers.search_request import (
    filters_for_mode,
    alias_config_map,
    FacetTypeValues,
    FacetBehaviourValues,
    FacetSortValues,
    types_alias_map,
    IncipitModeValues
)

log = logging.getLogger(__name__)
RANGE_PARSING_REGEX: Pattern = re.compile(r'\[(?P<start>-?\d{,4})\s?TO\s?(?P<end>-?\d{,4})\]')


def get_facets(req, obj: Results) -> Optional[dict]:
    facet_result: Optional[dict] = obj.raw_response.get('facets')

    if not facet_result:
        return None

    cfg: dict = req.app.ctx.config
    transl: dict = req.ctx.translations

    current_mode: str = req.args.get("mode", cfg["search"]["default_mode"])
    filters = filters_for_mode(cfg, current_mode)
    facet_config_map: dict = alias_config_map(filters)
    type_config_map: dict = types_alias_map(filters)

    facets: dict = {}

    # The notation and query search facets are treated slightly differently than the other facets
    # The purpose of the notation facet is to activate the keyboard interface in the search UI.
    notation_aliases: list = type_config_map.get(FacetTypeValues.NOTATION, [])
    for n_alias in notation_aliases:
        n_translation_key: str = facet_config_map[n_alias]['label']
        n_translation: Optional[dict] = transl.get(n_translation_key)

        n_label: dict
        if n_translation:
            n_label = n_translation
        else:
            n_label = {"none": [n_translation_key]}

        n_facet_cfg: dict = {
            "label": n_label,
            "alias": n_alias,
            "type": _get_facet_type(FacetTypeValues.NOTATION)

        }
        n_facet_cfg.update(_create_notation_facet(transl))
        facets[n_alias] = n_facet_cfg

    # the purpose of the query facet is to announce that there is a means of sending a full-text query
    # on a specific field to the server through a filter.
    query_aliases: list = type_config_map.get(FacetTypeValues.QUERY, [])
    for q_alias in query_aliases:
        q_translation_key: str = facet_config_map[q_alias]['label']
        q_translation: Optional[dict] = transl.get(q_translation_key)

        q_label: dict
        if q_translation:
            q_label = q_translation
        else:
            q_label = {"none": [q_translation_key]}

        q_facet_cfg: dict = {
            "label": q_label,
            "alias": q_alias,
            "type": _get_facet_type(FacetTypeValues.QUERY)
        }
        q_facet_cfg.update(_create_query_facet(q_alias, req, facet_config_map[q_alias]))
        facets[q_alias] = q_facet_cfg

    # Facets that contain values that are returned from a Solr search
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
            log.debug(f"Bailing with facet type of {facet_type}")
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

        cfg: dict = {
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
    elif val == FacetTypeValues.QUERY:
        return "rism:QueryFacet"
    else:
        return "rism:Facet"


def __get_key_signature(value: str) -> dict:
    if value == "n":
        return {
            "label": {"none": ["None"]},
            "value": value
        }

    symbol: str = ""
    if value.startswith("x"):
        symbol = "♯"
    elif value.startswith("b"):
        symbol = "♭"

    # The number of accidentals is the length of the string, subtract 1 for the initial character.
    num_accidentals: int = len(value) - 1
    return {
        "label": {"none": [f"{num_accidentals}{symbol}"]},
        "value": value
    }

KEY_SIGNATURES = [
    "n",
    "xF",
    "xFC",
    "xFCG",
    "xFCGD",
    "xFCGDA",
    "xFCGDAE",
    "xFCGDAEB",
    "bBEADGCF",
    "bBEADGC",
    "bBEADG",
    "bBEAD",
    "bBEA",
    "bBE",
    "bB",
]


def __get_key_signature_options() -> list[dict]:
    return [__get_key_signature(v) for v in KEY_SIGNATURES]


TIME_SIGNATURES = [
    "-",
    "4/4",
    "3/4",
    "6/8",
    "c",
    "c/",
    "o",
    "o."
]


def __get_time_signature(value: str) -> dict:
    if value == "-":
        label = "None"
    else:
        label = value

    return {
        "label": {"none": [f"{label}"]},
        "value": value
    }


def __get_time_signature_options() -> list[dict]:
    return [__get_time_signature(v) for v in TIME_SIGNATURES]


def _create_notation_facet(all_translations: dict) -> dict:
    return {
        "modes": {
            "label": {"none": ["Query mode"]},  # TODO: Translate
            "query": "im",
            "options": [{
                "label": {"none": ["Intervals"]},
                "value": IncipitModeValues.INTERVALS
            }, {
                "label": {"none": ["Exact pitches"]},
                "value": IncipitModeValues.EXACT_PITCHES
            }, {
                "label": {"none": ["Contour"]},
                "value": IncipitModeValues.CONTOUR
            }]
        },
        "options": {
            "clef": {
                "label": all_translations.get("records.clef"),
                "query": "ic",
                "options": [{
                    "label": all_translations.get("records.g_minus_2_treble"),
                    "value": "G-2"
                }, {
                    "label": all_translations.get("records.f_minus_4_bass"),
                    "value": "F-4"
                }, {
                    "label": all_translations.get("records.c_minus_3"),
                    "value": "C-3"
                }, {
                    "label": all_translations.get("records.c_minus_1"),
                    "value": "C-1"
                }, {
                    "label": all_translations.get("records.c_plus_1"),
                    "value": "C+1"
                }]
            },
            "keysig": {
                "label": all_translations.get("records.key_signature"),
                "query": "ik",
                "options": __get_key_signature_options()
            },
            "timesig": {
                "label": all_translations.get("records.time_signature"),
                "query": "it",
                "options": __get_time_signature_options()
            },
        }
    }


def _create_range_facet(alias: str, res, req) -> dict:
    min_val = res["min"]
    max_val = res["max"]
    incoming_args: list = req.args.getlist("fq", [])

    # present these values as the min/max values
    # unless there is a query argument that tells us otherwise.
    lower: int = min_val
    upper: int = max_val

    for arg in incoming_args:
        arg_name, arg_value = arg.split(":", 1)
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


def _create_toggle_facet(res) -> dict:
    toggle_fields: dict = {
        "value": "true"
    }
    return toggle_fields


def _create_select_facet(alias: str, res: dict, req, cfg: dict, all_translations: dict) -> dict:
    value_buckets = res["buckets"]
    translation_prefix: Optional[str] = cfg.get("translation_prefix")
    translation_values: Optional[dict] = cfg.get("translation_values")

    default_behaviour: str = cfg.get("default_behaviour", FacetBehaviourValues.INTERSECTION)
    current_behaviour: str = default_behaviour
    incoming_facet_behaviour: list = req.args.getlist("fb", [])
    for arg in incoming_facet_behaviour:
        arg_name, arg_value = arg.split(":")
        if arg_name == alias:
            current_behaviour = arg_value

    default_sort: str = cfg.get("default_sort", FacetSortValues.COUNT)

    items: list = []
    for bucket in value_buckets:
        solr_value = bucket['val']
        value: str

        if isinstance(solr_value, bool):
            value = str(solr_value).lower()
        else:
            value = urllib.parse.quote_plus(str(solr_value))

        label: dict
        default_label: dict = {"none": [str(solr_value)]}

        if translation_prefix:
            label = all_translations.get(f"{translation_prefix}.{solr_value}", default_label)
        elif translation_values:
            # look up the Solr value in the translation values in the configuration
            trans_key: Optional[str] = translation_values.get(solr_value)
            if not trans_key:
                label = default_label
            else:
                label = all_translations.get(f"{trans_key}", default_label)
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
        "defaultSort": default_sort,
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


def _create_query_facet(alias: str, req, cfg: dict) -> dict:
    default_behaviour: str = cfg.get("default_behaviour", FacetBehaviourValues.INTERSECTION)
    current_behaviour: str = default_behaviour
    incoming_facet_behaviour: list = req.args.getlist("fb", [])
    for arg in incoming_facet_behaviour:
        arg_name, arg_value = arg.split(":")
        if arg_name == alias:
            current_behaviour = arg_value

    suggestion_uri = get_identifier(req, "query.suggest")

    return {
        "suggestions": f"{suggestion_uri}?alias={alias}&q=",
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
