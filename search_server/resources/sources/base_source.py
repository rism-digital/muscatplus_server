import ypres

from search_server.helpers.display_fields import LabelConfig, get_display_fields
from search_server.helpers.display_translators import (
    material_content_types_translator,
    material_source_types_translator,
)
from search_server.helpers.formatters import format_source_label
from search_server.helpers.identifiers import get_identifier, strip_prefix
from search_server.helpers.record_types import create_source_types_block
from search_server.helpers.solr_connection import SolrResult
from search_server.resources.shared.part_of import PartOfSection
from search_server.resources.shared.record_history import get_record_history
from search_server.resources.shared.relationship import Relationship


class BaseSource(ypres.AsyncDictSerializer):
    """
    A base source serializer for providing a basic set of information for
    a RISM Source. A full record of the source is provided by the full source
    serializer, which adds additional information to this
    """

    sid = ypres.MethodField(label="id")
    stype = ypres.StaticField(label="type", value="rism:Source")
    type_label = ypres.MethodField(label="typeLabel")
    slabel = ypres.MethodField(label="label")
    creator = ypres.MethodField()
    part_of = ypres.MethodField(label="partOf")
    summary = ypres.MethodField()
    source_types = ypres.MethodField(label="sourceTypes")
    record_history = ypres.MethodField(label="recordHistory")

    def get_sid(self, obj: SolrResult) -> str:
        req = self.context["request"]
        source_id_val = obj["id"] if obj.get("type") == "source" else obj["source_id"]
        source_id: str = strip_prefix(source_id_val)

        return get_identifier(req, "sources.source", source_id=source_id)

    def get_slabel(self, obj: SolrResult) -> dict:
        if "standard_titles_json" not in obj:
            return {"none": [obj.get("main_title_s", "[No title]")]}

        req = self.context["request"]
        transl: dict = req.ctx.translations
        label = format_source_label(obj["standard_titles_json"], transl)

        return label

    def get_type_label(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return transl["records.source"]

    def get_creator(self, obj: SolrResult) -> dict | None:
        if "creator_json" not in obj:
            return None

        return Relationship(
            obj["creator_json"][0],
            context={
                "request": self.context["request"],
            },
        ).serialized

    def get_part_of(self, obj: SolrResult) -> dict | None:
        # This source is not part of another source; return None
        if "source_membership_json" not in obj:
            return None

        return PartOfSection(
            obj, context={"request": self.context["request"]}
        ).serialized

    # This method will get overridden in the 'full source' class, and will be returned as 'None' since
    # the summary is part of the 'contents' section. But in the base source view it will deliver some basic
    # identification fields.
    def get_summary(self, obj: SolrResult) -> list[dict] | None:
        req = self.context["request"]
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
        req = self.context["request"]
        transl: dict = req.ctx.translations
        source_type: str = obj.get("source_type_s", "unspecified")
        content_identifiers: list[str] = obj.get("content_types_sm", [])
        record_type: str = obj.get("record_type_s", "item")

        return create_source_types_block(
            record_type, source_type, content_identifiers, transl
        )

    def get_record_history(self, obj: SolrResult) -> dict | None:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return get_record_history(obj, transl)
