from typing import Dict, Optional

import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult


class PersonExternalLinkList(JSONLDContextDictSerializer):
    rtype = StaticField(
        label="type",
        value="rism:PersonExternalLinkList"
    )
    label = serpy.MethodField()
    items = serpy.MethodField()

    def get_label(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.translations

        return transl.get("records.related_resources")

    def get_items(self, obj: SolrResult) -> Dict:
        return PersonExternalLink(obj["external_links_json"], many=True,
                                  context={"request": self.context.get("request")}).data


class PersonExternalLink(JSONLDContextDictSerializer):
    ptype = StaticField(
        label="type",
        value="rism:PersonExternalLink"
    )
    url = serpy.MethodField()
    note = serpy.MethodField()

    def get_url(self, obj: Dict) -> Optional[str]:
        return obj.get("url")

    def get_note(self, obj: Dict) -> Optional[Dict]:
        return {"none": [n]} if (n := obj.get("note")) else None

