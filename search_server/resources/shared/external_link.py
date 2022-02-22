from typing import Optional

import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult


class ExternalResourcesSection(JSONLDContextDictSerializer):
    """
    Returns a formatted object of external links.

    Note: `external_links_json` should be checked for presence
    in the Solr result before calling this, as we assume that if this is called there
    is at least one link!
    """
    rtype = StaticField(
        label="type",
        value="rism:ExternalResourcesSection"
    )
    label = serpy.MethodField()
    items = serpy.MethodField()

    def get_label(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        return transl.get("records.related_resources")

    def get_items(self, obj: SolrResult) -> list[dict]:
        return ExternalResource(obj["external_resources_json"], many=True,
                                context={"request": self.context.get("request")}).data


class ExternalResource(JSONLDContextDictSerializer):
    rtype = StaticField(
        label="type",
        value="rism:ExternalResource"
    )
    url = serpy.MethodField()
    label = serpy.MethodField()
    resource_type = serpy.MethodField(
        label="resourceType"
    )

    def get_url(self, obj: dict) -> Optional[str]:
        return obj.get("url")

    def get_label(self, obj: dict) -> dict:
        label: str

        if "note" in obj:
            label = obj.get("note")
        elif "link_type" in obj:
            label = obj.get("link_type")
        else:
            label = "[External Resource]"
        return {"none": [label]}

    def get_resource_type(self, obj: dict) -> Optional[str]:
        rtype: str = ""
        link_type: Optional[str] = obj.get("link_type")

        if link_type == "IIIF":
            rtype = "IIIFManifestLink"
        elif link_type == "Digitalization":
            rtype = "DigitizationLink"
        else:
            rtype = "OtherLink"

        return f"rism:{rtype}"
