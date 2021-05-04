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

    def get_fid(self, obj: Dict) -> str:
        req = self.context.get("request")
        festival_id: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "festivals.festival", festival_id=festival_id)

    def get_label(self, obj: Dict) -> Dict:
        # This serializer can also be used by the 'liturgical festival' section
        # on a source, which has a different name field.
        if 'name' in obj:
            return {"none": [f"{obj.get('name')}"]}
        else:
            return {"none": [f"{obj.get('name_s')}"]}

    def get_summary(self, obj: Dict) -> Optional[List]:
        if not self.context.get("direct_request"):
            return None

        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        field_config: LabelConfig = {
            # should be "Alternate terms" but this is not available in the translations currently...
            "alternate_terms_sm": ("records.other_form_of_name", None),
            "notes_sm": ("records.general_note", None)
        }

        return get_display_fields(obj, transl, field_config=field_config)
