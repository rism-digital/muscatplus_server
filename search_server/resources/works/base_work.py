import re
from typing import Optional

import serpy

from search_server.resources.shared.relationship import Relationship
from shared_helpers.formatters import format_work_label
from shared_helpers.identifiers import ID_SUB, get_identifier
from shared_helpers.solr_connection import SolrResult


class BaseWork(serpy.AsyncDictSerializer):
    wid = serpy.MethodField(
        label="id"
    )
    wtype = serpy.StaticField(
        label="type",
        value="rism:Work"
    )
    label = serpy.MethodField()
    creator = serpy.MethodField()
    sources = serpy.MethodField()

    def get_wid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        work_id: str = re.sub(ID_SUB, "", obj['id'])

        return get_identifier(req, "works.work", work_id=work_id)

    def get_label(self, obj: SolrResult) -> dict:
        return {"none": [format_work_label(obj)]}

    def get_creator(self, obj: SolrResult) -> Optional[dict]:
        if 'creator_json' not in obj:
            return None

        return Relationship(obj["creator_json"][0],
                            context={"request": self.context.get('request'),
                                     "reltype": "rism:Creator"}).data

    def get_sources(self, obj: SolrResult) -> Optional[dict]:
        req = self.context.get("request")
        work_id: str = obj.get("id")
        source_count: int = obj.get("source_count_i", 0)

        ident: str = re.sub(ID_SUB, "", work_id)

        return {
            "url": get_identifier(req, "works.work_sources", work_id=ident),
            "totalItems": source_count
        }
