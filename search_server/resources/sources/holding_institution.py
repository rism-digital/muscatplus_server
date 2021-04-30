from typing import Dict

import serpy as serpy

from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult


class HoldingInstitutionSection(JSONLDContextDictSerializer):
    label = serpy.MethodField()

    def get_label(self, obj: SolrResult):
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        return transl.get("records.library_information_relations")
