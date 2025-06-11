import ypres
from small_asc.client import Results

from search_server.resources.publications.publication import Publication
from shared_helpers.identifiers import get_identifier
from shared_helpers.solr_connection import SolrConnection


class PublicationList(ypres.AsyncDictSerializer):
    pid = ypres.MethodField(label="id")
    ptype = ypres.StaticField(label="type", value="rism:PublicationList")
    plabel = ypres.MethodField(label="label")
    items = ypres.MethodField()

    def get_pid(self, obj: dict) -> str:
        req = self.context["request"]
        return get_identifier(req, "publications.publications_list")

    def get_plabel(self, obj: dict) -> dict:
        return {"none": ["Work Catalogs"]}

    async def get_items(self, obj) -> list[dict] | None:
        fq: list = ["type:publication", "is_work_catalogue_b:true"]
        results: Results = await SolrConnection.search(
            {"query": "*:*", "filter": fq}, cursor=True
        )

        if results.hits == 0:
            return None

        return await Publication(
            results, many=True, context={"request": self.context["request"]}
        ).serialized_many
