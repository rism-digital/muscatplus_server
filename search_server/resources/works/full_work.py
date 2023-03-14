import re
from typing import Optional

import serpy
from small_asc.client import Results

from search_server.resources.sources.base_source import BaseSource, SOLR_FIELDS_FOR_BASE_SOURCE
from shared_helpers.identifiers import ID_SUB, get_identifier
from search_server.resources.works.base_work import BaseWork
from shared_helpers.solr_connection import SolrResult, SolrConnection


class FullWork(BaseWork):
    sources = serpy.MethodField()

    async def get_sources(self, obj: SolrResult) -> Optional[dict]:
        req = self.context.get("request")
        work_id: str = obj.get("id")
        source_count: int = obj.get("source_count_i", 0)

        ident: str = re.sub(ID_SUB, "", work_id)

        d: dict = {
            "url": get_identifier(req, "works.work_sources", work_id=ident),
            "totalItems": source_count
        }

        items: Optional[list] = await get_source_objects(req, work_id)
        if items:
            d["items"] = items

        return d


async def get_source_objects(req, work_id: str) -> Optional[list]:
    fq = ["type:source",
          f"work_ids:{work_id}"]

    sort: str = "main_title_ans asc"
    source_results: Results = await SolrConnection.search({"query": "*:*",
                                                           "filter": fq,
                                                           "fields": SOLR_FIELDS_FOR_BASE_SOURCE,
                                                           "sort": sort}, cursor=True)

    if source_results.hits == 0:
        return None

    items: list[dict] = []

    async for res in source_results:
        items.append(await BaseSource(res,
                                      context={"request": req}).data)

    return items or None
