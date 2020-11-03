import re
from typing import Dict, List, Optional

import pysolr
import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.serializers import ContextDictSerializer
from search_server.helpers.solr_connection import SolrConnection, SolrManager


def handle_materialgroup_list_request(req, source_id: str) -> Optional[Dict]:
    fq: List = ["type:source_materialgroup",
                f"source_id:source_{source_id}"]

    records: pysolr.Results = SolrConnection.search("*:*", fq=fq)

    if records.hits == 0:
        pass


def handle_materialgroup_request(req, source_id: str, materialgroup_id: str) -> Optional[Dict]:
    pass


class SourceMaterialGroupList(ContextDictSerializer):
    mid = serpy.MethodField(
        label="id"
    )
    mtype = StaticField(
        label="type",
        value="rism:MaterialGroupList"
    )
    label = serpy.MethodField()
    items = serpy.MethodField()

    def get_mid(self, obj: Dict) -> str:
        req = self.context.get("request")
        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))

        return get_identifier(req, "materialgroup_list", source_id=source_id)

    def get_label(self, obj: Dict) -> Dict:
        pass

    def get_items(self, obj: Dict) -> Optional[List]:
        conn = SolrManager(SolrConnection)
        fq: List = ["type:source_materialgroup",
                    f"source_id:{obj.get('source_id')}"]
        sort: str = "group_num_s asc"

        conn.search("*:*", fq=fq, sort=sort)

        if conn.hits == 0:
            return None

        items = SourceMaterialGroup(conn.results, many=True,
                                    context={"request": self.context.get('request')})

        return items.data


class SourceMaterialGroup(ContextDictSerializer):
    ctx = serpy.MethodField(
        label="@context"
    )
    mid = serpy.MethodField(
        label="id"
    )
    mtype = StaticField(
        label="type",
        value="rism:MaterialGroup"
    )
    display_fields = serpy.MethodField(
        label="displayFields"
    )

    def get_ctx(self, obj: Dict) -> Dict:
        pass

    def get_mid(self, obj: Dict) -> str:
        req = self.context.get("request")

        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))
        materialgroup_id: str = f"{obj.get('group_num_s')}"

        return get_identifier(req, "materialgroup", source_id=source_id, materialgroup_id=materialgroup_id)

    def get_display_fields(self, obj: Dict) -> List:
        pass
