import re
from typing import Optional, Dict, List

import pysolr
import serpy

from search_server.helpers.display_fields import LabelConfig, get_display_fields
from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult, SolrConnection


def handle_festival_request(req, festival_id: str) -> Optional[Dict]:
    fq: List = ["type:liturgical_festival",
                f"id:festival_{festival_id}"]
    record: pysolr.Results = SolrConnection.search("*:*", fq=fq, rows=1)

    if record.hits == 0:
        return None

    return LiturgicalFestival(record.docs[0], context={"request": req,
                                                       "direct_request": True}).data


class LiturgicalFestival(JSONLDContextDictSerializer):
    fid = serpy.MethodField(
        label="id"
    )
    ftype = StaticField(
        label="type",
        value="rism:LiturgicalFestival"
    )
    label = serpy.MethodField()
    summary = serpy.MethodField()

    def get_fid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        festival_id: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "festivals.festival", festival_id=festival_id)

    def get_label(self, obj: SolrResult) -> Dict:
        return {"none": [f"{obj.get('name_s')}"]}

    def get_summary(self, obj: SolrResult) -> Optional[List]:
        req = self.context.get("request")
        transl: Dict = req.app.translations

        field_config: LabelConfig = {
            "alternate_terms_sm": ("records.alternate_terms", None),
            "notes_sm": ("records.general_note", None)
        }

        return get_display_fields(obj, transl, field_config=field_config)