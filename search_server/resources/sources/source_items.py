from typing import Dict, List

import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult, has_results, SolrManager, SolrConnection
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
                    "is_item_record_b:true",
                    f"source_membership_id:{this_id}",
                    f"!id:{this_id}"]
        sort: str = "source_id asc"

        if not has_results(fq=fq):
            return None

        conn = SolrManager(SolrConnection)
        # increasing the number of rows means fewer requests for larger items, but NB: Solr pre-allocates memory
        # for each value in row, so there needs to be a balance between large numbers and fewer requests.
        # (remember that the SolrManager object automatically retrieves the next page of results when iterating)
        conn.search("*:*", fq=fq, sort=sort, rows=100)

        return BaseSource(conn.results, many=True,
                          context={"request": self.context.get("request")}).data
