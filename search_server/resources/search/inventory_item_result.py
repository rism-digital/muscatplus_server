import ypres

from search_server.helpers.display_fields import get_search_result_summary
from search_server.helpers.display_translators import title_json_value_translator
from search_server.helpers.identifiers import get_identifier, strip_prefix
from search_server.helpers.solr_connection import SolrResult


class InventoryItemSearchResult(ypres.DictSerializer):
    srid = ypres.MethodField(label="id")
    slabel = ypres.MethodField(label="label")
    result_type = ypres.StaticField(label="type", value="rism:InventoryItem")
    type_label = ypres.MethodField(label="typeLabel")
    summary = ypres.MethodField()
    flags = ypres.MethodField()

    def get_srid(self, obj: SolrResult) -> str:
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

        label: dict | None = title_json_value_translator(
            obj.get("standard_titles_json", []), transl
        )
        return label or {"none": ["[No title]"]}

    def get_type_label(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl = req.ctx.translations

        return transl.get("records.inventory_item")

    def get_summary(self, obj: SolrResult) -> dict | None:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        field_config: dict = {
            "inventory_source_s": (
                "inventorySource",
                "records.inventory_source",
                None,
            ),
            "inventory_number_s": (
                "inventoryNumber",
                "records.inventory_number",
                None,
            ),
            "creator_name_s": ("inventoryComposer", "records.composer_author", None),
        }

        return get_search_result_summary(field_config, transl, obj)

    def get_flags(self, obj: SolrResult) -> dict | None:
        flags: dict[str, str] = {}
        if inventory_section := obj.get("inventory_section_s"):
            flags["inventorySection"] = inventory_section

        return flags or None
