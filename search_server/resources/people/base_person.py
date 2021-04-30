import re
from typing import Optional, Dict

import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult


class BasePerson(JSONLDContextDictSerializer):
    pid = serpy.MethodField(
        label="id"
    )
    stype = StaticField(
        label="type",
        value="rism:Person"
    )
    type_label = serpy.MethodField(
        label="typeLabel"
    )
    label = serpy.MethodField()

    def get_pid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        person_id: str = re.sub(ID_SUB, "", obj.get('person_id'))

        return get_identifier(req, "people.person", person_id=person_id)

    def get_label(self, obj: SolrResult) -> Dict:
        name: str = obj.get("name_s")
        dates: Optional[str] = f" ({d})" if (d := obj.get("date_statement_s")) else ""

        return {"none": [f"{name}{dates}"]}

    def get_type_label(self, obj: SolrResult) -> Optional[Dict]:
        req = self.context.get("request")
        transl = req.app.ctx.translations
        return transl.get("records.person")
