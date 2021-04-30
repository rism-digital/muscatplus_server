from typing import Dict

import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult


class ReferencesNotesSection(JSONLDContextDictSerializer):
    label = serpy.MethodField()
    stype = StaticField(
        label="type",
        value="rism:ReferencesNotesSection"
    )

    def get_label(self, obj: SolrResult):
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        return transl.get("records.references_and_notes")
