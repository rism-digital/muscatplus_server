from typing import Dict, List

import serpy

# from search_server.helpers.identifiers import PERSON_NAME_VARIANT_TYPES
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult


class NameVariantList(JSONLDContextDictSerializer):
    label = serpy.MethodField()
    # items = serpy.MethodField()

    def get_label(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        return transl.get("records.name_variants")

    # def get_items(self, obj: SolrResult) -> List[Dict]:
    #     return NameVariant(obj['name_variants_json'],
    #                        many=True,
    #                        context={"request": self.context.get("request")}).data


# class NameVariant(JSONLDContextDictSerializer):
#     label = serpy.MethodField()
#     value = serpy.MethodField()
#
#     def get_label(self, obj: Dict) -> Dict:
#         req = self.context.get("request")
#         transl: Dict = req.app.ctx.translations
#         transl_key = PERSON_NAME_VARIANT_TYPES.get(obj["type"])
#
#         return transl.get(transl_key)
#
#     def get_value(self, obj: Dict) -> Dict:
#         return {"none": obj['variants']}
