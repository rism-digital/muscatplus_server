import ypres

from search_server.helpers.display_fields import LabelConfig, get_display_fields
from search_server.helpers.display_translators import (
    secondary_literature_json_value_translator,
)
from search_server.helpers.identifiers import get_identifier
from search_server.helpers.solr_connection import SolrResult


class NotesSection(ypres.DictSerializer):
    sid = ypres.MethodField(label="id")
    slabel = ypres.MethodField(label="label")
    ntype = ypres.StaticField(label="type", value="rism:NotesSection")
    notes = ypres.MethodField()

    def get_sid(self, obj: SolrResult) -> str | None:
        req = self.context["request"]
        route_name = self.context["section_route"]
        route_params = self.context["route_params"]

        return get_identifier(req, route_name, **route_params)

    def get_slabel(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        # TODO: Change this to just 'notes' when the translation is available.
        return transl["records.references_and_notes"]

    def get_notes(self, obj: SolrResult) -> list | None:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        field_config: LabelConfig = {
            "general_notes_sm": ("records.general_note", None),
            "institution_history_sm": ("records.history_institution", None),
            "bibliographic_references_json": (
                "records.bibliographic_reference",
                secondary_literature_json_value_translator,
            ),
            "source_data_found_json": (
                "records.source_data_found",
                secondary_literature_json_value_translator,
            ),
            "work_catalogue_notes_sm": ("records.work_catalog_note", None),
        }

        return get_display_fields(obj, transl, field_config)
