from typing import Dict, List

import serpy

from search_server.helpers.display_translators import person_name_variant_labels_translator
from search_server.helpers.fields import StaticField
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult


class NameVariantSection(JSONLDContextDictSerializer):
    ntype = StaticField(
        label="type",
        value="rism:NameVariantsSection"
    )
    label = serpy.MethodField()
    items = serpy.MethodField()

    def get_label(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        return transl.get("records.name_variants")

    def get_items(self, obj: SolrResult) -> List[Dict]:
        return NameVariant(obj['name_variants_json'],
                           many=True,
                           context={"request": self.context.get("request")}).data


class NameVariant(JSONLDContextDictSerializer):
    vtype = StaticField(
        label="type",
        value="rism:NameVariant"
    )
    label = serpy.MethodField()
    value = serpy.MethodField()

    def get_label(self, obj: Dict) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations
        return person_name_variant_labels_translator(obj['type'], transl)

    def get_value(self, obj: Dict) -> Dict:
        return {"none": obj['variants']}
