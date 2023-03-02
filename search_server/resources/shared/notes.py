from typing import Optional

import serpy

from shared_helpers.display_fields import get_display_fields, LabelConfig
from shared_helpers.solr_connection import SolrResult


class NotesSection(serpy.AsyncDictSerializer):
    label = serpy.MethodField()
    ntype = serpy.StaticField(
        label="type",
        value="rism:NotesSection"
    )
    notes = serpy.MethodField()

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
            "additional_biography_sm": ("records.additional_biographical_information", None)
        }

        return get_display_fields(obj, transl, field_config)
