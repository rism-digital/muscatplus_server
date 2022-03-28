import re
from typing import Optional
import logging

import serpy

from search_server.helpers.display_translators import title_json_value_translator
from search_server.helpers.record_types import create_record_block
from search_server.helpers.display_fields import LabelConfig, get_display_fields
from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult
from search_server.resources.shared.record_history import get_record_history


# The Solr fields necessary to construct a base source record. Helps cut down on internal Solr
# communication by limiting the fields to only those that are necessary.
SOLR_FIELDS_FOR_BASE_SOURCE: list = [
    "id", "type", "main_title_s", "material_group_types_sm", "shelfmark_s", "siglum_s",
    "source_membership_json", "source_id", "creator_name_s", "source_type_s", "content_types_sm", "record_type_s",
    "created", "updated", "main_title_ans"
]

log = logging.getLogger(__name__)


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
        log.debug(source_membership)

        req = self.context.get('request')
        parent_source_id: str = re.sub(ID_SUB, "", source_membership.get("source_id"))
        ident: str = get_identifier(req, "sources.source", source_id=parent_source_id)
        transl = req.app.ctx.translations

        parent_title: Optional[str] = source_membership.get("main_title")

        record_type: str = source_membership.get("record_type", "item")
        source_type: str = source_membership.get("source_type", "unspecified")
        content_types: list[str] = source_membership.get("content_types", [])

        record_block: dict = create_record_block(record_type, source_type, content_types)

        log.debug(record_block)

        return {
            "label": transl.get("records.item_part_of"),
            "type": "rism:PartOfSection",
            "source": {
                "id": ident,
                "type": "rism:Source",
                "typeLabel": transl.get("records.source"),
                "record": record_block,
                "label": {"none": [parent_title]}
            }
        }

    # This method will get overridden in the 'full source' class, and will be returned as 'None' since
    # the summary is part of the 'contents' section. But in the base source view it will deliver some basic
    # identification fields.
    def get_summary(self, obj: SolrResult) -> Optional[list[dict]]:
        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        field_config: LabelConfig = {
            "source_member_composers_sm": ("records.composer", None),
            "creator_name_s": ("records.composer_author", None),
            "institution_s": ("records.institution", None),
            "date_statements_sm": ("records.dates", None),
            "num_source_members_i": ("records.items_in_source", None),
            "material_group_types_sm": ("records.material_description", None),
            "standard_titles_json": ("records.standardized_title", title_json_value_translator),
        }

        return get_display_fields(obj, transl, field_config=field_config)

    def get_record(self, obj: SolrResult) -> dict:
        source_type: str = obj.get("source_type_s", "unspecified")
        content_identifiers: list[str] = obj.get("content_types_sm", [])
        record_type: str = obj.get("record_type_s", "item")

        return create_record_block(record_type, source_type, content_identifiers)

    def get_record_history(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        return get_record_history(obj, transl)

