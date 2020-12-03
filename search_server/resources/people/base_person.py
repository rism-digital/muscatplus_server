import re
from typing import Optional, Dict, List, Union

import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import get_jsonld_context, ID_SUB, get_identifier, JSONLDContext
from search_server.helpers.serializers import ContextDictSerializer
from search_server.helpers.solr_connection import SolrResult


class BasePerson(ContextDictSerializer):
    ctx = serpy.MethodField(
        label="@context"
    )
    pid = serpy.MethodField(
        label="id"
    )
    stype = StaticField(
        label="type",
        value="rism:Person"
    )
    label = serpy.MethodField()

    def get_ctx(self, obj: SolrResult) -> Optional[JSONLDContext]:
        direct_request: bool = self.context.get("direct_request")
        return get_jsonld_context(self.context.get("request")) if direct_request else None

    def get_pid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        person_id: str = re.sub(ID_SUB, "", obj.get('person_id'))

        return get_identifier(req, "person", person_id=person_id)

    def get_label(self, obj: SolrResult) -> Dict:
        name: str = obj.get("name_s")
        dates: Optional[str] = f" ({d})" if (d := obj.get("date_statement_s")) else ""

        return {"none": [f"{name}{dates}"]}

