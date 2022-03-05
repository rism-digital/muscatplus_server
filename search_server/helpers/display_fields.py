from typing import Optional, Callable, Union
import logging

from search_server.helpers.solr_connection import SolrResult


# LabelConfig takes a Solr field, and maps it to a tuple containing the translation value for the label, and an
# optional Callable that can be used to provide the value translations. For example, if we have:
#
#  {"foo_s": ("records.foo", foo_value_translator)}
#
#  This means that:
#   - The value comes from the `foo_s` Solr field
#   - The label for this field is the value in the `records.foo` translation
#   - Whatever is in this field will be passed through the `foo_value_translator` function before being sent to the
#     client.
#
#  A value of `None` for the value translator means to simply take the value verbatim. (Technically, a value of None
#  passes it through the _default_translator function, but this is largely transparent to the user).
#
LabelConfig = dict[str, tuple[str, Optional[Union[Callable, dict]]]]

log = logging.getLogger(__name__)

FIELD_CONFIG: LabelConfig = {
    "main_title_s": ("records.standardized_title", None),
    "scoring_summary_sm": ("records.scoring_summary", None),
    "source_title_s": ("records.title_on_source", None),
    "additional_title_s": ("records.additional_title", None)
}


def _default_translator(value: Union[str, list], translations: dict) -> dict:
    """
    If the parameter given for a value translator in the field configuration is None,
    then use this function as the default translator. It will return the value wrapped
    as "none" in the language map, meaning that the string may have a language, but
    none is declared.

    See: https://github.com/w3c/json-ld-syntax/issues/102

    Additional specialized translators are defined in the display_translators module.

    Ensures the values sent back are always strings!

    :param value: The field value
    :param translations: Not used, but provided so that this method has the same signature as the others.
    :return: A dictionary containing a default language map of the value.
    """
    return {"none": [str(v) for v in value] if isinstance(value, list) else [str(value)]}


# The field configuration should have a Solr field on one side, and a Tuple on the other. The tuple
# contains two values; the first is the key for the translations of the label, and the other is a translator function
# that will be able to convert the value of the keys to a language map. This can also be 'None', indicating that the
# value will use the default translator function, returning a language key of "none".
# The function for translating takes two arguments: The string to translate, and a dictionary of available translations.
# This field config will be the default used if one is not provided.
def _assemble_label_value(record: Union[SolrResult, dict], field_name: str, translation_map: tuple[str, Optional[Callable]], translations: dict) -> dict:
    # deconstruct the translation map tuple into the translation
    # key and the translator function
    label_translation, value_translator = translation_map

    # If the second key is None, set the translator function
    # to the default translator.
    if value_translator is None:
        value_translator = _default_translator

    record_value = record.get(field_name)

    label_value_map: dict = {
        "label": translations.get(label_translation),
        "value": value_translator(record_value, translations)
    }

    return label_value_map


def get_display_fields(record: Union[SolrResult, dict], translations: dict, field_config: Optional[LabelConfig] = None) -> Optional[list]:
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

    display: list = []

    for field, translation_map in field_config.items():
        if field not in record:
            continue

        label_value: dict = _assemble_label_value(record, field, translation_map, translations)

        display.append(label_value)

    return display or None


def get_search_result_summary(field_config: dict, translations: dict, result: dict) -> Optional[dict]:
    summary: dict = {}

    for solr_fieldname, cfg in field_config.items():
        if solr_fieldname not in result:
            continue

        output_fieldname: str = cfg[0]
        translation_key: str = cfg[1]
        translation_value_translator_fn: Optional[Callable] = cfg[2]
        field_res: dict = _assemble_label_value(result, solr_fieldname, (translation_key, translation_value_translator_fn), translations)
        summary.update({output_fieldname: field_res})

    return summary or None
