SOURCE_TYPE_MAP: dict = {
    "printed": "rism:PrintedSource",
    "manuscript": "rism:ManuscriptSource",
    "composite": "rism:CompositeSource",
    "unspecified": "rism:UnspecifiedSource"
}

RECORD_TYPE_MAP: dict = {
    "item": "rism:ItemRecord",
    "single_item": "rism:SingleItemRecord",
    "collection": "rism:CollectionRecord",
    "composite": "rism:CompositeRecord"
}

CONTENT_TYPE_MAP: dict = {
    "libretto": "rism:LibrettoContent",
    "treatise": "rism:TreatiseContent",
    "musical": "rism:MusicalContent",
    "other": "rism:OtherContent"
}


def create_record_block(record_type: str, source_type: str, content_types: list[str]) -> dict:
    type_identifier: str = SOURCE_TYPE_MAP[source_type]
    content_type_block: list = []

    for c in content_types:
        content_type_block.append({
            "label": {"none": [c]},  # TODO translate!
            "type": CONTENT_TYPE_MAP.get(c, "rism:MusicalSource")
        })

    record_type_identifier: str = RECORD_TYPE_MAP[record_type]

    return {
        "recordType": {
            "label": {"none": [record_type]},  # TODO: Translate!
            "type": record_type_identifier
        },
        "sourceType": {
            "label": {"none": [source_type]},  # TODO: Translate!
            "type": type_identifier
        },
        "contentTypes": content_type_block
    }
