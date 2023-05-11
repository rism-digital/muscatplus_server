import ypres

from shared_helpers.display_translators import person_name_variant_labels_translator
from shared_helpers.solr_connection import SolrResult


class VariantNamesSection(ypres.DictSerializer):
    ntype = ypres.StaticField(
        label="type",
        value="rism:VariantNamesSection"
    )
    label = ypres.MethodField()
    items = ypres.MethodField()

    def get_label(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        return transl.get("records.name_variants")

    def get_items(self, obj: SolrResult) -> list[dict]:
        return NameVariant(obj['variant_names_json'],
                           many=True,
                           context={"request": self.context.get("request")}).data


class NameVariant(ypres.DictSerializer):
    vtype = ypres.StaticField(
        label="type",
        value="rism:VariantName"
    )
    label = ypres.MethodField()
    value = ypres.MethodField()

    def get_label(self, obj: dict) -> dict:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        return person_name_variant_labels_translator(obj['type'], transl)

    def get_value(self, obj: dict) -> dict:
        return {"none": obj['variants']}
