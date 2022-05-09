from typing import Optional

import serpy
from small_asc.client import Results

from search_server.helpers.fields import StaticField
from search_server.helpers.serializers import JSONLDContextDictSerializer
from shared_helpers.solr_connection import SolrResult, SolrConnection
from search_server.resources.sources.base_source import BaseSource


class SourceItemsSection(JSONLDContextDictSerializer):
    stype = StaticField(
        label="type",
        value="rism:SourceItemsSection"
    )
    label = serpy.MethodField()
    items = serpy.MethodField()

    def get_label(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        return transl.get("records.items_in_source")

    def get_items(self, obj: SolrResult) -> Optional[list]:
        this_id: str = obj.get("id")

        # Remember to filter out the current source from the list of
        # all sources in this membership group.
        fq: list = ["type:source",
                    "is_contents_record_b:true",
                    f"source_membership_id:{this_id}",
                    f"!id:{this_id}"]
        # Sort first by the sort order of the record in the parent, but fall back to the
        # sort order of the source_id if that isn't present.
        sort: str = "source_membership_order_i asc, source_id asc"

        source_results: Results = SolrConnection.search({"query": "*:*", "filter": fq, "sort": sort}, cursor=True)
        items: list = []

        items += BaseSource(source_results,
                            many=True,
                            context={"request": self.context.get("request")}).data

        # Check to see if we have any sources related to this through the holdings records
        # We will only do this if we are loading a 'composite' record.
        if obj.get("source_type_s") == "composite":
            composite_filters: list = ["type:holding",
                                       f"composite_parent_id:{this_id}"]
            composite_results: Results = SolrConnection.search({"query": "*:*",
                                                                "filter": composite_filters,
                                                                "sort": sort}, cursor=True)
            # Conveniently, we can pass holding records to the Base Source serializer!
            # They contain just enough of the same information to produce a basic source
            # record.
            items += BaseSource(composite_results,
                                many=True,
                                context={"request": self.context.get("request")}).data

        return items or None

