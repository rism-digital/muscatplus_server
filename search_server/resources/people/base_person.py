import re
from typing import Optional

import serpy

from shared_helpers.formatters import format_person_label
from shared_helpers.identifiers import ID_SUB, get_identifier
from shared_helpers.serializers import JSONLDAsyncDictSerializer
from shared_helpers.solr_connection import SolrResult
from search_server.resources.shared.record_history import get_record_history


SOLR_FIELDS_FOR_BASE_PERSON: list = [
    "id", "type", "created", "updated", "name_s", "name_ans", "date_statement_s"
]


class BasePerson(JSONLDAsyncDictSerializer):
    pid = serpy.MethodField(
        label="id"
    )
    stype = serpy.StaticField(
        label="type",
        value="rism:Person"
    )
    type_label = serpy.MethodField(
        label="typeLabel"
    )
    label = serpy.MethodField()
    record_history = serpy.MethodField(
        label="recordHistory"
    )

    def get_pid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        person_id: str = re.sub(ID_SUB, "", obj['id'])

        return get_identifier(req, "people.person", person_id=person_id)

    def get_label(self, obj: SolrResult) -> dict:
        label: str = format_person_label(obj)

        return {"none": [label]}

    def get_type_label(self, obj: SolrResult) -> Optional[dict]:
        req = self.context.get("request")
        transl = req.app.ctx.translations
        return transl.get("records.person")

    def get_record_history(self, obj: dict) -> Optional[dict]:
        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        return get_record_history(obj, transl)
