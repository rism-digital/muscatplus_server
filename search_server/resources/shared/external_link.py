from typing import Optional

import ypres

from shared_helpers.solr_connection import SolrResult


class ExternalResourcesSection(ypres.DictSerializer):
    """
    Returns a formatted object of external links.

    Note: `external_links_json` should be checked for presence
    in the Solr result before calling this, as we assume that if this is called there
    is at least one link!
    """
    section_label = ypres.MethodField(
        label="sectionLabel"
    )
    items = ypres.MethodField()

    def get_section_label(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        return transl.get("records.related_resources", {})

    def get_items(self, obj: SolrResult) -> list[dict]:
        if "external_resources" in obj:
            # If we're serializing from a JSON field, then this will be the key
            res = obj["external_resources"]
        else:
            # otherwise use the JSON field on the Solr document.
            res = obj["external_resources_json"]

        return ExternalResource(res, many=True,
                                context={"request": self.context.get("request")}).data


class ExternalResource(ypres.DictSerializer):
    rtype = ypres.StaticField(
        label="type",
        value="rism:ExternalResource"
    )
    url = ypres.MethodField()
    label = ypres.MethodField()
    resource_type = ypres.MethodField(
        label="resourceType"
    )

    def get_url(self, obj: dict) -> Optional[str]:
        return obj.get("url")

    def get_label(self, obj: dict) -> dict:
        label: str

        if "note" in obj:
            label = obj["note"]
        elif "link_type" in obj:
            label = obj["link_type"]
        else:
            label = "[External Resource]"
        return {"none": [label]}

    def get_resource_type(self, obj: dict) -> Optional[str]:
        rtype: str
        link_type: Optional[str] = obj.get("link_type")

        if link_type in ("IIIF", "IIIF manifest (digitized source)", "IIIF manifest (other)"):
            rtype = "IIIFManifestLink"
        elif link_type in ("Digitalization", "Digitized"):
            rtype = "DigitizationLink"
        else:
            rtype = "OtherLink"

        return f"rism:{rtype}"
