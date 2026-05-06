import ypres

from search_server.helpers.display_fields import LabelConfig, get_display_fields
from search_server.helpers.display_translators import (
    dramatic_roles_json_value_translator,
    key_mode_value_translator,
    material_content_types_translator,
    material_source_types_translator,
    periodical_value_translator,
    scoring_json_value_translator,
    title_json_value_translator,
)
from search_server.helpers.languages import languages_translator
from search_server.helpers.solr_connection import SolrResult
from search_server.resources.shared.subjects import SubjectsSection


class ContentsSection(ypres.DictSerializer):
    section_label = ypres.MethodField(label="sectionLabel")
    summary = ypres.MethodField()
    subjects = ypres.MethodField()

    def get_section_label(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return transl["records.title_content_description"]

    def get_summary(self, obj: SolrResult) -> list[dict] | None:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        field_config: LabelConfig = {
            "material_source_types_sm": (
                "records.source_type",
                material_source_types_translator,
            ),
            "material_content_types_sm": (
                "records.content_type",
                material_content_types_translator,
            ),
            "date_statements_sm": ("records.dates", None),
            "key_mode_s": ("records.key_or_mode", key_mode_value_translator),
            "standard_title_s": ("records.standardized_title", None),
            "source_title_sm": ("records.title_on_source", None),
            "variant_titles_sm": ("records.variant_source_title", None),
            "additional_titles_json": (
                "records.additional_title",
                title_json_value_translator,
            ),
            "common_name_s": ("records.additional_title", None),
            "opus_numbers_sm": ("records.opus_number", None),
            "description_summary_sm": ("records.description_summary", None),
            "periodical_series_json": (
                "records.periodical_or_series",
                periodical_value_translator,
            ),
            "dramatic_roles_json": (
                "records.named_dramatic_roles",
                dramatic_roles_json_value_translator,
            ),
            "scoring_summary_sm": ("records.scoring_summary", None),
            "physical_dimensions_s": ("records.dimensions", None),
            "scoring_json": ("records.total_scoring", scoring_json_value_translator),
            "colophon_notes_sm": ("records.colophon", None),
            "language_text_sm": ("records.language_text", languages_translator),
            "language_original_sm": (
                "records.language_original_text",
                languages_translator,
            ),
            "language_notes_sm": ("records.language_note", None),
            "rism_series_identifiers_sm": ("records.series_statement", None),
            "source_fingerprint_s": ("records.fingerprint_identifier", None),
            "access_restrictions_sm": ("records.access_restrictions", None),
            "full_rism_id": ("records.rism_id_number", None),
        }

        return get_display_fields(obj, transl, field_config=field_config)

    def get_subjects(self, obj: SolrResult) -> dict | None:
        if "subjects_json" not in obj:
            return None

        return SubjectsSection(
            obj,
            context={
                "request": self.context["request"],
            },
        ).serialized
