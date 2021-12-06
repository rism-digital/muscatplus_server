import re
from typing import Optional

import serpy

from search_server.helpers.display_fields import LabelConfig, get_display_fields
from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult
from search_server.resources.shared.record_history import get_record_history

SOURCE_TYPE_MAP: dict = {
    "printed": "rism:PrintedSource",
    "manuscript": "rism:ManuscriptSource",
    "composite": "rism:CompositeSource",
    "unspecified": "rism:UnspecifiedSource"
}

RECORD_TYPE_MAP: dict = {
    "item": "rism:ItemRecord",
    "collection": "rism:CollectionRecord",
    "composite": "rism:CompositeRecord"
}

CONTENT_TYPE_MAP: dict = {
    "libretto": "rism:LibrettoContent",
    "treatise": "rism:TreatiseContent",
    "musical": "rism:MusicalContent",
    "composite_content": "rism:CompositeContent"
}


class BaseSource(JSONLDContextDictSerializer):
    """
    A base source serializer for providing a basic set of information for
    a RISM Source. A full record of the source is provided by the full source
    serializer, which adds additional information to this
    """
    sid = serpy.MethodField(
        label="id"
    )
    stype = StaticField(
        label="type",
        value="rism:Source"
    )
    type_label = serpy.MethodField(
        label="typeLabel"
    )
    label = serpy.MethodField()
    part_of = serpy.MethodField(
        label="partOf"
    )
    summary = serpy.MethodField()
    record = serpy.MethodField()
    record_history = serpy.MethodField(
        label="recordHistory"
    )

    def get_sid(self, obj: SolrResult) -> str:
        req = self.context.get('request')
        source_id_val = obj.get("id") if obj.get('type') == "source" else obj.get("source_id")
        source_id: str = re.sub(ID_SUB, "", source_id_val)

        return get_identifier(req, "sources.source", source_id=source_id)

    def get_label(self, obj: SolrResult) -> dict:
        title: str = obj.get("main_title_s", "[No title]")
        #  TODO: Translate source types
        source_types: Optional[list] = obj.get("material_group_types_sm")
        shelfmark: Optional[str] = obj.get("shelfmark_s")
        siglum: Optional[str] = obj.get("siglum_s")

        label: str = title
        if source_types:
            label = f"{label}; {', '.join(source_types)}"
        if siglum and shelfmark:
            label = f"{label}; {siglum} {shelfmark}"

        return {"none": [label]}

    def get_type_label(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl = req.app.ctx.translations

        return transl.get("records.source")

    def get_part_of(self, obj: SolrResult) -> Optional[dict]:
        # This source is not part of another source; return None
        if 'source_membership_json' not in obj:
            return None

        source_membership: dict = obj.get('source_membership_json', {})

        req = self.context.get('request')
        parent_source_id: str = re.sub(ID_SUB, "", source_membership.get("source_id"))
        ident: str = get_identifier(req, "sources.source", source_id=parent_source_id)
        transl = req.app.ctx.translations

        parent_title: Optional[str] = source_membership.get("main_title")

        return {
            "label": transl.get("records.item_part_of"),
            "type": "rism:PartOfSection",
            "source": {
                "id": ident,
                "type": "rism:Source",
                "typeLabel": transl.get("records.source"),
                "label": {"none": [parent_title]}
            }
        }

    # This method will get overridden in the 'full source' class, and will be returned as 'None' since
    # the summary is part of the 'contents' section. But in the base source view it will deliver some basic
    # identification fields.
    def get_summary(self, obj: SolrResult) -> Optional[list[dict]]:
        print(obj)
        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        field_config: LabelConfig = {
            "creator_name_s": ("records.composer_author", None),
            "material_group_types_sm": ("records.type", None),
        }

        return get_display_fields(obj, transl, field_config=field_config)

    def get_record(self, obj: SolrResult) -> dict:
        source_type: str = obj.get("source_type_s", "unspecified")
        type_identifier: str = SOURCE_TYPE_MAP.get(source_type)

        content_identifiers: list = obj.get("content_types_sm", [])
        content_type_block: list = []

        for c in content_identifiers:
            content_type_block.append({
                "label": {"none": [c]},  # TODO translate!
                "type": CONTENT_TYPE_MAP.get(c, "rism:MusicalSource")
            })

        record_type: str = obj.get("record_type_s", "contents")
        record_type_identifier: str = RECORD_TYPE_MAP.get(record_type)

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

    def get_record_history(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        return get_record_history(obj, transl)
