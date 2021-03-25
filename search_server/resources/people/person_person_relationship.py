import logging
import re
from typing import Dict, Optional, List

import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import get_identifier, ID_SUB, PERSON_RELATIONSHIP_LABELS
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult

log = logging.getLogger()


class PersonRelationshipList(JSONLDContextDictSerializer):
    pid = serpy.MethodField(
        label="id"
    )
    rtype = StaticField(
        label="type",
        value="rism:PersonPersonRelationshipList"
    )
    label = serpy.MethodField()
    items = serpy.MethodField()

    def get_pid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        person_id: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "person_relationships_list", person_id=person_id)

    def get_label(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.translations

        return transl.get("records.related_personal_name")

    def get_items(self, obj: SolrResult) -> Optional[List[Dict]]:
        return PersonPersonRelationship(obj["related_people_json"], many=True,
                                        context={"request": self.context.get("request")}).data


class PersonPersonRelationship(JSONLDContextDictSerializer):
    prid = serpy.MethodField(
        label="id"
    )

    ptype = StaticField(
        label="type",
        value="rism:PersonPersonRelationship"
    )
    role = serpy.MethodField()
    related_to = serpy.MethodField(
        label="relatedTo"
    )

    def get_prid(self, obj: Dict) -> str:
        person_id = re.sub(ID_SUB, "", obj.get('this_person_id'))
        relationship_id = obj.get("id")
        req = self.context.get("request")

        return get_identifier(req, "person_person_relationship",
                              person_id=person_id, related_id=f"{relationship_id}")

    def get_role(self, obj: Dict) -> Optional[Dict]:
        if 'relationship' not in obj:
            return None

        req = self.context.get("request")
        transl: Dict = req.app.translations

        translation_key: str = PERSON_RELATIONSHIP_LABELS.get(obj['relationship'])

        return transl.get(translation_key)

    def get_related_to(self, obj: Dict) -> Dict:
        req = self.context.get("request")
        person_id = re.sub(ID_SUB, "", obj.get('other_person_id'))

        return {
            "id": get_identifier(req, "person", person_id=person_id),
            "name": {"none": [obj.get("name")]},
            "type": "rism:Person"
        }
