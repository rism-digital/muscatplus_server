import re
from typing import Dict, Optional, List

import serpy

from search_server.helpers.identifiers import get_identifier, ID_SUB
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.resources.people.base_person import BasePerson


def handle_creator_request(req, source_id: str) -> Optional[Dict]:
    pass


class SourceCreator(JSONLDContextDictSerializer):
    # cid = serpy.MethodField(
    #     label="id"
    # )
    heading = serpy.MethodField()
    qualifier = serpy.MethodField()
    related_to = serpy.MethodField(
        label="relatedTo"
    )

    def get_cid(self, obj: Dict) -> str:
        req = self.context.get("request")
        source_id: str = re.sub(ID_SUB, "", obj.get("person_id"))

        return get_identifier(req, "sources.creator", source_id=source_id)

    def get_heading(self, obj: Dict) -> List:
        req = self.context.get("request")
        transl: Dict = req.app.translations

        return [{
            "label": transl.get("records.composer_author")
        }]

    def get_qualifier(self, obj: Dict) -> Optional[str]:
        return f"rism:{q}" if (q := obj.get('qualifier_s')) else None

    def get_related_to(self, obj: Dict) -> Dict:
        return BasePerson(obj, context={"request": self.context.get("request")}).data
