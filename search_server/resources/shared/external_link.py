from typing import Dict, List, Optional

import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult


class ExternalResourcesList(JSONLDContextDictSerializer):
    """
    Returns a formatted object of external links.

    Note: `external_links_json` should be checked for presence
    in the Solr result before calling this, as we assume that if this is called there
    is at least one link!
    """
    rtype = StaticField(
        label="type",
        value="rism:ExternalResourceList"
    )
    label = serpy.MethodField()
    items = serpy.MethodField()

    def get_label(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        return transl.get("records.related_resources")

    def get_items(self, obj: SolrResult) -> List[Dict]:
        return ExternalResource(obj["external_resources_json"], many=True,
                                context={"request": self.context.get("request")}).data


class ExternalResource(JSONLDContextDictSerializer):
    rtype = StaticField(
        label="type",
        value="rism:ExternalResource"
    )
    url = serpy.MethodField()
    label = serpy.MethodField()

    def get_url(self, obj: Dict) -> Optional[str]:
        return obj.get("url")

    def get_label(self, obj: Dict) -> Optional[Dict]:
        return {"none": [n]} if (n := obj.get("note")) else None
