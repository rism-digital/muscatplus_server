import re
from typing import Dict, Optional

import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.serializers import ContextDictSerializer


class SourceSubject(ContextDictSerializer):
    sid = serpy.MethodField(
        label="id"
    )
    stype = StaticField(
        label="type",
        value="rism:Subject"
    )
    term = serpy.MethodField()

    def get_sid(self, obj: Dict) -> str:
        req = self.context.get("request")
        subject_id: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "subjects.subject", subject_id=subject_id)

    def get_term(self, obj: Dict) -> Dict:
        term: Optional[str] = obj.get("subject")

        return {"none": [term]}
