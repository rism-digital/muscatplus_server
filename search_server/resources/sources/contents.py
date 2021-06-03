import re
from typing import Dict, Optional, List

import serpy

from search_server.helpers.display_fields import LabelConfig, get_display_fields
from search_server.helpers.display_translators import (
    dramatic_roles_json_value_translator,
    title_json_value_translator,
    secondary_literature_json_value_translator,
    scoring_json_value_translator)
from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.languages import languages_translator
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult
from search_server.resources.shared.relationship import Relationship


class ContentsSection(JSONLDContextDictSerializer):
    label = serpy.MethodField()
    stype = StaticField(
        label="type",
        value="rism:ContentsSection"
    )
    creator = serpy.MethodField()
    summary = serpy.MethodField()
    subjects = serpy.MethodField()

    def get_label(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        return transl.get("records.title_content_description")

    def get_creator(self, obj: SolrResult) -> Optional[Dict]:
        if 'creator_json' not in obj:
            return None

        return Relationship(obj["creator_json"][0],
                            context={"request": self.context.get('request')}).data

    def get_summary(self, obj: SolrResult) -> Optional[List[Dict]]:
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        field_config: LabelConfig = {
            "source_type_sm": ("records.source_type", None),
            "source_title_s": ("records.title_on_source", None),
            "variant_title_s": ("records.variant_source_title", None),
            "standard_titles_json": ("records.standardized_title", title_json_value_translator),
            "works_catalogue_json": ("records.catalog_works", secondary_literature_json_value_translator),
            "additional_titles_json": ("records.additional_title", title_json_value_translator),
            "opus_numbers_sm": ("records.opus_number", None),
            "description_summary_sm": ("records.description_summary", None),
            "dramatic_roles_json": ("records.named_dramatic_roles", dramatic_roles_json_value_translator),
            "scoring_json": ("records.total_scoring", scoring_json_value_translator),
            "colophon_notes_sm": ("records.colophon", None),
            "language_text_sm": ("records.language_text", languages_translator),
            "language_libretto_sm": ("records.language_libretto", languages_translator),
            "language_original_sm": ("records.language_original_text", languages_translator),
            "language_notes_sm": ("records.language_note", None),
            "rism_id": ("records.rism_id_number", None)
        }

        return get_display_fields(obj, transl, field_config=field_config)

    def get_subjects(self, obj: SolrResult) -> Optional[Dict]:
        if 'subjects_json' not in obj:
            return None

        return SourceSubjectsSection(obj, context={"request": self.context.get("request")}).data


class SourceSubjectsSection(JSONLDContextDictSerializer):
    stype = StaticField(
        label="type",
        value="rism:SourceSubjectSection"
    )
    label = serpy.MethodField()
    items = serpy.MethodField()

    def get_label(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        return transl.get("records.subject_headings")

    def get_items(self, obj: SolrResult) -> List:
        return SourceSubject(obj['subjects_json'],
                             many=True,
                             context={"request": self.context.get("request")}).data


# A minimal subject serializer. This is because the data for the subjects
# comes from the JSON field on the source, rather than from the Solr records
# for subjects.
class SourceSubject(JSONLDContextDictSerializer):
    sid = serpy.MethodField(
        label="id"
    )
    stype = StaticField(
        label="type",
        value="rism:Subject"
    )
    term = serpy.MethodField()

    def get_sid(self, obj: Dict) -> str:
        req = self.context.get("request")
        subject_id: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "subjects.subject", subject_id=subject_id)

    def get_term(self, obj: Dict) -> Dict:
        return {"none": [obj.get("subject")]}
