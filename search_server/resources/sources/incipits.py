from typing import Dict, Optional, List

import serpy
from small_asc.client import Results

from search_server.helpers.fields import StaticField
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult, SolrConnection
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
        transl: Dict = req.app.ctx.translations

        return transl.get("records.incipits")

    def get_items(self, obj: SolrResult) -> Optional[List]:
        fq: List = [f"source_id:{obj.get('id')}",
                    "type:incipit"]
        sort: str = "work_num_ans asc"
        rows: int = 100

        results: Results = SolrConnection.search({"params": {"q": "*:*", "fq": fq, "sort": sort, "rows": rows}},
                                                 cursor=True)

        # It will be strange for this to happen, since we only
        # call this code if the record has said there are incipits
        # for this source. Nevertheless, we'll be safe and return
        # None here.
        if results.hits == 0:
            return None

        # TODO: Change to serializing all, not just the first page!
        return Incipit(results,
                       many=True,
                       context={"request": self.context.get("request")}).data
