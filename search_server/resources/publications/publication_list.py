import ypres
from small_asc.client import Results

from search_server.helpers.identifiers import get_identifier
from search_server.helpers.solr_connection import SolrConnection
from search_server.resources.publications.publication import Publication


class PublicationList(ypres.AsyncDictSerializer):
    pid = ypres.MethodField(label="id")
    ptype = ypres.StaticField(label="type", value="rism:PublicationList")
    plabel = ypres.MethodField(label="label")
    items = ypres.MethodField()

    def get_pid(self, obj: dict) -> str:
        req = self.context["request"]
        return get_identifier(req, "publications.publications_list")

    def get_plabel(self, obj: dict) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations
        return transl["records.work_catalogs"]

    async def get_items(self, obj) -> list[dict] | None:
        fq: list = ["type:publication", "is_work_catalogue_b:true"]
        results: Results = await SolrConnection.search(
            {"query": "*:*", "filter": fq, "sort": "composer_name_ans asc"}, cursor=True
        )

        if results.hits == 0:
            return None

        return await Publication(
            results, many=True, context={"request": self.context["request"]}
        ).serialized_many
