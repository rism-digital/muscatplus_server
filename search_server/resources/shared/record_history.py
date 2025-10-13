def get_record_history(obj: dict, transl: dict) -> dict | None:
    """
    Formats a record history object with the appropriate translation labels.

    The `obj` must have the 'created' and 'updated' fields in it. This will
    return None in the case that they don't to prevent runtime crashes, but
    other components (e.g., a user interface) may expect this as a required
    field.

    :param obj: A dictionary, most likely a Solr result
    :param transl: A dictionary of translatable fields
    :return: A dictionary corresponding to a record history block.
    """
    if "created" not in obj or "updated" not in obj:
        return None

    return {
        "type": "rism:RecordHistory",
        "created": {
            "label": transl.get("general.created_at"),
            "value": obj.get("created"),
        },
        "updated": {
            "label": transl.get("general.updated_at"),
            "value": obj.get("updated"),
        },
    }
