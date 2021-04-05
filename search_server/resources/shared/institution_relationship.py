import re
from typing import Dict, List, Optional, Union

import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult


class InstitutionRelationshipList(JSONLDContextDictSerializer):
    # rid = serpy.MethodField(
    #     label="id"
    # )
    rtype = StaticField(
        label="type",
        value="rism:InstitutionRelationshipList"
    )
    label = serpy.MethodField()
    items = serpy.MethodField()

    def get_rid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        obj_type: str = obj.get("type")
        obj_fieldname: str = f"{obj_type}_id"

        # TODO: Finish me!
        return get_identifier(req, "", "")

    def get_label(self, obj: Union[Dict, SolrResult]) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.translations

        return transl.get("records.associated_institution")

    def get_items(self, obj: Union[Dict, SolrResult]) -> Optional[List]:
        if "institutions" in obj:
            itemlist = obj["institutions"]
        else:
            itemlist = obj["related_institutions_json"]
        return InstitutionRelationship(itemlist, many=True,
                                       context={"request": self.context.get("request")}).data


class InstitutionRelationship(JSONLDContextDictSerializer):
    rtype = StaticField(
        label="type",
        value="rism:InstitutionRelationship"
    )
    related_to = serpy.MethodField(
        label="relatedTo"
    )

    def get_related_to(self, obj: Dict) -> Dict:
        req = self.context.get("request")
        institution_id = re.sub(ID_SUB, "", obj.get("institution_id"))

        return {
            "id": get_identifier(req, "institutions.institution", institution_id=institution_id),
            "label": {"none": [obj.get("name")]},
            "type": "rism:Institution"
        }
