import logging
import re
from typing import Optional

import ypres
from small_asc.client import Results

from search_server.resources.sources.base_source import BaseSource
from shared_helpers.identifiers import ID_SUB, get_identifier
from shared_helpers.solr_connection import SolrConnection, SolrResult

log = logging.getLogger("mp_server")


class SourceItemsSection(ypres.AsyncDictSerializer):
    section_label = ypres.MethodField(label="sectionLabel")
    url = ypres.MethodField()
    total_items = ypres.MethodField(label="totalItems")
    items = ypres.MethodField()

    def get_section_label(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        return transl.get("records.items_in_source")

    def get_url(self, obj: SolrResult) -> str:
        source_id: str = obj["id"]
        ident: str = re.sub(ID_SUB, "", source_id)

        return get_identifier(
            self.context.get("request"), "sources.contents", source_id=ident
        )

    def get_total_items(self, obj: SolrResult) -> int:
        return obj.get("num_source_members_i", 0)

    async def get_items(self, obj: SolrResult) -> Optional[list]:
        this_id: str = obj.get("id")
        is_composite: bool = obj["record_type_s"] == "composite"

        # Remember to filter out the current source from the list of
        # all sources in this membership group.
        if is_composite:
            fq = [
                "type:source OR type:holding",
                f"source_membership_id:{this_id} OR composite_parent_id:{this_id}",
                f"!id:{this_id}",
            ]
        else:
            fq = ["type:source", f"source_membership_id:{this_id}", f"!id:{this_id}"]
        # Sort first by the sort order of the record in the parent, but fall back to the
        # sort order of the source_id if that isn't present.
        sort: str = "source_membership_order_i asc, source_id asc"
        source_results: Results = await SolrConnection.search(
            {"query": "*:*", "filter": fq, "sort": sort, "limit": 100},
            cursor=True,
            session=self.context.get("session"),
        )

        if source_results.hits == 0:
            return None

        items: list[dict] = []

        async for res in source_results:
            if res["type"] == "source":
                items.append(
                    await BaseSource(
                        res,
                        context={
                            "request": self.context.get("request"),
                            "session": self.context.get("session"),
                        },
                    ).data
                )
            elif res["type"] == "holding" and is_composite:
                # This requires a Solr lookup, so it's slower, but it should only happen on a small
                # proportion of the results.
                source_id: str = res["source_id"]
                source_doc: Optional[dict] = await SolrConnection.get(
                    source_id, session=self.context.get("session")
                )

                if not source_doc:
                    log.error("Could not load source for holding %s", res["id"])
                    continue

                items.append(
                    await BaseSource(
                        source_doc,
                        context={
                            "request": self.context.get("request"),
                            "session": self.context.get("session"),
                        },
                    ).data
                )
            else:
                log.error("Unexpected result type %s for %s", res.get("type"), this_id)
                continue

        return items or None
