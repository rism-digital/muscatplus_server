import re
from typing import Dict

import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import get_identifier, ID_SUB
from search_server.helpers.serializers import ContextDictSerializer
from search_server.helpers.solr_connection import SolrResult


class PersonPersonRelationship(ContextDictSerializer):
    prid = serpy.MethodField(
        label="id"
    )

    ptype = StaticField(
        label="type",
        value="rism:PersonPersonRelationship"
    )
    role = serpy.StrField(
        attr="relationship_s",
        required=False
    )
    related_to = serpy.MethodField(
        label="relatedTo"
    )

    def get_prid(self, obj: SolrResult) -> str:
        person_id = re.sub(ID_SUB, "", obj.get('person_id'))
        related_id = re.sub(ID_SUB, "", obj.get("related_id"))
        req = self.context.get("request")

        return get_identifier(req, "person_person_relationship", person_id=person_id, related_id=related_id)

    def get_related_to(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        person_id = re.sub(ID_SUB, "", obj.get('person_id'))

        return {
            "id": get_identifier(req, "person", person_id=person_id),
            "name": {"none": [obj.get("name_s")]},
            "type": "rism:Person"
        }
