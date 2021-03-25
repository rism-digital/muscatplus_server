import re
from typing import Dict, List, Optional

import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult


class PersonInstitutionRelationshipList(JSONLDContextDictSerializer):
    pid = serpy.MethodField(
        label="id"
    )
    rtype = StaticField(
        label="type",
        value="rism:PersonInstitutionRelationshipList"
    )
    label = serpy.MethodField()
    items = serpy.MethodField()

    def get_pid(self, obj: SolrResult) -> str:
        pass

    def get_label(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.translations

        return transl.get("records.associated_institution")

    def get_items(self, obj: SolrResult) -> Optional[List]:
        return PersonInstitutionRelationship(obj["related_institutions_json"], many=True,
                                             context={"request": self.context.get("request")}).data


class PersonInstitutionRelationship(JSONLDContextDictSerializer):
    pid = serpy.MethodField(
        label="id"
    )
    rtype = StaticField(
        label="type",
        value="rism:PersonInstitutionRelationship"
    )
    related_to = serpy.MethodField(
        label="relatedTo"
    )

    def get_pid(self, obj: Dict) -> str:
        pass

    def get_related_to(self, obj: Dict) -> Dict:
        req = self.context.get("request")
        institution_id = re.sub(ID_SUB, "", obj.get("institution_id"))

        return {
            "id": get_identifier(req, "institution", institution_id=institution_id),
            "name": {"none": [obj.get("name")]},
            "type": "rism:Institution"
        }
