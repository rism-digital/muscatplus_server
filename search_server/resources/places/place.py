import re
from typing import Optional

import serpy

from search_server.helpers.display_fields import LabelConfig, get_display_fields
from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult, SolrConnection


async def handle_place_request(req, place_id: str) -> Optional[dict]:
    record: Optional[dict] = SolrConnection.get(f"place_{place_id}")

    if not record:
        return None

    return Place(record, context={"request": req,
                                  "direct_request": True}).data


class Place(JSONLDContextDictSerializer):
    pid = serpy.MethodField(
        label="id"
    )
    ptype = StaticField(
        label="type",
        value="rism:Place"
    )
    label = serpy.MethodField()
    summary = serpy.MethodField()

    def get_pid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        place_id: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "places.place", place_id=place_id)

    def get_label(self, obj: SolrResult) -> dict:
        return {"none": [obj.get("name_s")]}

    def get_summary(self, obj: SolrResult) -> Optional[dict]:
        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        field_config: LabelConfig = {
            "country_s": ("records.country", None),
            "district_s": ("records.place", None)  # TODO: Should be district
        }

        return get_display_fields(obj, transl, field_config)
