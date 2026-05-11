import ypres
from small_asc.client import Results

from search_server.helpers.display_translators import title_json_value_translator
from search_server.helpers.identifiers import get_identifier, strip_prefix
from search_server.helpers.solr_connection import SolrConnection, SolrResult
from search_server.resources.shared.contents import ContentsSection
from search_server.resources.shared.external_resources import ExternalResourcesSection
from search_server.resources.shared.record_history import get_record_history
from search_server.resources.shared.references_notes import ReferencesNotesSection
from search_server.resources.shared.relationship import (
    Relationship,
    RelationshipsSection,
)


class InventoryItemSection(ypres.AsyncDictSerializer):
    sid = ypres.MethodField(label="id")
    stype = ypres.StaticField(value="rism:InventoryItemSection", label="type")
    section_label = ypres.MethodField(label="sectionLabel")
    items = ypres.MethodField()
    total_items = ypres.IntField(attr="num_inventory_items_i", label="totalItems")

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
    slabel = ypres.MethodField(label="label")
    stype = ypres.StaticField(value="rism:InventoryItem", label="type")
    creator = ypres.MethodField()
    contents = ypres.MethodField()
    references_notes = ypres.MethodField(label="referencesNotes")
    relationships = ypres.MethodField()
    inventory = ypres.MethodField()
    external_resources = ypres.MethodField(label="externalResources")
    record_history = ypres.MethodField(label="recordHistory")

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

    def get_slabel(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        t: dict | None = title_json_value_translator(
            obj.get("standard_titles_json", []), transl
        )
        return t or {"none": ["[No title]"]}

    def get_creator(self, obj: SolrResult) -> dict | None:
        if "creator_json" not in obj:
            return None

        return Relationship(
            obj["creator_json"][0], context={"request": self.context["request"]}
        ).serialized

    def get_contents(self, obj: SolrResult) -> dict | None:
        if not self.context.get("direct_request", False):
            return None

        req = self.context["request"]
        return ContentsSection(obj, context={"request": req}).serialized

    def get_references_notes(self, obj: SolrResult) -> dict | None:
        req = self.context["request"]
        refnotes: dict = ReferencesNotesSection(
            obj, context={"request": req}
        ).serialized

        # if the only two keys in the references and notes section is 'label' and 'type'
        # then there is no content and we can hide this section.
        if {"notes", "performanceLocations", "liturgicalFestivals"}.isdisjoint(
            refnotes.keys()
        ):
            return None

        return refnotes

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

    def get_inventory(self, obj: SolrResult) -> dict | None:
        if {
            "inventory_source_s",
            "inventory_section_s",
            "inventory_number_s",
        }.isdisjoint(obj.keys()):
            return None

        d = {
            "inventorySource": obj.get("inventory_source_s"),
            "inventorySection": obj.get("inventory_section_s"),
            "inventoryNumber": obj.get("inventory_number_s"),
        }

        return {k: v for k, v in d.items() if v}

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

    def get_record_history(self, obj: SolrResult) -> dict | None:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return get_record_history(obj, transl)
