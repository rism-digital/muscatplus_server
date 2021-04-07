from typing import Optional, Dict, List

import serpy

from search_server.helpers.display_fields import LabelConfig, get_display_fields
from search_server.helpers.fields import StaticField
from search_server.helpers.serializers import JSONLDContextDictSerializer, ContextDictSerializer
from search_server.helpers.solr_connection import SolrResult


class NoteList(JSONLDContextDictSerializer):
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
            "description_summary_sm": ("records.description_summary", None)
        }

        return get_display_fields(obj, transl, field_config)

