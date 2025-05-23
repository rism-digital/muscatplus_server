import re

import ypres
from small_asc.client import Results

from search_server.resources.incipits.incipit import (
    WorkIncipitsSection,
)
from search_server.resources.shared.external_resources import ExternalResourcesSection
from search_server.resources.sources.base_source import (
    BaseSource,
)
from search_server.resources.works.base_work import BaseWork
from shared_helpers.identifiers import ID_SUB, get_identifier
from shared_helpers.solr_connection import SolrConnection, SolrResult


class FullWork(BaseWork):
    incipits = ypres.MethodField()
    sources = ypres.MethodField()
    external_resources = ypres.MethodField(label="externalResources")
    works_catalogue = ypres.MethodField(label="worksCatalogue")

    async def get_incipits(self, obj: SolrResult) -> dict | None:
        if not obj.get("has_incipits_b", False):
            return None

        req = self.context["request"]
        return await WorkIncipitsSection(
            obj, context={"request": req}
        ).serialized

    def get_external_resources(self, obj: SolrResult) -> dict | None:
        if "external_resources_json" not in obj and not obj.get(
                "has_external_record_b", False
        ):
            return None

        return ExternalResourcesSection(
            obj,
            context={
                "request": self.context["request"],
            },
        ).serialized

    def get_works_catalogue(self, obj: SolrResult) -> dict | None:
        if "works_catalogue_json" not in obj:
            return None

        wc = obj["works_catalogue_json"][0]
        wc_id = re.sub(ID_SUB, "", wc["id"])
        req = self.context["request"]

        return {
            "id": get_identifier(req, "publications.publication", publication_id=wc_id),
            "label": {"none": [wc["formatted"]]},
        }

    def get_sources(self, obj: SolrResult) -> dict | None:
        source_count: int = obj.get("source_count_i", 0)
        if source_count == 0:
            return None

        req = self.context["request"]
        work_id: str = obj["id"]
        ident: str = re.sub(ID_SUB, "", work_id)

        d: dict = {
            "url": get_identifier(req, "works.work_sources", work_id=ident),
            "totalItems": source_count,
        }

        return d


async def get_source_objects(req, work_id: str) -> list | None:
    fq = ["type:source", f"work_ids:{work_id}"]

    sort: str = "main_title_ans asc"
    source_results: Results = await SolrConnection.search(
        {
            "query": "*:*",
            "filter": fq,
            "sort": sort,
        },
        cursor=True,
    )

    if source_results.hits == 0:
        return None

    items: list[dict] = []

    async for res in source_results:
        items.append(await BaseSource(res, context={"request": req}).serialized)

    return items or None
