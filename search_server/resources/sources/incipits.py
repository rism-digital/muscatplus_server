from typing import Optional

import serpy
from small_asc.client import Results

from shared_helpers.fields import StaticField
from shared_helpers.serializers import JSONLDContextDictSerializer
from shared_helpers.solr_connection import SolrResult, SolrConnection
from search_server.resources.incipits.incipit import Incipit


class IncipitsSection(JSONLDContextDictSerializer):
    label = serpy.MethodField()
    stype = StaticField(
        label="type",
        value="rism:IncipitsSection"
    )
    items = serpy.MethodField()

    def get_label(self, obj: SolrResult):
        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        return transl.get("records.incipits")

    def get_items(self, obj: SolrResult) -> Optional[list]:
        fq: list = [f"source_id:{obj.get('id')}",
                    "type:incipit"]
        sort: str = "work_num_ans asc"

        results: Results = SolrConnection.search({"query": "*:*",
                                                  "filter": fq,
                                                  "sort": sort}, cursor=True)

        # It will be strange for this to happen, since we only
        # call this code if the record has said there are incipits
        # for this source. Nevertheless, we'll be safe and return
        # None here.
        if results.hits == 0:
            return None

        return Incipit(results,
                       many=True,
                       context={"request": self.context.get("request")}).data
