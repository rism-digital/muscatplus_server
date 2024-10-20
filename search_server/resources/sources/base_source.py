import logging
import re
from typing import Optional

import ypres

from search_server.helpers.record_types import create_source_types_block
from search_server.resources.shared.record_history import get_record_history
from search_server.resources.shared.relationship import Relationship
from shared_helpers.display_fields import LabelConfig, get_display_fields
from shared_helpers.display_translators import (
    material_content_types_translator,
    material_source_types_translator,
)
from shared_helpers.formatters import format_source_label
from shared_helpers.identifiers import ID_SUB, get_identifier
from shared_helpers.solr_connection import SolrResult

# The Solr fields necessary to construct a base source record. Helps cut down on internal Solr
# communication by limiting the fields to only those that are necessary.
SOLR_FIELDS_FOR_BASE_SOURCE: list = [
    "id",
    "type",
    "main_title_s",
    "material_source_types_sm",
    "material_content_types_sm",
    "shelfmark_s",
    "siglum_s",
    "source_membership_json",
    "source_id",
    "creator_name_s",
    "source_type_s",
    "content_types_sm",
    "record_type_s",
    "created",
    "updated",
    "main_title_ans",
    "standard_titles_json",
]

log = logging.getLogger("mp_server")


class BaseSource(ypres.AsyncDictSerializer):
    """
    A base source serializer for providing a basic set of information for
    a RISM Source. A full record of the source is provided by the full source
    serializer, which adds additional information to this
    """

    sid = ypres.MethodField(label="id")
    stype = ypres.StaticField(label="type", value="rism:Source")
    type_label = ypres.MethodField(label="typeLabel")
    label = ypres.MethodField()
    creator = ypres.MethodField()
    part_of = ypres.MethodField(label="partOf")
    summary = ypres.MethodField()
    source_types = ypres.MethodField(label="sourceTypes")
    record_history = ypres.MethodField(label="recordHistory")

    def get_sid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        source_id_val = (
            obj.get("id") if obj.get("type") == "source" else obj.get("source_id")
        )
        source_id: str = re.sub(ID_SUB, "", source_id_val)

        return get_identifier(req, "sources.source", source_id=source_id)

    def get_label(self, obj: SolrResult) -> dict:
        if "standard_titles_json" not in obj:
            return {"none": [obj.get("main_title_s", "[No title]")]}

        req = self.context.get("request")
        transl: dict = req.ctx.translations
        label = format_source_label(obj["standard_titles_json"], transl)

        return label

    def get_type_label(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        return transl.get("records.source")

    async def get_creator(self, obj: SolrResult) -> Optional[dict]:
        if "creator_json" not in obj:
            return None

        return await Relationship(
            obj["creator_json"][0],
            context={
                "request": self.context.get("request"),
                "reltype": "rism:Creator",
                "session": self.context.get("session"),
            },
        ).data

    def get_part_of(self, obj: SolrResult) -> Optional[dict]:
        # This source is not part of another source; return None
        if "source_membership_json" not in obj:
            return None

        source_membership: dict = obj.get("source_membership_json", {})
        req = self.context.get("request")
        parent_source_id: str = re.sub(ID_SUB, "", source_membership.get("source_id"))
        ident: str = get_identifier(req, "sources.source", source_id=parent_source_id)
        transl: dict = req.ctx.translations

        parent_title: str = source_membership.get("main_title", "[No title]")
        parent_shelfmark: Optional[str] = source_membership.get("shelfmark")
        parent_siglum: Optional[str] = source_membership.get("siglum")
        parent_material_types: Optional[list] = source_membership.get("material_types")

        # NB: This should match the format in formatters.format_source_label! But since
        # we're dealing with a JSON field the names are different, and we only do this
        # once in the whole app.
        label: str = parent_title
        if parent_material_types:
            label = f"{label}; {', '.join(parent_material_types)}"
        if parent_siglum and parent_shelfmark:
            label = f"{label}; {parent_siglum} {parent_shelfmark}"

        record_type: str = source_membership.get("record_type", "item")
        source_type: str = source_membership.get("source_type", "unspecified")
        content_types: list[str] = source_membership.get("content_types", [])

        source_types_block: dict = create_source_types_block(
            record_type, source_type, content_types, transl
        )

        return {
            "sectionLabel": transl.get("records.item_part_of"),
            "source": {
                "id": ident,
                "type": "rism:Source",
                "typeLabel": transl.get("records.source"),
                "sourceTypes": source_types_block,
                "label": {"none": [label]},
            },
        }

    # This method will get overridden in the 'full source' class, and will be returned as 'None' since
    # the summary is part of the 'contents' section. But in the base source view it will deliver some basic
    # identification fields.
    def get_summary(self, obj: SolrResult) -> Optional[list[dict]]:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        field_config: LabelConfig = {
            "source_member_composers_sm": ("records.composer", None),
            "creator_name_s": ("records.composer_author", None),
            "institution_s": ("records.institution", None),
            "date_statements_sm": ("records.dates", None),
            "num_source_members_i": ("records.items_in_source", None),
            "material_source_types_sm": (
                "records.source_type",
                material_source_types_translator,
            ),
            "material_content_types_sm": (
                "records.content_type",
                material_content_types_translator,
            ),
            "standard_title_s": ("records.standardized_title", None),
        }

        return get_display_fields(obj, transl, field_config=field_config)

    def get_source_types(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.ctx.translations
        source_type: str = obj.get("source_type_s", "unspecified")
        content_identifiers: list[str] = obj.get("content_types_sm", [])
        record_type: str = obj.get("record_type_s", "item")

        return create_source_types_block(
            record_type, source_type, content_identifiers, transl
        )

    def get_record_history(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        return get_record_history(obj, transl)
