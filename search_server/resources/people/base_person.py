import re

import ypres

from search_server.helpers.formatters import format_person_label
from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.solr_connection import SolrResult
from search_server.resources.shared.record_history import get_record_history


class BasePerson(ypres.AsyncDictSerializer):
    pid = ypres.MethodField(label="id")
    stype = ypres.StaticField(label="type", value="rism:Person")
    type_label = ypres.MethodField(label="typeLabel")
    slabel = ypres.MethodField(label="label")
    record_history = ypres.MethodField(label="recordHistory")

    def get_pid(self, obj: SolrResult) -> str:
        req = self.context["request"]
        person_id: str = re.sub(ID_SUB, "", obj["id"])

        return get_identifier(req, "people.person", person_id=person_id)

    def get_slabel(self, obj: SolrResult) -> dict:
        label: str = format_person_label(obj)

        return {"none": [label]}

    def get_type_label(self, obj: SolrResult) -> dict | None:
        req = self.context["request"]
        transl: dict = req.ctx.translations
        return transl.get("records.person")

    def get_record_history(self, obj: dict) -> dict | None:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return get_record_history(obj, transl)
