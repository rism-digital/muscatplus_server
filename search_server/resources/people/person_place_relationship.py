import logging
import re
from typing import Dict, Optional, List

import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import ID_SUB, get_identifier, PERSON_PLACE_RELATIONSHIP_LABELS
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult

log = logging.getLogger()


class PersonPlaceRelationshipList(JSONLDContextDictSerializer):
    pid = serpy.MethodField(
        label="id"
    )
    rtype = StaticField(
        label="type",
        value="rism:PersonPlaceRelationshipList"
    )
    label = serpy.MethodField()
    items = serpy.MethodField()

    def get_pid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        person_id: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "person_place_relationships_list", person_id=person_id)

    def get_label(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.translations

        return transl.get("records.related_place")

    def get_items(self, obj: SolrResult) -> Optional[List[Dict]]:
        if 'related_places_json' not in obj:
            return None

        return PersonPlaceRelationship(obj["related_places_json"], many=True,
                                       context={"request": self.context.get("request")}).data


class PersonPlaceRelationship(JSONLDContextDictSerializer):
    pid = serpy.MethodField(
        label="id"
    )
    ptype = StaticField(
        label="type",
        value="rism:PersonPlaceRelationship"
    )
    role = serpy.MethodField()
    related_to = serpy.MethodField()

    def get_pid(self, obj: Dict) -> str:
        req = self.context.get("request")
        person_id: str = re.sub(ID_SUB, "", obj.get("this_person_id"))
        # TODO: When places are linked to the authority file records, put the place ID in the index
        #  and then add it to the identifier
        relationship_id: str = obj.get("id")

        return get_identifier(req, "person_place_relationship", person_id=person_id, related_id=relationship_id)

    def get_role(self, obj: Dict) -> Optional[Dict]:
        if 'relationship' not in obj:
            return None

        req = self.context.get("request")
        transl: Dict = req.app.translations

        translation_key: str = PERSON_PLACE_RELATIONSHIP_LABELS.get(obj['relationship'])

        return transl.get(translation_key)

    def get_related_to(self, obj: Dict) -> Dict:
        pass