import serpy

from search_server.helpers.display_translators import person_name_variant_labels_translator
from search_server.helpers.fields import StaticField
from search_server.helpers.serializers import JSONLDContextDictSerializer
from shared_helpers.solr_connection import SolrResult


class VariantNamesSection(JSONLDContextDictSerializer):
    ntype = StaticField(
        label="type",
        value="rism:VariantNamesSection"
    )
    label = serpy.MethodField()
    items = serpy.MethodField()

    def get_label(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        return transl.get("records.name_variants")

    def get_items(self, obj: SolrResult) -> list[dict]:
        return NameVariant(obj['variant_names_json'],
                           many=True,
                           context={"request": self.context.get("request")}).data


class NameVariant(JSONLDContextDictSerializer):
    vtype = StaticField(
        label="type",
        value="rism:VariantName"
    )
    label = serpy.MethodField()
    value = serpy.MethodField()

    def get_label(self, obj: dict) -> dict:
        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        return person_name_variant_labels_translator(obj['type'], transl)

    def get_value(self, obj: dict) -> dict:
        return {"none": obj['variants']}
