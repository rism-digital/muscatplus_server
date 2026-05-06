import ypres
from small_asc.client import Results

from search_server.helpers.identifiers import get_identifier, strip_prefix
from search_server.helpers.solr_connection import SolrConnection, SolrResult
from search_server.resources.shared.relationship import (
    Relationship,
    RelationshipsSection,
)
from search_server.resources.shared.subjects import SubjectsSection


class InventoryItemSection(ypres.AsyncDictSerializer):
    sid = ypres.MethodField(label="id")
    section_label = ypres.MethodField(label="sectionLabel")
    items = ypres.MethodField()

    def get_sid(self, obj: SolrResult) -> str:
        req = self.context["request"]
        source_id = obj["rism_id"]

        return get_identifier(req, "sources.inventory_items", source_id=source_id)

    def get_section_label(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return transl["records.inventory"]

    async def get_items(self, obj: SolrResult) -> list | None:
        if not self.context.get("direct_request", False):
            return None

        req = self.context["request"]

        source_id: str | None = req.match_info.get("source_id", None)
        if not source_id:
            return None

        fq = ["type:inventory_item", f"source_id:source_{source_id}"]
        sort = "source_order_i asc"

        results: Results = await SolrConnection.search(
            {"query": "*:*", "filter": fq, "sort": sort}, cursor=True
        )
        if results.hits == 0:
            return None

        return await InventoryItem(
            results, many=True, context={"request": self.context["request"]}
        ).serialized_many


class InventoryItem(ypres.AsyncDictSerializer):
    iid = ypres.MethodField(label="id")
    label = ypres.MethodField()
    creator = ypres.MethodField()
    relationships = ypres.MethodField()
    subjects = ypres.MethodField()

    def get_iid(self, obj: SolrResult) -> str:
        req = self.context["request"]
        source_id = strip_prefix(obj["source_id"])
        inventory_item_id = strip_prefix(obj["id"])

        return get_identifier(
            req,
            "sources.inventory_item",
            source_id=source_id,
            inventory_item_id=inventory_item_id,
        )

    def get_label(self, obj: SolrResult) -> dict:
        return {"none": ["This is a title to be replaced."]}

    def get_creator(self, obj: SolrResult) -> dict | None:
        if "creator_json" not in obj:
            return None

        return Relationship(
            obj["creator_json"][0], context={"request": self.context["request"]}
        ).serialized

    def get_relationships(self, obj: SolrResult) -> dict | None:
        if not self.context.get("direct_request", False):
            return None

        # sets are cool; two sets are disjoint if they have no keys in common. We
        # can use this to check whether these keys are in the solr result; if not,
        # we have no relationships to render, so we can return.
        if {
            "related_people_json",
            "related_institutions_json",
        }.isdisjoint(obj.keys()):
            return None

        req = self.context["request"]
        return RelationshipsSection(obj, context={"request": req}).serialized

    def get_subjects(self, obj: SolrResult) -> dict | None:
        if "subjects_json" not in obj:
            return None

        return SubjectsSection(
            obj,
            context={
                "request": self.context["request"],
            },
        ).serialized
