import logging
import re
from typing import Dict, Optional, List

import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult

log = logging.getLogger()


class PlaceRelationshipList(JSONLDContextDictSerializer):
    rtype = StaticField(
        label="type",
        value="rism:PlaceRelationshipList"
    )
    label = serpy.MethodField()
    # items = serpy.MethodField()

    def get_label(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        return transl.get("records.related_place")

    # def get_items(self, obj: SolrResult) -> Optional[List[Dict]]:
    #     return PlaceRelationship(obj["related_places_json"], many=True,
    #                              context={"request": self.context.get("request")}).data


# class PlaceRelationship(JSONLDContextDictSerializer):
#     ptype = StaticField(
#         label="type",
#         value="rism:PlaceRelationship"
#     )
#     role = serpy.MethodField()
#     related_to = serpy.MethodField(
#         label="relatedTo"
#     )
#     value = serpy.MethodField()
#
#     def get_role(self, obj: Dict) -> Optional[Dict]:
#         if 'relationship' not in obj:
#             return None
#
#         req = self.context.get("request")
#         transl: Dict = req.app.ctx.translations
#
#         translation_key: str = PERSON_PLACE_RELATIONSHIP_LABELS.get(obj['relationship'])
#
#         return {"label": transl.get(translation_key)}
#
#     # TODO: Fill this in with the appropriate linking values when the places are attached to the authorities.
#     def get_related_to(self, obj: Dict) -> Optional[Dict]:
#         # For values that are not linked to authority records we don't have the ID -- so we can't construct a relatedTo
#         # object.
#         if 'place_id' not in obj:
#             return None
#
#         req = self.context.get("request")
#         place_id = re.sub(ID_SUB, "", obj.get("place_id"))
#
#         return {
#             "id": get_identifier(req, "places.place", place_id=place_id),
#             "label": {"none": [obj.get("name")]},
#             "type": "rism:Place"
#         }
#
#     def get_value(self, obj: Dict) -> Optional[Dict]:
#         """
#         Used for occasions where the entry is not linked to an item in the Place authority record, but is
#         simply given as a name. In other words, if there is a place ID mentioned, skip this.
#         """
#         if "place_id" in obj:
#             return None
#
#         return {"none": [obj.get("name")]}
