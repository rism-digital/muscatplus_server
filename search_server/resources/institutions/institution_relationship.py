import logging
import re
from typing import Dict, Optional

import serpy

from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.serializers import ContextDictSerializer

log = logging.getLogger()


class InstitutionRelationship(ContextDictSerializer):
    srid = serpy.MethodField(
        label="id"
    )
    role = serpy.MethodField()
    qualifier = serpy.MethodField()
    related_to = serpy.MethodField(
        label="relatedTo"
    )

    def get_srid(self, obj: Dict) -> str:
        req = self.context.get("request")

        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))
        relationship_id: str = f"{obj.get('relationship_id')}"

        return get_identifier(req, "relationship", source_id=source_id, relationship_id=relationship_id)

    def get_role(self, obj: Dict) -> Optional[str]:
        if t := obj.get("relationship_s"):
            return f"relators:{t}"

        return None

    def get_qualifier(self, obj: Dict) -> str:
        return f"rism:{q}" if (q := obj.get('qualifier_s')) else None

    def get_related_to(self, obj: Dict) -> Optional[Dict]:
        req = self.context.get("request")
        source_id: str = re.sub(ID_SUB, "", obj.get('source_id'))

        return {
            "id": get_identifier(req, "source", source_id=source_id),
            "type": "rism:Source",
            "label": {"none": [obj.get("title_s")]}
        }
