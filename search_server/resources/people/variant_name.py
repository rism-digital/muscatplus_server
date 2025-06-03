import ypres

from shared_helpers.display_translators import person_name_variant_labels_translator
from shared_helpers.solr_connection import SolrResult


class VariantNamesSection(ypres.DictSerializer):
    ntype = ypres.StaticField(label="type", value="rism:VariantNamesSection")
    slabel = ypres.MethodField(label="label")
    items = ypres.MethodField()

    def get_slabel(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return transl["records.name_variants"]

    def get_items(self, obj: SolrResult) -> list[dict]:
        return NameVariant(
            obj["variant_names_json"],
            many=True,
            context={"request": self.context["request"]},
        ).serialized_many


class NameVariant(ypres.DictSerializer):
    vtype = ypres.StaticField(label="type", value="rism:VariantName")
    slabel = ypres.MethodField(label="label")
    value = ypres.MethodField()

    def get_slabel(self, obj: dict) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return person_name_variant_labels_translator(obj["type"], transl)

    def get_value(self, obj: dict) -> dict:
        return {"none": obj["variants"]}
