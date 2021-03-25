from typing import Optional, Dict, List

import serpy

from search_server.helpers.display_fields import get_display_fields, LabelConfig
from search_server.helpers.fields import StaticField
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult


class PersonNoteList(JSONLDContextDictSerializer):
    label = serpy.MethodField()
    ntype = StaticField(
        label="type",
        value="rism:NoteList"
    )
    items = serpy.MethodField()

    def get_label(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.translations

        return transl.get("records.references_and_notes")

    def get_items(self, obj: SolrResult) -> Optional[List]:
        req = self.context.get("request")
        transl = req.app.translations

        field_config: LabelConfig = {
            "general_notes_sm": ("records.general_note", None),
            "additional_biography_sm": ("records.additional_biographical_information", None)
        }

        return get_display_fields(obj, transl, field_config)
