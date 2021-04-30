import logging
import re
from typing import Dict, Optional, List, Union

import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import get_identifier, ID_SUB
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult

log = logging.getLogger()


class PersonRelationshipList(JSONLDContextDictSerializer):
    rtype = StaticField(
        label="type",
        value="rism:PersonRelationshipList"
    )
    label = serpy.MethodField()
    # items = serpy.MethodField()

    def get_label(self, obj: Union[Dict, SolrResult]) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        return transl.get("records.related_personal_name")

    # def get_items(self, obj: Union[Dict, SolrResult]) -> Optional[List[Dict]]:
    #     itemlist = obj.get("related_people_json")
    #
    #     return PersonRelationship(itemlist, many=True,
    #                               context={"request": self.context.get("request")}).data


# class PersonRelationship(JSONLDContextDictSerializer):
#     ptype = StaticField(
#         label="type",
#         value="rism:PersonRelationship"
#     )
#     role = serpy.MethodField()
#     qualifier = serpy.MethodField()
#     related_to = serpy.MethodField(
#         label="relatedTo"
#     )
#
#     def get_role(self, obj: Dict) -> Optional[Dict]:
#         if 'relationship' not in obj:
#             return None
#
#         req = self.context.get("request")
#         transl: Dict = req.app.ctx.translations
#
#         translation_key: str = _PERSON_RELATIONSHIP_LABELS_MAP.get(obj['relationship'])
#
#         return {"label": transl.get(translation_key)}
#
#     def get_qualifier(self, obj: Dict) -> Optional[Dict]:
#         if 'qualifier' not in obj:
#             return None
#
#         qualifier: str = obj['qualifier']
#
#         req = self.context.get("request")
#         transl: Dict = req.app.ctx.translations
#
#         translation_key: str = QUALIFIER_LABELS.get(qualifier)
#
#         return {"label": transl.get(translation_key)}
#
#     def get_related_to(self, obj: Dict) -> Dict:
#         if 'date_statement' in obj:
#             name = f"{obj.get('name')} ({obj.get('date_statement')})"
#         else:
#             name = f"{obj.get('name')}"
#
#         req = self.context.get("request")
#         person_id = re.sub(ID_SUB, "", obj.get('other_person_id'))
#
#         return {
#             "id": get_identifier(req, "people.person", person_id=person_id),
#             "label": {"none": [name]},
#             "type": "rism:Person"
#         }
