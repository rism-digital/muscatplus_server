import re
from typing import Dict, Optional, List

import pysolr
import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.ld_context import RISM_JSONLD_CONTEXT
from search_server.helpers.serializers import ContextDictSerializer
from search_server.helpers.solr_connection import SolrConnection


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

    def get_ctx(self, obj: Dict) -> Optional[Dict]:
        direct_request: bool = self.context.get("direct_request")
        return RISM_JSONLD_CONTEXT if direct_request else None

    def get_incip_id(self, obj: Dict) -> str:
        req = self.context.get("request")

        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))
        incipit_id: str = f"{obj.get('work_num_s')}"

        return get_identifier(req, "incipit", source_id=source_id, incipit_id=incipit_id)
