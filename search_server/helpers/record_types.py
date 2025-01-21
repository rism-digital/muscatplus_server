from shared_helpers.display_translators import (
    content_type_translator,
    record_type_translator,
    source_type_translator,
)

SOURCE_TYPE_MAP: dict = {
    "printed": "rism:PrintedSource",
    "manuscript": "rism:ManuscriptSource",
    "composite": "rism:CompositeSource",
    "unspecified": "rism:UnspecifiedSource",
}

RECORD_TYPE_MAP: dict = {
    "item": "rism:ItemRecord",
    "single_item": "rism:SingleItemRecord",
    "collection": "rism:CollectionRecord",
    "composite": "rism:CompositeRecord",
}

CONTENT_TYPE_MAP: dict = {
    "libretto": "rism:LibrettoContent",
    "treatise": "rism:TreatiseContent",
    "musical": "rism:MusicalContent",
    "mixed": "rism:MixedContent",
    "other": "rism:OtherContent",
}


def create_source_types_block(
    record_type: str, source_type: str, content_types: list[str], translations: dict
) -> dict:
    type_identifier: str = SOURCE_TYPE_MAP[source_type]
    content_type_block: list = []

    for c in content_types:
        label = content_type_translator(c, translations)
        content_type_block.append(
            {"label": label, "type": CONTENT_TYPE_MAP.get(c, "rism:MusicalSource")}
        )

    record_type_identifier: str = RECORD_TYPE_MAP[record_type]
    record_type_label = record_type_translator(record_type, translations)
    source_type_label = source_type_translator(source_type, translations)
    return {
        "recordType": {"label": record_type_label, "type": record_type_identifier},
        "sourceType": {"label": source_type_label, "type": type_identifier},
        "contentTypes": content_type_block,
    }
