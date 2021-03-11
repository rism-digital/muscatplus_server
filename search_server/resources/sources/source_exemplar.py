import re
from typing import Dict, Optional, List

import pysolr
import serpy

from search_server.helpers.display_fields import LabelConfig, get_display_fields
from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import ID_SUB, get_identifier, RISM_JSONLD_CONTEXT, get_jsonld_context, \
    JSONLDContext
from search_server.helpers.serializers import ContextDictSerializer
from search_server.helpers.solr_connection import SolrConnection, SolrResult, SolrManager


def handle_holding_request(req, source_id: str, holding_id: str) -> Optional[Dict]:
    fq: List = ["type:holding",
                f"source_id:source_{source_id}",
                f"id:holding_{holding_id} OR id:holding_{holding_id}-source_{source_id}"]
    record: pysolr.Results = SolrConnection.search("*:*", fq=fq, rows=1)

    if record.hits == 0:
        return None

    holding_record = record.docs[0]
    holding = SourceExemplar(holding_record, context={"request": req,
                                                     "direct_request": True})

    return holding.data


class SourceExemplarList(ContextDictSerializer):
    ctx = serpy.MethodField(
        label="@context"
    )
    lid = serpy.MethodField(
        label="id"
    )
    ltype = StaticField(
        label="type",
        value="rism:ExemplarList"
    )
    label = serpy.MethodField()
    items = serpy.MethodField()

    def get_ctx(self, obj: SolrResult) -> Optional[JSONLDContext]:
        direct_request: bool = self.context.get("direct_request")
        return get_jsonld_context(self.context.get("request")) if direct_request else None

    def get_lid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))

        return get_identifier(req, "holding_list", source_id=source_id)

    def get_label(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.translations

        return transl.get("records.exemplars")

    def get_items(self, obj: SolrResult) -> Optional[List]:
        conn = SolrManager(SolrConnection)
        fq: List = [f"source_id:{obj.get('id')}",
                    "type:holding"]

        sort: str = "siglum_s asc, shelfmark_s asc"
        conn.search("*:*", fq=fq, sort=sort)

        if conn.hits == 0:
            return None

        return SourceExemplar(conn.results,
                              many=True,
                              context={"request": self.context.get("request")}).data


class SourceExemplar(ContextDictSerializer):
    ctx = serpy.MethodField(
        label="@context",
    )

    sid = serpy.MethodField(
        label="id"
    )
    stype = StaticField(
        label="type",
        value="rism:SourceExemplar"
    )
    held_by = serpy.MethodField(
        label="heldBy"
    )
    summary = serpy.MethodField()

    def get_ctx(self, obj: SolrResult) -> Optional[JSONLDContext]:
        direct_request: Optional[bool] = self.context.get("direct_request")
        return get_jsonld_context(self.context.get("request")) if direct_request else None

    def get_sid(self, obj: Dict) -> str:
        req = self.context.get('request')
        # find the holding id
        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))

        return get_identifier(req, "holding", source_id=source_id, holding_id=obj.get("holding_id_sni"))

    def get_held_by(self, obj: Dict) -> Dict:
        req = self.context.get('request')
        institution_id: str = re.sub(ID_SUB, "", obj.get("institution_id"))

        return {
            "id": get_identifier(req, "institution", institution_id=institution_id),
            "type": "rism:Institution",
            "label": {
                "none": [f"{obj.get('institution_s')}"]
            },
            "siglum": {
                "none": [obj.get("siglum_s")]
            }
        }

    def get_summary(self, obj: SolrResult) -> List[Dict]:
        req = self.context.get("request")
        transl: Dict = req.app.translations

        field_config: LabelConfig = {
            "shelfmark_s": ("records.shelfmark", None),
            "former_shelfmarks_sm": ("records.shelfmark_olim", None),
            "material_held_sm": ("records.material_held", None),
            "local_numbers_sm": ("records.local_number", None),
        }

        return get_display_fields(obj, transl, field_config)
