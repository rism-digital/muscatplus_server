import re
from typing import Dict, Optional, List

import pysolr
import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import ID_SUB, get_identifier, RISM_JSONLD_CONTEXT, get_jsonld_context, \
    JSONLDContext
from search_server.helpers.serializers import ContextDictSerializer
from search_server.helpers.solr_connection import SolrConnection, SolrResult, SolrManager


def handle_incipits_list_request(req, source_id: str) -> Optional[Dict]:
    pass


def handle_incipit_request(req, source_id: str, work_num: str) -> Optional[Dict]:
    fq: List = ["type:source_incipit",
                f"source_id:source_{source_id}",
                f"work_num_s:{work_num}"]

    record: pysolr.Results = SolrConnection.search("*:*", fq=fq, rows=1)

    if record.hits == 0:
        return None

    incipit_record = record.docs[0]
    incipit = SourceIncipit(incipit_record, context={"request": req,
                                                     "direct_request": True})

    return incipit.data


class SourceIncipitList(ContextDictSerializer):
    ctx = serpy.MethodField(
        label="@context"
    )
    lid = serpy.MethodField(
        label="id"
    )
    ltype = StaticField(
        label="type",
        value="rism:IncipitList"
    )
    label = serpy.MethodField()
    items = serpy.MethodField()

    def get_ctx(self, obj: SolrResult) -> Optional[JSONLDContext]:
        direct_request: bool = self.context.get("direct_request")
        return get_jsonld_context(self.context.get("request")) if direct_request else None

    def get_lid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))

        return get_identifier(req, "incipits_list", source_id=source_id)

    def get_label(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.translations

        return transl.get("records.incipits")

    def get_items(self, obj: SolrResult) -> Optional[List]:
        conn = SolrManager(SolrConnection)
        fq: List = [f"source_id:{obj.get('id')}",
                    "type:source_incipit"]
        sort: str = "work_num_s asc"

        conn.search("*:*", fq=fq, sort=sort)

        if conn.hits == 0:
            return None

        return SourceIncipit(conn.results,
                             many=True,
                             context={"request": self.context.get("request")}).data


class SourceIncipit(ContextDictSerializer):
    ctx = serpy.MethodField(
        label="@context"
    )
    incip_id = serpy.MethodField(
        label="id"
    )
    itype = StaticField(
        label="type",
        value="rism:Incipit"
    )
    title = serpy.StrField(
        attr="title_s",
        required=False
    )
    music_incipit = serpy.StrField(
        label="musicIncipit",
        attr="music_incipit_s",
        required=False
    )
    text_incipit = serpy.StrField(
        label="textIncipit",
        attr="text_incipit_s",
        required=False
    )
    work_number = serpy.StrField(
        label="workNumber",
        attr="work_num_s",
        required=False
    )

    def get_ctx(self, obj: Dict) -> Optional[Dict]:
        direct_request: bool = self.context.get("direct_request")
        return get_jsonld_context(self.context.get("request")) if direct_request else None

    def get_incip_id(self, obj: Dict) -> str:
        req = self.context.get("request")

        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))
        incipit_id: str = f"{obj.get('work_num_s')}"

        return get_identifier(req, "incipit", source_id=source_id, incipit_id=incipit_id)
