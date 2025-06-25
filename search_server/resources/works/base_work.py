import re

import ypres

from search_server.resources.shared.relationship import Relationship
from shared_helpers.formatters import format_work_label
from shared_helpers.identifiers import ID_SUB, get_identifier
from shared_helpers.solr_connection import SolrResult


class BaseWork(ypres.AsyncDictSerializer):
    wid = ypres.MethodField(label="id")
    wtype = ypres.StaticField(label="type", value="rism:Work")
    slabel = ypres.MethodField(label="label")
    creator = ypres.MethodField()

    def get_wid(self, obj: SolrResult) -> str:
        req = self.context["request"]
        work_id: str = re.sub(ID_SUB, "", obj["id"])

        return get_identifier(req, "works.work", work_id=work_id)

    def get_slabel(self, obj: SolrResult) -> dict:
        return {"none": [format_work_label(obj)]}

    def get_creator(self, obj: SolrResult) -> dict | None:
        if "creator_json" not in obj:
            return None

        return Relationship(
            obj["creator_json"][0],
            context={"request": self.context["request"]},
        ).serialized
