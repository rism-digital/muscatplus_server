import re
from typing import Dict, Optional, List

import pysolr
import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import ID_SUB, get_identifier, RISM_JSONLD_CONTEXT, get_jsonld_context, \
    JSONLDContext
from search_server.helpers.serializers import ContextDictSerializer
from search_server.helpers.solr_connection import SolrConnection, SolrResult


def handle_holding_request(req, source_id: str, holding_id: str) -> Optional[Dict]:
    fq: List = ["type:source_holding",
                f"source_membership_id:source_{source_id}",
                f"id:holding_{holding_id}"]
    record: pysolr.Results = SolrConnection.search("*:*", fq=fq, rows=1)

    if record.hits == 0:
        return None

    holding_record = record.docs[0]
    holding = SourceHolding(holding_record, context={"request": req,
                                                     "direct_request": True})

    return holding.data


class SourceHolding(ContextDictSerializer):
    ctx = serpy.MethodField(
        label="@context",
    )

    sid = serpy.MethodField(
        label="id"
    )
    stype = StaticField(
        label="type",
        value="rism:SourceHolding"
    )
    shelfmark = serpy.MethodField()
    held_by = serpy.MethodField(
        label="heldBy"
    )

    def get_ctx(self, obj: SolrResult) -> Optional[JSONLDContext]:
        direct_request: Optional[bool] = self.context.get("direct_request")
        return get_jsonld_context(self.context.get("request")) if direct_request else None

    def get_sid(self, obj: Dict) -> str:
        req = self.context.get('request')

        source_id: str = re.sub(ID_SUB, "", obj.get("source_membership_id"))
        holding_id: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "holding", source_id=source_id, holding_id=holding_id)

    def get_held_by(self, obj: Dict) -> Dict:
        req = self.context.get('request')
        institution_id: str = re.sub(ID_SUB, "", obj.get("holding_institution_id"))

        return {
            "id": get_identifier(req, "institution", institution_id=institution_id),
            "label": {
                "none": [f"{obj.get('holding_institution_s')}"]
            }
        }

    def get_shelfmark(self, obj: Dict) -> Dict:
        return {"none": [f"{obj.get('shelfmark_s')}"]}
