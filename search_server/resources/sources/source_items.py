from typing import Dict, List

import serpy
from small_asc.client import Results

from search_server.helpers.fields import StaticField
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult, has_results, SolrConnection
from search_server.resources.sources.base_source import BaseSource


class SourceItemsSection(JSONLDContextDictSerializer):
    stype = StaticField(
        label="type",
        value="rism:SourceItemsSection"
    )
    label = serpy.MethodField()
    items = serpy.MethodField()

    def get_label(self, obj: SolrResult):
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        return transl.get("records.items_in_source")

    def get_items(self, obj: SolrResult):
        this_id: str = obj.get("id")

        # Remember to filter out the current source from the list of
        # all sources in this membership group.
        fq: List = ["type:source",
                    "is_contents_record_b:true",
                    f"source_membership_id:{this_id}",
                    f"!id:{this_id}"]
        sort: str = "source_id asc"

        # if not has_results(fq=fq):
        #     return None

        results: Results = SolrConnection.search({"query": "*:*", "filter": fq, "sort": sort}, cursor=True)
        if results.hits == 0:
            return None

        return BaseSource(results,
                          many=True,
                          context={"request": self.context.get("request")}).data
