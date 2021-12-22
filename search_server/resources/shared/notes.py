from typing import Optional

import serpy

from search_server.helpers.display_fields import get_display_fields, LabelConfig
from search_server.helpers.fields import StaticField
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult


class NotesSection(JSONLDContextDictSerializer):
    label = serpy.MethodField()
    ntype = StaticField(
        label="type",
        value="rism:NotesSection"
    )
    notes = serpy.MethodField()

    def get_label(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        # TODO: Change this to just 'notes' when the translation is available.
        return transl.get("records.references_and_notes")

    def get_notes(self, obj: SolrResult) -> Optional[list]:
        req = self.context.get("request")
        transl = req.app.ctx.translations

        field_config: LabelConfig = {
            "general_notes_sm": ("records.general_note", None),
            "additional_biography_sm": ("records.additional_biographical_information", None)
        }

        return get_display_fields(obj, transl, field_config)
