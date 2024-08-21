from typing import Optional

import ypres

from shared_helpers.display_fields import LabelConfig, get_display_fields
from shared_helpers.display_translators import (
    secondary_literature_json_value_translator,
)
from shared_helpers.solr_connection import SolrResult


class NotesSection(ypres.AsyncDictSerializer):
    label = ypres.MethodField()
    ntype = ypres.StaticField(label="type", value="rism:NotesSection")
    notes = ypres.MethodField()

    def get_label(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        # TODO: Change this to just 'notes' when the translation is available.
        return transl.get("records.references_and_notes")

    def get_notes(self, obj: SolrResult) -> Optional[list]:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        field_config: LabelConfig = {
            "general_notes_sm": ("records.general_note", None),
            "additional_biography_sm": (
                "records.additional_biographical_information",
                None,
            ),
            "institution_history_sm": ("records.history_institution", None),
            "bibliographic_references_json": (
                "records.bibliographic_reference",
                secondary_literature_json_value_translator,
            ),
        }

        return get_display_fields(obj, transl, field_config)
