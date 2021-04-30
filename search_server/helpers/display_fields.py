from typing import Dict, List, Optional, Callable, Tuple, Union
import logging

from search_server.helpers.solr_connection import SolrResult

LabelConfig = Dict[str, Tuple[str, Optional[Union[Callable, Dict]]]]

log = logging.getLogger(__name__)

FIELD_CONFIG: LabelConfig = {
    "main_title_s": ("records.standardized_title", None),
    "scoring_summary_sm": ("records.scoring_summary", None),
    "source_title_s": ("records.title_on_source", None),
    "additional_title_s": ("records.additional_title", None)
}


def _default_translator(value: Union[str, List], translations: Dict) -> Dict:
    """
    If the parameter given for a value translator in the field configuration is None,
    then use this function as the default translator. It will return the value wrapped
    as "none" in the language map, meaning that the string may have a language, but
    none is declared.

    See: https://github.com/w3c/json-ld-syntax/issues/102

    Additional specialized translators are defined in the display_translators module.

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


def get_display_fields(record: Union[SolrResult, Dict], translations: Dict, field_config: Optional[LabelConfig] = None) -> Optional[List]:
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

        # deconstruct the translation map tuple into the translation
        # key and the translator function
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
