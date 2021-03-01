from typing import Dict, List, Optional, Callable, Tuple, Union
import logging

from search_server.helpers.solr_connection import SolrResult

LabelConfig = Dict[str, Tuple[str, Optional[Callable]]]

log = logging.getLogger(__name__)

_KEY_MODE_MAP: Dict = {
    "A": "records.a_major",
    "a": "records.a_minor",
    "A|b": "records.af_major",
    "a|b": "records.af_minor",
    "A|x": "records.as_major",
    "a|x": "records.as_minor",
    "B": "records.b_major",
    "b": "records.b_minor",
    "B|b": "records.bf_major",
    "b|b": "records.bf_minor",
    "C": "records.c_major",
    "c": "records.c_minor",
    "C|b": "records.cf_major",
    "c|b": "records.cf_minor",
    "C|x": "records.cs_major",
    "c|x": "records.cs_minor",
    "D": "records.d_major",
    "d": "records.d_minor",
    "D|b": "records.df_major",
    "d|b": "records.df_minor",
    "D|x": "records.ds_major",
    "d|x": "records.ds_minor",
    "E": "records.e_major",
    "e": "records.e_minor",
    "E|b": "records.ef_major",
    "e|b": "records.ef_minor",
    "F": "records.f_major",
    "f": "records.f_minor",
    "F|x": "records.fs_major",
    "f|x": "records.fs_minor",
    "G": "records.g_major",
    "g": "records.g_minor",
    "G|b": "records.gf_major",
    "g|b": "records.gf_minor",
    "G|x": "records.gs_major",
    "g|x": "records.gs_minor",
    "1t": "records.mode_1t",
    "1tt": "records.mode_1tt",
    "2t": "records.mode_2t",
    "2tt": "records.mode_2tt",
    "3t": "records.mode_3t",
    "3tt": "records.mode_3tt",
    "4t": "records.mode_4t",
    "4tt": "records.mode_4tt",
    "5t": "records.mode_5t",
    "5tt": "records.mode_5tt",
    "6t": "records.mode_6t",
    "6tt": "records.mode_6tt",
    "7t": "records.mode_7t",
    "7tt": "records.mode_7tt",
    "8t": "records.mode_8t",
    "8tt": "records.mode_8tt",
    "9t": "records.mode_9t",
    "9tt": "records.mode_9tt",
    "10t": "records.mode_10t",
    "10tt": "records.mode_10tt",
    "11t": "records.mode_11t",
    "11tt": "records.mode_11tt",
    "12t": "records.mode_12t",
    "12tt": "records.mode_12tt",
    "1byz": "records.octoechos1",
    "2byz": "records.octoechos2",
    "3byz": "records.octoechos3",
    "4byz": "records.octoechos4",
    "5byz": "records.octoechos5",
    "6byz": "records.octoechos6",
    "7byz": "records.octoechos7",
    "8byz": "records.octoechos8",
}

_CLEF_MAP: Dict = {
    "G-2": "records.g_minus_2_treble",
    "C-1": "records.c_minus_1"
}


def key_mode_value_translator(value: str, translations: Dict) -> Dict:
    """
    Returns a translated value from the Solr records. Keys and modes are stored as simple values,
    and the key/mode map provides a mapping between these values and the correct translation string.

    If for some reason the value is not found in the map, it is returned with a language code of "none".

    :param value: A key or mode value from the Solr index
    :param translations: A dictionary of available translations
    :return: A dictionary corresponding to a language map for that value.
    """
    trans_key: Optional[str] = _KEY_MODE_MAP.get(value)
    if not trans_key:
        return {"none": [value]}
    return translations.get(trans_key)


def clef_translator(value: str, translations: Dict) -> Dict:
    trans_key: Optional[str] = _CLEF_MAP.get(value)
    if not trans_key:
        return {"none": [value]}
    return translations.get(trans_key)


def _default_translator(value: Union[str, List], translations: Dict) -> Dict:
    """
    If the parameter given for a value translator in the field configuration is None,
    then use this function as the default translator. It will return the value wrapped
    as "none" in the language map, meaning that the string may have a language, but
    none is declared.

    See: https://github.com/w3c/json-ld-syntax/issues/102

    :param value: The field value
    :param translations: Not used, but provided so that this method has the same signature as the others.
    :return: A dictionary containing a default language map of the value.
    """
    return {"none": value if isinstance(value, list) else [value]}


# The field configuration should have a Solr field on one side, and a Tuple on the other. The tuple
# contains two values; the first is the key for the translations of the label, and the other is a translator function
# that will be able to convert the value of the keys to a language map. This can also be 'None', indicating that the
# value will use the default translator function, returning a language key of "none".
# The function for translating takes two arguments: The string to translate, and a dictionary of available translations.
# This field config will be the default used if one is not provided.
FIELD_CONFIG: LabelConfig = {
    "main_title_s": ("records.standardized_title", None),
    "source_title_s": ("records.title_on_source", None),
    "additional_title_s": ("records.additional_title", None),
}


def get_display_fields(record: SolrResult, translations: Dict, field_config: Optional[LabelConfig] = None) -> Optional[List]:
    """
    Returns a list of translated display fields for a given record. Uses the metadata fields to configure
    the label, based on the Solr field. Supports direct value output, or a function for translating the values.

    :param translations: A dictionary of the available application translations
    :param field_config: An optional configuration dictionary
    :param record: A record from a Solr instance
    :return: A formatted list of display fields
    """
    if not field_config:
        field_config = FIELD_CONFIG

    display: List = []

    for field, translation_map in field_config.items():
        if field not in record:
            continue

        label_translation, value_translator = translation_map

        # If the second key is None, set the translator function
        # to the default translator.
        if value_translator is None:
            value_translator = _default_translator

        record_value = record.get(field)

        label_value_map: Dict = {
            "label": translations.get(label_translation),
            "value": value_translator(record_value, translations)
        }

        display.append(label_value_map)

    return display or None
