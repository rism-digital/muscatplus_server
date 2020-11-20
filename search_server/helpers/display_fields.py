from typing import Dict, List, Optional

from search_server.helpers.solr_connection import SolrResult

FIELD_CONFIG: Dict[str, str] = {
    "source_title_s": "records.title_on_source"
}


def get_display_fields(record: SolrResult, translations: Dict, field_config: Optional[Dict[str, str]] = None) -> Optional[List]:
    """
    Returns a list of translated display fields for a given record. Uses the metadata fields to configure
    the label, based on the Solr field.

    :param translations: A dictionary of the available application translations
    :param field_config: An optional configuration dictionary
    :param record: A record from a Solr instance
    :return: A formatted list of display fields
    """
    if not field_config:
        field_config = FIELD_CONFIG

    display: List = []

    for field, label in field_config.items():
        val = record.get(field)
        if not val:
            continue

        if isinstance(val, list):
            fval = [{
                "label": translations.get(label),
                "value": {"none": val}
            }]
        else:
            fval = [{
                "label": translations.get(label),
                "value": {"none": [val]}
            }]

        display += fval

    return display or None
