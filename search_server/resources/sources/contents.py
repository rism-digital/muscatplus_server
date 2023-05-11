import re
import urllib.parse
from typing import Optional

import ypres

from shared_helpers.display_fields import LabelConfig, get_display_fields
from shared_helpers.display_translators import (
    dramatic_roles_json_value_translator,
    title_json_value_translator,
    scoring_json_value_translator,
    material_content_types_translator,
    material_source_types_translator, key_mode_value_translator
)
from shared_helpers.identifiers import ID_SUB, get_identifier
from shared_helpers.languages import languages_translator
from shared_helpers.solr_connection import SolrResult


class ContentsSection(ypres.DictSerializer):
    section_label = ypres.MethodField(
        label="sectionLabel"
    )
    summary = ypres.MethodField()
    subjects = ypres.MethodField()

    def get_section_label(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        return transl.get("records.title_content_description")

    def get_summary(self, obj: SolrResult) -> Optional[list[dict]]:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        field_config: LabelConfig = {
            "material_source_types_sm": ("records.source_type", material_source_types_translator),
            "material_content_types_sm": ("records.content_type", material_content_types_translator),
            "key_mode_s": ("records.key_or_mode", key_mode_value_translator),
            "standard_title_s": ("records.standardized_title", None),
            "source_title_s": ("records.title_on_source", None),
            "variant_title_s": ("records.variant_source_title", None),
            "additional_titles_json": ("records.additional_title", title_json_value_translator),
            "opus_numbers_sm": ("records.opus_number", None),
            "description_summary_sm": ("records.description_summary", None),
            "dramatic_roles_json": ("records.named_dramatic_roles", dramatic_roles_json_value_translator),
            "scoring_summary_sm": ("records.scoring_summary", None),
            "scoring_json": ("records.total_scoring", scoring_json_value_translator),
            "colophon_notes_sm": ("records.colophon", None),
            "language_text_sm": ("records.language_text", languages_translator),
            "language_libretto_sm": ("records.language_libretto", languages_translator),
            "language_original_sm": ("records.language_original_text", languages_translator),
            "language_notes_sm": ("records.language_note", None),
            "rism_series_identifiers_sm": ("records.series_statement", None),
            "rism_id": ("records.rism_id_number", None),
            "source_fingerprint_s": ("records.fingerprint_identifier", None),
        }

        return get_display_fields(obj, transl, field_config=field_config)

    def get_subjects(self, obj: SolrResult) -> Optional[dict]:
        if 'subjects_json' not in obj:
            return None

        return SourceSubjectsSection(obj, context={"request": self.context.get("request"),
                                                   "session": self.context.get("session")}).data


class SourceSubjectsSection(ypres.DictSerializer):
    section_label = ypres.MethodField(
        label="sectionLabel"
    )
    items = ypres.MethodField()

    def get_section_label(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        return transl.get("records.subject_headings")

    def get_items(self, obj: SolrResult) -> list:
        return SourceSubject(obj['subjects_json'],
                             many=True,
                             context={"request": self.context.get("request"),
                                      "session": self.context.get("session")}).data


# A minimal subject serializer. This is because the data for the subjects
# comes from the JSON field on the source, rather than from the Solr records
# for subjects.
class SourceSubject(ypres.DictSerializer):
    sid = ypres.MethodField(
        label="id"
    )
    stype = ypres.StaticField(
        label="type",
        value="rism:Subject"
    )
    label = ypres.MethodField()
    value = ypres.MethodField()

    def get_sid(self, obj: dict) -> str:
        req = self.context.get("request")
        subject_id: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "subjects.subject", subject_id=subject_id)

    def get_label(self, obj: dict) -> dict:
        return {"none": [obj.get("subject")]}

    def get_value(self, obj: dict) -> str:
        if "subject" not in obj:
            return ""
        return urllib.parse.quote_plus(obj["subject"])
