import re
from typing import List, Optional, Dict

import pysolr
import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrConnection, SolrResult


def handle_place_request(req, place_id: str) -> Optional[Dict]:
    fq: List = ["type:place",
                f"id:place_{place_id}"]

    record: pysolr.Results = SolrConnection.search("*:*", fq=fq, rows=1)

    if record.hits == 0:
        return None

    place_record = record.docs[0]

    return Place(place_record, context={"request": req,
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

    def get_pid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        place_id: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "places.place", place_id=place_id)

    def get_label(self, obj: SolrResult) -> Dict:
        return {"none": [obj.get("name_s")]}