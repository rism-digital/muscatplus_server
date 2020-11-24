from typing import Union, Optional, Dict, List

import serpy

from search_server.helpers.display_fields import get_display_fields, LabelConfig
from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import get_jsonld_context
from search_server.helpers.serializers import ContextDictSerializer
from search_server.helpers.solr_connection import SolrResult


class SourceNoteList(ContextDictSerializer):
    ctx = serpy.MethodField(
        label="@context"
    )
    heading = serpy.MethodField()
    ntype = StaticField(
        label="type",
        value="rism:NoteList"
    )
    items = serpy.MethodField()

    def get_ctx(self, obj: SolrResult) -> Optional[Union[str, Dict]]:
        direct_request: bool = self.context.get("direct_request")
        return get_jsonld_context(self.context.get("request")) if direct_request else None

    def get_heading(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.translations

        return {
            "label": transl.get("records.further_information")
        }

    def get_items(self, obj: SolrResult) -> Optional[List]:
        req = self.context.get("request")
        transl = req.app.translations

        field_config: LabelConfig = {
            "general_notes_sm": ("records.general_note", None),
            "description_summary_sm": ("records.description_summary", None)
        }

        return get_display_fields(obj, transl, field_config)
